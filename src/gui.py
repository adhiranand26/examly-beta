import os
import sys
import customtkinter as ctk
from src.config import AppConfig

class SettingsWindow(ctk.CTk):
    def __init__(self, app_controller):
        super().__init__()
        self.app_controller = app_controller
        self.config = AppConfig.load()
        
        self.title("Examly Settings")
        self.geometry("500x680")
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkLabel(self, text="⚙️ Examly Preferences", font=ctk.CTkFont(size=24, weight="bold"))
        header.pack(pady=(20, 10))
        
        # Frame for API Settings
        api_frame = ctk.CTkFrame(self)
        api_frame.pack(fill="x", padx=20, pady=10)
        api_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(api_frame, text="AI Provider:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.provider_var = ctk.StringVar(value=self.config.ai.provider)
        ctk.CTkOptionMenu(api_frame, variable=self.provider_var, values=["gemini", "openai", "mistral", "inceptionlabs", "ollama"]).grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(api_frame, text="API Key:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.api_key_var = ctk.StringVar(value=self.config.ai.api_key)
        # Using show="*" hides the API key
        self.api_entry = ctk.CTkEntry(api_frame, textvariable=self.api_key_var, show="*")
        self.api_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        # Frame for UI Settings
        ui_frame = ctk.CTkFrame(self)
        ui_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(ui_frame, text="Answer Window Transparency", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.opacity_var = ctk.DoubleVar(value=self.config.overlay_opacity)
        ctk.CTkSlider(ui_frame, variable=self.opacity_var, from_=0.1, to=1.0).pack(fill="x", padx=10, pady=(5, 15))
        
        # Frame for Hotkeys
        hk_frame = ctk.CTkFrame(self)
        hk_frame.pack(fill="x", padx=20, pady=10)
        hk_frame.grid_columnconfigure(1, weight=1)
        
        valid_keys = list("abcdefghijklmnopqrstuvwxyz0123456789")
        
        ctk.CTkLabel(hk_frame, text="Region Capture (Cmd+Shift + ...)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.region_key_var = ctk.StringVar(value=self.config.hotkey.region_key)
        ctk.CTkOptionMenu(hk_frame, variable=self.region_key_var, values=valid_keys, width=70).grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        ctk.CTkLabel(hk_frame, text="Full Capture (Cmd+Shift + ...)", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.full_key_var = ctk.StringVar(value=self.config.hotkey.key)
        ctk.CTkOptionMenu(hk_frame, variable=self.full_key_var, values=valid_keys, width=70).grid(row=1, column=1, padx=10, pady=10, sticky="e")

        ctk.CTkLabel(hk_frame, text="Show Last (Cmd+Shift + ...)", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.show_key_var = ctk.StringVar(value=self.config.hotkey.show_key)
        ctk.CTkOptionMenu(hk_frame, variable=self.show_key_var, values=valid_keys, width=70).grid(row=2, column=1, padx=10, pady=10, sticky="e")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(btn_frame, text="Save Settings", command=self.save_settings, width=140).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Save & Relaunch", command=self.save_and_relaunch, width=140, fg_color="#ff5566", hover_color="#cc4455").pack(side="left", padx=10)
        
        # Status Label
        self.status_label = ctk.CTkLabel(self, text="App is running. Minimize to keep using.", text_color="gray")
        self.status_label.pack(pady=5)

        # Fix Accessibility button
        ctk.CTkButton(self, text="Fix 'Not Trusted' / Hotkey Error", command=self.open_accessibility, fg_color="transparent", border_width=1, text_color="gray").pack(pady=10)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _update_config_from_vars(self):
        self.config.ai.api_key = self.api_key_var.get()
        self.config.ai.provider = self.provider_var.get()
        self.config.overlay_opacity = self.opacity_var.get()
        self.config.hotkey.region_key = self.region_key_var.get().lower()[-1:] if self.region_key_var.get() else 'd'
        self.config.hotkey.key = self.full_key_var.get().lower()[-1:] if self.full_key_var.get() else 'a'
        self.config.hotkey.show_key = self.show_key_var.get().lower()[-1:] if self.show_key_var.get() else 'e'
        
        self.region_key_var.set(self.config.hotkey.region_key)
        self.full_key_var.set(self.config.hotkey.key)
        self.show_key_var.set(self.config.hotkey.show_key)
        self.config.save()

    def save_settings(self):
        self._update_config_from_vars()
        self.app_controller.restart_hotkeys()
        self.status_label.configure(text="Settings saved!", text_color="#00e68a")

    def save_and_relaunch(self):
        self._update_config_from_vars()
        self.app_controller._shutdown()
        self.destroy()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def open_accessibility(self):
        os.system('open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"')
        self.status_label.configure(text="Please toggle 'Python' or 'Examly' ON in the Settings window that just opened.", text_color="#ffaa00")

    def on_close(self):
        self.app_controller._shutdown()
        self.destroy()
