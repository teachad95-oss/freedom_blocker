import os
import sys
import time
import threading
import psutil
import logging
import win32gui
import win32con
import win32process
import winreg

try:
    import uiautomation as auto
    HAS_UIAUTOMATION = True
except ImportError:
    HAS_UIAUTOMATION = False



# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebsiteBlocker:
    """
    Manages the blocking of websites by modifying the system hosts file.
    """
    HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
    REDIRECT_IP = "127.0.0.1"
    
    SAFE_SEARCH_MAP = {
        "google.com": "216.239.38.120",
        "www.google.com": "216.239.38.120",
        "bing.com": "150.171.27.16", # strict.bing.com IP
        "www.bing.com": "150.171.27.16",
        "duckduckgo.com": "20.207.72.188", # safe.duckduckgo.com
        "search.brave.com": "108.158.46.10", # safe.search.brave.com (User reported forcesafe was Moderate)
        # IPv6 VIPs
        "ipv6.google.com": "2001:4860:4802:32::78", 
    }
    
    # We will handle IPv6 lines dynamically in the block method loop

    IPV6_MAP = {
        "google.com": "2001:4860:4802:32::78",
        "www.google.com": "2001:4860:4802:32::78",
        "bing.com": "2620:1ec:33::16", # strict.bing.com IPv6
        "www.bing.com": "2620:1ec:33::16",
        "duckduckgo.com": "2603:1030:804:4::29", # Approximate safe.duckduckgo.com IPv6 (often varies, but this is common)
        "search.brave.com": "2a05:d018:76c:b02:f302:b0a9:1065:f769" # Approximate forcesafe IPv6
    }

    def __init__(self, blocked_sites=None):
        self.blocked_sites = blocked_sites if blocked_sites else []
        self.is_blocking = False
        self.safe_search_enabled = False

    def set_safe_search(self, enabled):
        self.safe_search_enabled = enabled

    def set_blocked_sites(self, sites):
        self.blocked_sites = sites

    def block(self):
        """Adds blocked sites to the hosts file."""
        if not self.blocked_sites:
            return

        try:
            with open(self.HOSTS_PATH, 'r+') as file:
                content = file.read()
                file.seek(0, 2) # Move to the end
                for site in self.blocked_sites:
                    # Add both with and without www, and mobile version m.
                    entries = [
                        f"{self.REDIRECT_IP} {site}\n",
                        f"{self.REDIRECT_IP} www.{site}\n",
                        f"{self.REDIRECT_IP} m.{site}\n"
                    ]
                    
                    for entry in entries:
                        if entry not in content:
                            file.write(entry)
                
                # Apply Safe Search Redirects
                if self.safe_search_enabled:
                    # IPv4
                    for domain, ip in self.SAFE_SEARCH_MAP.items():
                        entry = f"{ip} {domain}\n"
                        if entry not in content:
                             file.write(entry)
                    # IPv6
                    for domain, ip in self.IPV6_MAP.items():
                        entry = f"{ip} {domain}\n"
                        if entry not in content:
                             file.write(entry)

                    # Enforce Browser Policies (Disable DoH)
                    self._enforce_browser_policies(enable=True)

            
            self.is_blocking = True
            logger.info(f"Blocked sites: {self.blocked_sites}")
            # Flush DNS to ensure changes take effect immediately
            os.system("ipconfig /flushdns")
            
        except PermissionError:
            logger.error("Permission denied: Cannot modify hosts file. Run as administrator.")
        except Exception as e:
            logger.error(f"Error blocking sites: {e}")

    def unblock(self):
        """Removes blocked sites from the hosts file."""
        try:
            with open(self.HOSTS_PATH, 'r+') as file:
                lines = file.readlines()
                file.seek(0)
                file.truncate()
                
                for line in lines:
                    # Check if line contains any of the blocked sites
                    # Also skip Safe Search entries
                    # Check if line contains any of the blocked sites
                    # Also skip Safe Search entries
                    is_blocked_site = any(site in line for site in self.blocked_sites)
                    is_safe_search_v4 = any(f"{ip} {domain}" in line for domain, ip in self.SAFE_SEARCH_MAP.items())
                    is_safe_search_v6 = any(f"{ip} {domain}" in line for domain, ip in self.IPV6_MAP.items())
                    
                    if not is_blocked_site and not is_safe_search_v4 and not is_safe_search_v6:
                        file.write(line)
            
            # Revert Browser Policies (Enable DoH again / Remove restriction)
            # Only if we enabled them. We can always try to remove the keys we added.
            if self.safe_search_enabled:
                 self._enforce_browser_policies(enable=False)
            
            self.is_blocking = False
            logger.info("Unblocked all sites.")
            os.system("ipconfig /flushdns")

        except PermissionError:
            logger.error("Permission denied: Cannot modify hosts file. Run as administrator.")
        except Exception as e:
            logger.error(f"Error unblocking sites: {e}")

    def enforce_policies(self):
        """
        Public method to enforce browser policies (Self-healing).
        """
        if self.safe_search_enabled:
             self._enforce_browser_policies(enable=True)

    def _enforce_browser_policies(self, enable=True):
        """
        Sets Windows Registry keys to disable DNS-over-HTTPS (DoH) for major browsers.
        This forces them to use the system DNS (our hosts file).
        """
        policies = [
            # Chrome
            (r"Software\Policies\Google\Chrome", "DnsOverHttpsMode", "off" if enable else None, winreg.REG_SZ),
            (r"Software\Policies\Google\Chrome", "ForceGoogleSafeSearch", 1 if enable else None, winreg.REG_DWORD),
            (r"Software\Policies\Google\Chrome", "ForceYouTubeRestrict", None, winreg.REG_DWORD), # Removed/Allowed
            (r"Software\Policies\Google\Chrome", "IncognitoModeAvailability", None, winreg.REG_DWORD), # Removed/Allowed

            # Edge
            (r"Software\Policies\Microsoft\Edge", "DnsOverHttpsMode", "off" if enable else None, winreg.REG_SZ),
            (r"Software\Policies\Microsoft\Edge", "ForceGoogleSafeSearch", 1 if enable else None, winreg.REG_DWORD),
            (r"Software\Policies\Microsoft\Edge", "ForceBingSafeSearch", 2 if enable else None, winreg.REG_DWORD), # 2 = Strict
            (r"Software\Policies\Microsoft\Edge", "ForceYouTubeRestrict", None, winreg.REG_DWORD), # Removed/Allowed
            (r"Software\Policies\Microsoft\Edge", "InPrivateModeAvailability", None, winreg.REG_DWORD), # Allowed
            (r"Software\Policies\Microsoft\Edge", "BrowserGuestModeEnabled", 0 if enable else None, winreg.REG_DWORD),

            # Firefox
            (r"Software\Policies\Mozilla\Firefox", "DNSOverHTTPS", 0 if enable else None, winreg.REG_DWORD),
            (r"Software\Policies\Mozilla\Firefox", "DisablePrivateBrowsing", None, winreg.REG_DWORD), # Allowed

            # Brave (Same keys as Chrome + Tor switch)
            (r"Software\Policies\BraveSoftware\Brave", "DnsOverHttpsMode", "off" if enable else None, winreg.REG_SZ),
            (r"Software\Policies\BraveSoftware\Brave", "ForceGoogleSafeSearch", 1 if enable else None, winreg.REG_DWORD),
            (r"Software\Policies\BraveSoftware\Brave", "ForceYouTubeRestrict", None, winreg.REG_DWORD), # Removed/Allowed
            (r"Software\Policies\BraveSoftware\Brave", "IncognitoModeAvailability", None, winreg.REG_DWORD), # Allowed
            (r"Software\Policies\BraveSoftware\Brave", "TorDisabled", 1 if enable else None, winreg.REG_DWORD),
            (r"Software\Policies\BraveSoftware\Brave", "GuestModeEnabled", 0 if enable else None, winreg.REG_DWORD),
            (r"Software\Policies\BraveSoftware\Brave", "DefaultSearchProviderEnabled", 1 if enable else None, winreg.REG_DWORD),
            (r"Software\Policies\BraveSoftware\Brave", "DefaultSearchProviderName", "Brave Strict" if enable else None, winreg.REG_SZ),
            (r"Software\Policies\BraveSoftware\Brave", "DefaultSearchProviderSearchURL", "https://safe.search.brave.com/search?q={searchTerms}" if enable else None, winreg.REG_SZ)
        ]

        for path, name, value, val_type in policies:
            try:
                if value is not None:
                    # Create/Open Key
                    key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, path)
                    winreg.SetValueEx(key, name, 0, val_type, value)
                    winreg.CloseKey(key)
                else:
                    # Remove value (Revert)
                    try:
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_WRITE)
                        winreg.DeleteValue(key, name)
                        winreg.CloseKey(key)
                    except FileNotFoundError:
                        pass # Key didn't exist, all good
            except Exception as e:
                # Often fails if not admin, but app checks admin on start.
                logger.error(f"Error modifying registry {path}: {e}")


