import customtkinter as ctk
import os
import sys

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, master, config):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.config = config

        self.grid_columnconfigure(0, weight=1)

        self.title = ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=20, weight="bold"))
        self.title.grid(row=0, column=0, padx=20, pady=20)

        # Appearance Mode
        self.appearance_mode_label = ctk.CTkLabel(self, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=1, column=0, padx=20, pady=(10, 0))
        
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self, values=["System", "Light", "Dark"],
                                                             command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=2, column=0, padx=20, pady=(10, 10))

        # Admin Status
        self.admin_label = ctk.CTkLabel(self, text=f"Admin Status: {'Active' if self.check_admin() else 'Inactive (Restart required)'}",
                                        text_color="green" if self.check_admin() else "red")
        self.admin_label.grid(row=3, column=0, padx=20, pady=20)

        # Locked Mode Setting
        self.locked_var = ctk.BooleanVar(value=self.config.get("locked_mode", False))
        self.locked_switch = ctk.CTkSwitch(self, text="Global Locked Mode (Prevent Exiting)", 
                                           variable=self.locked_var, command=self.toggle_locked_mode)
        self.locked_switch.grid(row=4, column=0, padx=20, pady=20)
        
        # Security PIN
        self.pin_button = ctk.CTkButton(self, text="Set/Change Blocklists PIN", command=self.set_pin)
        self.pin_button.grid(row=5, column=0, padx=20, pady=20)
        
        # Safe Search
        self.safe_search_var = ctk.BooleanVar(value=self.config.get("force_safe_search", False))
        self.safe_search_switch = ctk.CTkSwitch(self, text="Enforce Safe Search (Google/Bing/DDG)",
                                                variable=self.safe_search_var, command=self.toggle_safe_search)
        self.safe_search_switch.grid(row=6, column=0, padx=20, pady=20)

    def toggle_safe_search(self):
        self.config.set("force_safe_search", self.safe_search_var.get())

    def set_pin(self):
        from tkinter import simpledialog, messagebox
        
        # Check if PIN is already set
        current_pin = self.config.get("security_pin")
        if current_pin:
             # Ask for old PIN
             old_pin_input = simpledialog.askstring("Security Check", "Enter current PIN:", show='*')
             if old_pin_input is None: # Cancelled
                 return
             
             if old_pin_input != current_pin:
                 messagebox.showerror("Error", "Incorrect current PIN. Access denied.")
                 return

        # Proceed to set new PIN
        new_pin = simpledialog.askstring("Set PIN", "Enter new 4-digit PIN (leave empty to remove):")
        
        if new_pin is None: # Cancelled
            return

        if new_pin == "":
            self.config.set("security_pin", None)
            messagebox.showinfo("Security", "PIN removed.")
            return

        if len(new_pin) == 4 and new_pin.isdigit():
            self.config.set("security_pin", new_pin)
            messagebox.showinfo("Security", "PIN set successfully.")
        else:
            messagebox.showerror("Error", "PIN must be exactly 4 digits.")

    def toggle_locked_mode(self):
        self.config.set("locked_mode", self.locked_var.get())

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def check_admin(self):
        try:
            return os.getuid() == 0
        except AttributeError:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
