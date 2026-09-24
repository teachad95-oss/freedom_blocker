import customtkinter as ctk
import time
from datetime import datetime, timedelta
from tkinter import messagebox

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, config, service):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.config = config
        self.service = service

        self.grid_columnconfigure(0, weight=1)

        # Title
        self.title = ctk.CTkLabel(self, text="Session Control", font=ctk.CTkFont(size=20, weight="bold"))
        self.title.grid(row=0, column=0, padx=20, pady=20)

        # Status
        self.status_label = ctk.CTkLabel(self, text="Status: Inactive", font=ctk.CTkFont(size=14))
        self.status_label.grid(row=1, column=0, padx=20, pady=10)

        # Time Inputs Frame
        self.time_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.time_frame.grid(row=2, column=0, padx=20, pady=10)

        self.start_entry = ctk.CTkEntry(self.time_frame, placeholder_text="Start (HH:MM)", width=100)
        self.start_entry.pack(side="left", padx=5)
        
        self.label_to = ctk.CTkLabel(self.time_frame, text="to")
        self.label_to.pack(side="left", padx=5)

        self.end_entry = ctk.CTkEntry(self.time_frame, placeholder_text="End (HH:MM)", width=100)
        self.end_entry.pack(side="left", padx=5)

        # Set default values (Now -> Now + 1hr)
        now = datetime.now()
        self.start_entry.insert(0, now.strftime("%H:%M"))
        self.end_entry.insert(0, (now + timedelta(hours=1)).strftime("%H:%M"))

        # Start/Stop Button
        self.action_button = ctk.CTkButton(self, text="Start Session", command=self.action_cleanup)
        self.action_button.grid(row=4, column=0, padx=20, pady=20)

        # Info Label
        self.info_label = ctk.CTkLabel(self, text="Overnight schedules allowed (e.g. 23:00 to 07:00)", text_color="gray")
        self.info_label.grid(row=5, column=0, padx=20, pady=5)
        
        # Update Timer
        self.after(1000, self.update_status)

        # Check for persisted session to resume
        self.check_auto_resume()

    def check_auto_resume(self):
        session = self.config.get("current_session")
        if session:
            try:
                start_str = session.get("start")
                end_str = session.get("end")
                locked = session.get("locked", False)
                
                # Check if we are still within the window (or if it's an overnight session)
                # We need to rely on the ServiceManager's logic to determine if it SHOULD run
                # But we can do a quick check to see if End Time is passed for simple cases.
                # Actually, simplest is to just try to start it. The service manager handles time checks.
                # But we should update UI fields first.
                
                self.start_entry.delete(0, "end")
                self.start_entry.insert(0, start_str)
                self.end_entry.delete(0, "end")
                self.end_entry.insert(0, end_str)
                
                # Load blocklists
                sites = self.config.get("blocked_sites", [])
                apps = self.config.get("blocked_apps", [])
                keywords = self.config.get("blocked_keywords", [])
                
                print(f"Resuming session: {start_str} to {end_str}, Locked: {locked}")
                
                # Check for safe search preference in global config
                # Note: We don't save per-session safe search state in 'current_session' yet, 
                # but it's a global toggle usually. Let's use global config.
                safe_search = self.config.get("force_safe_search", False)
                
                self.service.start(sites, apps, keywords, duration=None, start_time_str=start_str, end_time_str=end_str, locked=locked, safe_search=safe_search)
                
                # If service decided it shouldn't run (e.g. ended), it will stop itself/not start.
                # But UI update comes next.
                self.update_ui_running()
                
            except Exception as e:
                print(f"Failed to resume session: {e}")
                self.config.set("current_session", None)

    def action_cleanup(self):
        if self.service.is_running:
            # Stop
            if self.service.stop():
                self.config.set("current_session", None)
                self.reset_ui()
            else:
                messagebox.showwarning("Locked Mode", "Cannot stop session while Locked Mode is active!")
        else:
            # Start
            start_str = self.start_entry.get().strip()
            end_str = self.end_entry.get().strip()
            
            # Basic format validation
            try:
                datetime.strptime(start_str, "%H:%M")
                datetime.strptime(end_str, "%H:%M")
            except ValueError:
                messagebox.showerror("Error", "Invalid time format. Use HH:MM (24h).")
                return

            sites = self.config.get("blocked_sites", [])
            apps = self.config.get("blocked_apps", [])
            keywords = self.config.get("blocked_keywords", [])
            locked = self.config.get("locked_mode", False)

            if not sites and not apps and not keywords:
                messagebox.showwarning("Warning", "No blocked sites, apps, or keywords configured!")
                return

            # Save active session for persistence
            self.config.set("current_session", {
                "start": start_str,
                "end": end_str,
                "locked": locked
            })
            
            safe_search = self.config.get("force_safe_search", False)
            self.service.start(sites, apps, keywords, duration=None, start_time_str=start_str, end_time_str=end_str, locked=locked, safe_search=safe_search)
            self.update_ui_running()

    def update_ui_running(self):
            if self.service.is_waiting:
                self.action_button.configure(text="Cancel Schedule", fg_color="orange", state="normal")
            else:
                self.action_button.configure(text="Session Running", fg_color="gray", state="disabled")

            self.start_entry.configure(state="disabled")
            self.end_entry.configure(state="disabled")

    def reset_ui(self):
            self.action_button.configure(text="Start Session", fg_color=["#3B8ED0", "#1F6AA5"], state="normal")
            self.status_label.configure(text="Status: Inactive", text_color="gray")
            self.start_entry.configure(state="normal")
            self.end_entry.configure(state="normal")

    def update_status(self):
        if self.service.is_running:
            if self.service.is_waiting:
                self.status_label.configure(text="Status: Scheduled (Waiting)", text_color="orange")
            else:
                self.status_label.configure(text="Status: Active (Blocking)", text_color="green")
            
            # Continuous update to ensure button state mimics internal state (e.g. transition from Waiting to Active)
            self.update_ui_running()
        else:
            self.status_label.configure(text="Status: Inactive", text_color="gray")
            if self.start_entry.cget("state") == "disabled":
                 self.reset_ui()
        
        self.after(1000, self.update_status)
