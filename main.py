import customtkinter as ctk
import sys
import os
from ui.main_window import MainWindow
from core.service import ServiceManager
from utils.config import ConfigManager

def check_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def main():

    if len(sys.argv) > 1 and sys.argv[1] == "--watchdog":
        # Run as watchdog
        # Args: --watchdog <target_pid> <end_timestamp> *restore_args
        try:
            from utils.watchdog import monitor
            target_pid = int(sys.argv[2])
            end_timestamp = float(sys.argv[3])
            restore_cmd = sys.argv[4:]
            monitor(target_pid, end_timestamp, restore_cmd)
        except Exception as e:
            print(f"Watchdog failure: {e}")
        return

    if not check_admin():
        # Re-run the program with admin rights
        import ctypes
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        return

    ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

    # Determine absolute path to config directory
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    config = ConfigManager(base_dir)
    service = ServiceManager()

    # Enforce Auto Start (Always On)
    ensure_autostart_powershell()

    # Single Instance Lock
    # We must keep the handle alive, so assign it to a variable
    mutex = SingleInstance()
    if mutex.already_running:
        print("Another instance is already running. Exiting.")
        sys.exit(0)

    app = MainWindow(config, service)

    # Tray Icon
    # We pass the app to the tray so it can show/hide it
    tray = TrayIcon(app)
    
    # If launched with "--hidden", hide the window immediately
    if "--hidden" in sys.argv:
        app.withdraw()
    
    # Run Tray in separate thread or hook into loop? 
    # CTk mainloop needs to be main thread. 
    # pystray run() is blocking, so best run tray.run_detached() or similar.
    # Actually, pystray typically needs to run on main thread for macOS, but Windows is flexible.
    # However, running CTk loop represents the "app".
    
    # Let's start tray icon in background thread to avoid blocking CTk
    import threading
    tray_thread = threading.Thread(target=tray.run, daemon=True)
    tray_thread.start()

    app.set_tray(tray) # Give app reference to tray to update menu/icon if needed
    app.mainloop()

class SingleInstance:
    """ Limits application to single instance """
    def __init__(self):
        import win32event, win32api, winerror
        self.mutexname = "Global\\FreedomBlocker_Mutex_Unique_Id"
        self.mutex = win32event.CreateMutex(None, False, self.mutexname)
        self.last_error = win32api.GetLastError()
    
    @property
    def already_running(self):
        return self.last_error == 183 # ERROR_ALREADY_EXISTS

class TrayIcon:
    def __init__(self, app):
        self.app = app
        self.icon = None
    
    def run(self):
        import pystray
        from PIL import Image, ImageDraw

        # Create a simple icon if we don't have one
        # Ideally load 'icon.ico' if exists
        try:
            image = Image.open("icon.ico")
        except:
            # Generate blue square
            width = 64
            height = 64
            image = Image.new('RGB', (width, height), color=(30, 144, 255))
            dc = ImageDraw.Draw(image)
            dc.rectangle((width//4, height//4, 3*width//4, 3*height//4), fill="white")

        def show_window(icon, item):
            self.app.deiconify()
            self.app.lift()
            self.app.focus_force()

        def quit_app(icon, item):
            # We defer to app's on_close to handle locked mode checks
            self.app.quit_from_tray()

        menu = pystray.Menu(
            pystray.MenuItem("Show", show_window, default=True),
            pystray.MenuItem("Quit", quit_app)
        )

        self.icon = pystray.Icon("FreedomBlocker", image, "Freedom Blocker", menu)
        self.icon.run()

    def notify(self, title, message):
        if self.icon:
            self.icon.notify(message, title)

def ensure_autostart_powershell():
    import subprocess
    import traceback
    
    task_name = "FreedomBlocker"
    
    if getattr(sys, 'frozen', False):
         # When passing to PowerShell, we need to be careful with quotes.
         # exe path: D:\Path\FreedomBlocker.exe
         exe = sys.executable
    else:
         exe = sys.executable 
         # Note: script support is trickier with Powershell actions, assuming frozen for prod logic
         # But we can try to support it by wrapping args
    
    # Determine arguments
    # We want to run with "--hidden" so it starts minimized
    action_args = "--hidden"
    if not getattr(sys, 'frozen', False):
         script = os.path.abspath("main.py")
         action_args = f'"{script}" --hidden'
    
    log_path = os.path.join(os.path.dirname(exe) if getattr(sys, 'frozen', False) else os.getcwd(), "autostart_debug.log")

    # PowerShell Command to creating valid task
    # We use a huge one-liner or multiple calls.
    # New-ScheduledTaskAction -Execute "..." -Argument "..."
    # New-ScheduledTaskTrigger -AtLogon
    # Register-ScheduledTask ...
    
    # We specifically want: 
    # 1. Trigger: AtLogon
    # 2. Trigger: Once, RepetitionInterval (1 minute), RepetitionDuration (Indefinite/1 day)
    # 3. Settings: Hidden, MultipleInstances=IgnoreNew, ExecutionTimeLimit=0 (Unlimited)
    # 4. User: SYSTEM or Current User with RunLevel Highest
    
    # Complexity: PowerShell escaping from Python is hell.
    # We will write a temp .ps1 file and execute it.
    
    ps_script = f"""
    $TaskName = "{task_name}"
    $ExePath = "{exe}"
    $Arg = '{action_args}'

    $Action = New-ScheduledTaskAction -Execute $ExePath -Argument $Arg
    
    # Trigger 1: At Logon
    $TrigLogon = New-ScheduledTaskTrigger -AtLogon
    
    # Trigger 2: At Startup (for robustness) - optional/skip
    
    # Settings: Hidden, RunLevel Highest, IgnoreNew execution
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
    
    # Register
    # Note: We need to use -Force
    # We want repetition. It's easier to modify the trigger object after creation or use raw XML, but Let's try advanced properties.
    $TrigLogon.Repetition.Interval = "PT1M"
    $TrigLogon.Repetition.Duration = "P1D" # Re-triggers every logon anyway
    
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $TrigLogon -Settings $Settings -RunLevel Highest -User $env:USERNAME -Force
    """
    
    ps_file = os.path.join(os.path.dirname(log_path), "register_task.ps1")
    
    try:
        with open(ps_file, "w") as f:
            f.write(ps_script)
            
        # Run PowerShell
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_file]
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
        
        with open(log_path, "w") as f:
            f.write(f"PS Script:\n{ps_script}\n")
            f.write(f"Return Code: {result.returncode}\n")
            f.write(f"Stdout: {result.stdout}\n")
            f.write(f"Stderr: {result.stderr}\n")

    except Exception as e:
         with open(log_path, "a") as f:
            f.write(f"Exception: {e}\n{traceback.format_exc()}\n")

if __name__ == "__main__":
    main()
