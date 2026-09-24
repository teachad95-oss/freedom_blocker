import customtkinter as ctk
from tkinter import simpledialog, messagebox

class BlocklistFrame(ctk.CTkFrame):
    def __init__(self, master, config, service):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.config = config
        self.service = service

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Websites Column
        self.site_label = ctk.CTkLabel(self, text="Blocked Websites", font=ctk.CTkFont(size=14, weight="bold"))
        self.site_label.grid(row=0, column=0, padx=5, pady=10)

        self.site_frame = ctk.CTkScrollableFrame(self, label_text="Websites")
        self.site_frame.grid(row=1, column=0, padx=5, pady=10, sticky="nsew")

        self.add_site_btn = ctk.CTkButton(self, text="Add Website", command=self.add_website)
        self.add_site_btn.grid(row=2, column=0, padx=5, pady=10)

        # Apps Column
        self.app_label = ctk.CTkLabel(self, text="Blocked Apps", font=ctk.CTkFont(size=14, weight="bold"))
        self.app_label.grid(row=0, column=1, padx=5, pady=10)

        self.app_frame = ctk.CTkScrollableFrame(self, label_text="Apps")
        self.app_frame.grid(row=1, column=1, padx=5, pady=10, sticky="nsew")

        self.add_app_btn = ctk.CTkButton(self, text="Add App", command=self.add_app)
        self.add_app_btn.grid(row=2, column=1, padx=5, pady=10)

        # Keywords Column
        self.keyword_label = ctk.CTkLabel(self, text="Blocked Keywords", font=ctk.CTkFont(size=14, weight="bold"))
        self.keyword_label.grid(row=0, column=2, padx=5, pady=10)

        self.keyword_frame = ctk.CTkScrollableFrame(self, label_text="Keywords")
        self.keyword_frame.grid(row=1, column=2, padx=5, pady=10, sticky="nsew")

        self.add_keyword_btn = ctk.CTkButton(self, text="Add Keyword", command=self.add_keyword)
        self.add_keyword_btn.grid(row=2, column=2, padx=5, pady=10)

        self.refresh_lists()

    def refresh_lists(self):
        # Clear existing
        for widget in self.site_frame.winfo_children():
            widget.destroy()
        for widget in self.app_frame.winfo_children():
            widget.destroy()
        for widget in self.keyword_frame.winfo_children():
            widget.destroy()

        # Load sites
        for site in self.config.get("blocked_sites", []):
            self.create_item(self.site_frame, site, "blocked_sites")

        # Load apps
        for app in self.config.get("blocked_apps", []):
            self.create_item(self.app_frame, app, "blocked_apps")

        # Load keywords
        for keyword in self.config.get("blocked_keywords", []):
            self.create_item(self.keyword_frame, keyword, "blocked_keywords")

    def create_item(self, parent, text, list_key):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=5, pady=5)
        
        # Truncate long text
        display_text = text if len(text) < 20 else text[:17] + "..."
        label = ctk.CTkLabel(frame, text=display_text)
        label.pack(side="left", padx=5)
        
        del_btn = ctk.CTkButton(frame, text="X", width=30, fg_color="red", hover_color="darkred",
                                command=lambda t=text, k=list_key: self.delete_item(k, t))
        del_btn.pack(side="right", padx=5)

    def add_website(self):
        site = simpledialog.askstring("Add Website", "Enter domain (e.g., facebook.com):")
        if site:
            self.config.add_unique("blocked_sites", site.lower())
            self.refresh_lists()

    def add_app(self):
        app = simpledialog.askstring("Add App", "Enter executable name (e.g., spotify):")
        if app:
            self.config.add_unique("blocked_apps", app.lower())
            self.refresh_lists()

    def add_keyword(self):
        keyword = simpledialog.askstring("Add Keyword", "Enter keyword (e.g., YouTube):")
        if keyword:
            self.config.add_unique("blocked_keywords", keyword.lower())
            self.refresh_lists()

    def delete_item(self, list_key, item):
        if self.service.is_running:
             messagebox.showwarning("Restricted", "You cannot remove items during an active session!")
             return
             
        self.config.remove_item(list_key, item)
        self.refresh_lists()
