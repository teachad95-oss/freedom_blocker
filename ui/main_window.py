import customtkinter as ctk
from .dashboard import DashboardFrame
from .blocklists import BlocklistFrame
from .settings import SettingsFrame

class MainWindow(ctk.CTk):
    def __init__(self, config, service):
        super().__init__()

        self.config = config
        self.service = service

        self.title("Freedom Blocker")
        self.geometry("800x600")

        # Configure grid layout (1x2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # distinct navigation frame
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(4, weight=1)

        self.nav_label = ctk.CTkLabel(self.navigation_frame, text="  Freedom Blocker",
                                      compound="left", font=ctk.CTkFont(size=15, weight="bold"))
        self.nav_label.grid(row=0, column=0, padx=20, pady=20)

        self.home_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10, text="Dashboard",
                                         fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                         anchor="w", command=self.home_button_event)
        self.home_button.grid(row=1, column=0, sticky="ew")

        self.blocklist_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10, text="Blocklists",
                                              fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                              anchor="w", command=self.blocklist_button_event)
        self.blocklist_button.grid(row=2, column=0, sticky="ew")

        self.settings_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10, text="Settings",
                                             fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                             anchor="w", command=self.settings_button_event)
        self.settings_button.grid(row=3, column=0, sticky="ew")

        # Create frames
        self.dashboard_frame = DashboardFrame(self, config, service)
        self.blocklist_frame = BlocklistFrame(self, config, service)
        self.settings_frame = SettingsFrame(self, config)

        # Select default frame
        self.select_frame_by_name("home")

        # Intercept close event
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.tray = None

    def set_tray(self, tray):
        self.tray = tray

    def on_close(self):
        # If locked, prevent closing
        if self.service.is_running and not self.service.is_waiting and self.service.locked_mode:
            from tkinter import messagebox
            messagebox.showwarning("Locked Mode", "Session is locked! You cannot close the application until the timer expires.")
            return
        
        # If not locked, minimize to tray instead of closing totally?
        # Standard behavior: Close 'X' minimizes to tray.
        self.withdraw()
        if self.tray:
            self.tray.notify("Freedom Blocker", "Application minimized to tray.")

    def quit_from_tray(self):
        # Called from tray "Quit"
        if self.service.is_running and not self.service.is_waiting and self.service.locked_mode:
            from tkinter import messagebox
            # We must show window to show message
            self.deiconify()
            self.lift()
            messagebox.showwarning("Locked Mode", "Session is locked! You cannot quit.")
            return
        
        if self.service.is_running:
             self.service.stop(force=True)
             
        self.destroy()
        if self.tray and self.tray.icon:
            self.tray.icon.stop()
        sys.exit(0)

    def select_frame_by_name(self, name):
        # set button color for selected button
        self.home_button.configure(fg_color=("gray75", "gray25") if name == "home" else "transparent")
        self.blocklist_button.configure(fg_color=("gray75", "gray25") if name == "blocklist" else "transparent")
        self.settings_button.configure(fg_color=("gray75", "gray25") if name == "settings" else "transparent")

        # show selected frame
        if name == "home":
            self.dashboard_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.dashboard_frame.grid_forget()
        
        if name == "blocklist":
            self.blocklist_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.blocklist_frame.grid_forget()

        if name == "settings":
            self.settings_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.settings_frame.grid_forget()

    def home_button_event(self):
        self.select_frame_by_name("home")

    def blocklist_button_event(self):
        # Check security PIN
        pin = self.config.get("security_pin")
        if pin:
            from tkinter import simpledialog, messagebox
            user_input = simpledialog.askstring("Security", "Enter PIN to access Blocklists:", show='*')
            if user_input != pin:
                 messagebox.showerror("Access Denied", "Incorrect PIN.")
                 return

        self.select_frame_by_name("blocklist")

    def settings_button_event(self):
        self.select_frame_by_name("settings")
