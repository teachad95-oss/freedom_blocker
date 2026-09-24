import os
import sys
import subprocess
import winreg
import psutil

def is_admin():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def kill_processes():
    print("Killing running blocker processes...")
    target_names = ["freedomblocker.exe", "freedomblocker_v15.exe", "freedomblocker_updated.exe"]
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info['name'].lower()
            if any(t in name for t in target_names):
                print(f"Killing process {proc.info['name']} (PID: {proc.info['pid']})")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def remove_scheduled_task():
    print("Deleting scheduled task 'FreedomBlocker'...")
    try:
        res = subprocess.run(["schtasks", "/delete", "/tn", "FreedomBlocker", "/f"], capture_output=True, text=True)
        if res.returncode == 0:
            print("Successfully deleted scheduled task 'FreedomBlocker'.")
        else:
            print(f"Scheduled task deletion output: {res.stderr.strip()}")
    except Exception as e:
        print(f"Error deleting scheduled task: {e}")

def clean_registry():
    print("Reverting browser policies registry keys...")
    policies = [
        # (path, name)
        (r"Software\Policies\Google\Chrome", "DnsOverHttpsMode"),
        (r"Software\Policies\Google\Chrome", "ForceGoogleSafeSearch"),
        (r"Software\Policies\Google\Chrome", "ForceYouTubeRestrict"),
        (r"Software\Policies\Google\Chrome", "IncognitoModeAvailability"),
        
        (r"Software\Policies\Microsoft\Edge", "DnsOverHttpsMode"),
        (r"Software\Policies\Microsoft\Edge", "ForceGoogleSafeSearch"),
        (r"Software\Policies\Microsoft\Edge", "ForceBingSafeSearch"),
        (r"Software\Policies\Microsoft\Edge", "ForceYouTubeRestrict"),
        (r"Software\Policies\Microsoft\Edge", "InPrivateModeAvailability"),
        (r"Software\Policies\Microsoft\Edge", "BrowserGuestModeEnabled"),
        
        (r"Software\Policies\Mozilla\Firefox", "DNSOverHTTPS"),
        (r"Software\Policies\Mozilla\Firefox", "DisablePrivateBrowsing"),
        
        (r"Software\Policies\BraveSoftware\Brave", "DnsOverHttpsMode"),
        (r"Software\Policies\BraveSoftware\Brave", "ForceGoogleSafeSearch"),
        (r"Software\Policies\BraveSoftware\Brave", "ForceYouTubeRestrict"),
        (r"Software\Policies\BraveSoftware\Brave", "IncognitoModeAvailability"),
        (r"Software\Policies\BraveSoftware\Brave", "TorDisabled"),
        (r"Software\Policies\BraveSoftware\Brave", "GuestModeEnabled"),
        (r"Software\Policies\BraveSoftware\Brave", "DefaultSearchProviderEnabled"),
        (r"Software\Policies\BraveSoftware\Brave", "DefaultSearchProviderName"),
        (r"Software\Policies\BraveSoftware\Brave", "DefaultSearchProviderSearchURL"),
    ]

    for path, name in policies:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_WRITE)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
            print(f"Removed registry value: {path}\\{name}")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error removing registry value {path}\\{name}: {e}")

    # Check if empty policy keys can be deleted
    empty_keys = [
        r"Software\Policies\BraveSoftware\Brave",
        r"Software\Policies\BraveSoftware",
        r"Software\Policies\Google\Chrome",
        r"Software\Policies\Google",
        r"Software\Policies\Microsoft\Edge",
        r"Software\Policies\Mozilla\Firefox",
        r"Software\Policies\Mozilla",
    ]
    for path in empty_keys:
        try:
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, path)
            print(f"Deleted empty registry key: {path}")
        except FileNotFoundError:
            pass
        except Exception as e:
            # Key might not be empty or permission error
            pass

def clean_hosts_file():
    import stat
    print("Cleaning hosts file...")
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
    
    # Domains we want to unblock/clean up
    domains_to_remove = ["facebook.com", "twitter.com", "instagram.com", "youtube.com", "reddit.com", "duckduckgo.com", "bing.com", "brave.com", "google.com"]
    
    try:
        # Remove Read-Only attribute to allow editing
        try:
            os.chmod(hosts_path, stat.S_IWRITE)
        except Exception as chmod_err:
            print(f"Warning: Could not clear Read-Only attribute: {chmod_err}")

        with open(hosts_path, 'r') as f:
            lines = f.readlines()
            
        new_lines = []
        removed_count = 0
        for line in lines:
            # If line is a comment or does not contain any of our target domains, keep it
            if line.strip().startswith("#") or not any(domain in line.lower() for domain in domains_to_remove):
                new_lines.append(line)
            else:
                removed_count += 1
                print(f"Removing line: {line.strip()}")
                
        with open(hosts_path, 'w') as f:
            f.writelines(new_lines)
            
        # Restore Read-Only attribute
        try:
            os.chmod(hosts_path, stat.S_IREAD)
        except Exception as chmod_err:
            pass
            
        print(f"Removed {removed_count} blocker entries from hosts file.")
        os.system("ipconfig /flushdns")
    except PermissionError:
        print("Permission Denied: Run as Administrator to clean hosts file.")
    except Exception as e:
        print(f"Error cleaning hosts file: {e}")

class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def main():
    if not is_admin():
        print("This script must be run as Administrator to remove services and registry keys.")
        print("Re-running with Administrator privileges...")
        import ctypes
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{__file__}"', None, 1)
        sys.exit(0)

    # Redirect stdout and stderr to a file so we can view it
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cleanup.log")
    sys.stdout = Logger(log_file)
    sys.stderr = sys.stdout

    # Deleting scheduled task first, so it doesn't restart when killed
    remove_scheduled_task()
    
    # Kill running instances
    kill_processes()
    
    # Revert registry keys
    clean_registry()
    
    # Revert hosts file changes
    clean_hosts_file()
    
    print("\n--- Cleanup Complete! ---")
    print("Freedom Blocker has been completely stopped and system settings restored.")
    # We don't block on input if redirected, but let's write to log
    print("Exiting.")

if __name__ == "__main__":
    main()