class AppBlocker:
    """
    Manages the blocking of applications by terminating their processes.
    """
    def __init__(self, blocked_apps=None):
        self.blocked_apps = blocked_apps if blocked_apps else []
        self.is_blocking = False

    def set_blocked_apps(self, apps):
        # Store as lowercase for case-insensitive comparison
        self.blocked_apps = [app.lower() for app in apps]

    def check_and_kill(self):
        """Checks running processes and kills any that are on the blocklist."""
        if not self.blocked_apps:
            return

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                
                # Check exact match or if blocked app name is part of process name
                for blocked in self.blocked_apps:
                    if blocked == proc_name or (blocked + ".exe") == proc_name:
                        # Double check access
                        try:
                            logger.info(f"Killing blocked process: {proc.info['name']} (PID: {proc.info['pid']})")
                            proc.kill()
                        except psutil.AccessDenied:
                            logger.error(f"Access denied killing {proc.info['name']}")

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
            except Exception as e:
                logger.error(f"Error checking process: {e}")

    def start_blocking(self):
        self.is_blocking = True
        logger.info("App blocking started.")

    def stop_blocking(self):
        self.is_blocking = False
        logger.info("App blocking stopped.")

class KeywordBlocker:
    """
    Monitors window titles and browser address bar URLs.
    
    Two-tier approach:
      1. Fast title scan (< 1ms, runs every cycle in service loop via check_and_close)
      2. Slow UIA URL scan (runs in background thread every 2s, never blocks main loop)
    """
    BROWSER_PROCESSES = {
        "chrome.exe", "msedge.exe", "brave.exe", "firefox.exe",
        "opera.exe", "vivaldi.exe", "browser.exe"
    }

    def __init__(self, blocked_keywords=None):
        self.blocked_keywords = blocked_keywords if blocked_keywords else []
        self.is_blocking = False
        self._uia_thread = None
        self._uia_stop = threading.Event()

    def set_blocked_keywords(self, keywords):
        self.blocked_keywords = [k.lower().strip() for k in keywords if k.strip()]

    # ── Process helper ─────────────────────────────────────────────────────────
    def _get_process_name(self, hwnd):
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid:
                return psutil.Process(pid).name().lower()
        except Exception:
            pass
        return ""

    # ── UIA address-bar extraction (slow, runs only in background thread) ──────
    def _get_browser_url(self, hwnd):
        if not HAS_UIAUTOMATION:
            return ""
        try:
            ctrl = auto.ControlFromHandle(hwnd)
            if not ctrl:
                return ""
            # Try well-known address bar names first (fast), then generic EditControl
            for name in ("Address and search bar", "Address bar",
                         "Search or enter web address", ""):
                edit = ctrl.EditControl(searchDepth=10, Name=name) if name else ctrl.EditControl(searchDepth=10)
                if edit and edit.Exists(0, 0):
                    try:
                        lp = edit.GetLegacyIAccessiblePattern()
                        if lp and lp.Value:
                            return lp.Value.lower()
                    except Exception:
                        pass
                    try:
                        vp = edit.GetValuePattern()
                        if vp and vp.Value:
                            return vp.Value.lower()
                    except Exception:
                        pass
                    if edit.Name:
                        return edit.Name.lower()
                    break   # found control but no text – stop searching
        except Exception as e:
            logger.debug(f"UIA error on hwnd {hwnd}: {e}")
        return ""

    # ── Close helper ───────────────────────────────────────────────────────────
    def _close_hwnd(self, hwnd):
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception as e:
            logger.error(f"Error closing window {hwnd}: {e}")

    # ── FAST path: window-title scan (called every second by service loop) ─────
    def check_and_close(self):
        """Fast title scan. Never calls UIA – always < 1ms."""
        if not self.blocked_keywords:
            return

        hwnds = []

        def _cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                hwnds.append(hwnd)
            return True         # keep enumerating

        try:
            win32gui.EnumWindows(_cb, None)
        except Exception as e:
            logger.error(f"EnumWindows error: {e}")
            return

        for hwnd in hwnds:
            title = win32gui.GetWindowText(hwnd).lower()
            if not title:
                continue
            for kw in self.blocked_keywords:
                if kw in title:
                    logger.info(f"[TITLE] Closing '{title}' – keyword '{kw}'")
                    self._close_hwnd(hwnd)
                    break

    # ── SLOW path: UIA URL scan (runs in its own thread every 2 seconds) ──────
    def _uia_loop(self):
        """Background thread: checks foreground browser URL every 2 s."""
        while not self._uia_stop.wait(2.0):   # sleep 2 s between checks
            if not self.blocked_keywords:
                continue
            try:
                fg_hwnd = win32gui.GetForegroundWindow()
                if not fg_hwnd or not win32gui.IsWindowVisible(fg_hwnd):
                    continue
                proc_name = self._get_process_name(fg_hwnd)
                if proc_name not in self.BROWSER_PROCESSES:
                    continue
                url = self._get_browser_url(fg_hwnd)
                if not url:
                    continue
                for kw in self.blocked_keywords:
                    if kw in url:
                        title = win32gui.GetWindowText(fg_hwnd)
                        logger.info(f"[URL] Closing [{proc_name}] '{title}' – keyword '{kw}' in '{url}'")
                        self._close_hwnd(fg_hwnd)
                        break
            except Exception as e:
                logger.debug(f"UIA loop error: {e}")

    # ── Lifecycle ──────────────────────────────────────────────────────────────
    def start_blocking(self):
        self.is_blocking = True
        self._uia_stop.clear()
        if HAS_UIAUTOMATION:
            self._uia_thread = threading.Thread(target=self._uia_loop, daemon=True, name="UIA-URL-Checker")
            self._uia_thread.start()
            logger.info("Keyword & URL blocking started (UIA thread running).")
        else:
            logger.info("Keyword blocking started (UIA not available – title-only).")

    def stop_blocking(self):
        self.is_blocking = False
        self._uia_stop.set()
        if self._uia_thread and self._uia_thread.is_alive():
            self._uia_thread.join(timeout=3.0)
        self._uia_thread = None
        logger.info("Keyword & URL blocking stopped.")

