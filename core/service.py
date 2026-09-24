import threading
import time
import logging
from datetime import datetime, timedelta
from .blocker import WebsiteBlocker, AppBlocker, KeywordBlocker

logger = logging.getLogger(__name__)

class ServiceManager:
    """
    Orchestrates the blocking service, managing websites, applications, and keywords.
    Run in a background thread.
    """
    def __init__(self):
        self.website_blocker = WebsiteBlocker()
        self.app_blocker = AppBlocker()
        self.keyword_blocker = KeywordBlocker()
        self.is_running = False
        self.is_waiting = False
        self.locked_mode = False
        self._stop_event = threading.Event()
        self._thread = None

    def start(self, sites, apps, keywords, duration=None, start_time_str=None, end_time_str=None, locked=False, safe_search=False):
        """
        Starts the blocking session (or schedules it).
        :param sites, apps, keywords: Lists of blocked items.
        :param duration: Optional minutes to run (legacy/immediate mode).
        :param start_time_str: "HH:MM" (24h) start time.
        :param end_time_str: "HH:MM" (24h) end time.
        :param locked: If True, prevents stopping.
        """
        if self.is_running:
            logger.warning("Service is already running.")
            return

        self.locked_mode = locked
        
        # Apply Safe Search setting if provided/enabled
        # Note: We need the config to know if it's enabled, or we pass it in.
        # Ideally, ServiceManager shouldn't know about config directly if decoupling, 
        # but for now we can assume the caller passes the flag or we check it.
        # Let's add a parameter 'safe_search' or rely on the caller setting it on the blocker before start?
        # Better: Add 'safe_search' parameter to start().
        
        self.website_blocker.set_blocked_sites(sites)
        self.website_blocker.set_safe_search(safe_search)
        self.app_blocker.set_blocked_apps(apps)
        self.keyword_blocker.set_blocked_keywords(keywords)

        logger.info(f"Configuring service. Locked: {locked}, Duration: {duration}, Start: {start_time_str}, End: {end_time_str}")
        
        self.is_running = True
        self._stop_event.clear()

        # Start background loop
        self._thread = threading.Thread(
            target=self._run_loop, 
            args=(duration, start_time_str, end_time_str), 
            daemon=True
        )
        self._thread.start()

    def stop(self, force=False):
        """
        Stops the blocking session.
        """
        if self.locked_mode and not force and not self.is_waiting:
            # If we are just waiting (blocking hasn't started), we usually allow cancel. 
            # But if user requested locked mode, maybe they want the schedule locked too? 
            # For safety, let's allow canceling "Waiting" state even in locked mode, 
            # unless we want strict "Commitment Contracts". 
            # Simplification: Allow cancel if is_waiting is True, or if force=True.
            logger.warning("Cannot stop service: Locked Mode is active.")
            return False

        logger.info("Stopping service...")
        self._stop_event.set()
        
        # Only join if we are not calling stop() from the running thread itself
        if self._thread and self._thread != threading.current_thread():
            self._thread.join(timeout=2.0)
        
        self._disable_blocking()
        self.is_running = False
        self.is_waiting = False
        self.locked_mode = False
        return True

    def _enable_blocking(self):
        self.website_blocker.block()
        self.app_blocker.start_blocking()
        self.keyword_blocker.start_blocking()

    def _disable_blocking(self):
        self.website_blocker.unblock()
        self.app_blocker.stop_blocking()
        self.keyword_blocker.stop_blocking()

    def _run_loop(self, duration, start_str, end_str):
        # Calculate start/end datetimes
        start_dt = None
        end_dt = None
        
        if start_str and end_str:
            now = datetime.now()
            try:
                # Parse times
                s_hour, s_min = map(int, start_str.split(':'))
                e_hour, e_min = map(int, end_str.split(':'))
                
                start_dt = now.replace(hour=s_hour, minute=s_min, second=0, microsecond=0)
                end_dt = now.replace(hour=e_hour, minute=e_min, second=0, microsecond=0)
                
                # Handle overnight (23:00 -> 02:00)
                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)
                
                # Check for "Morning After" resume case:
                # If Start is in future (tonight), but we are currently in the window of "Yesterday's" session.
                # e.g. Start 23:00, End 07:00, Now 01:00.
                # Default logic sets Start=Today 23:00, End=Tom 07:00.
                # We need to shift back 1 day.
                if start_dt > now:
                     prev_start = start_dt - timedelta(days=1)
                     prev_end = end_dt - timedelta(days=1)
                     if prev_start <= now < prev_end:
                          start_dt = prev_start
                          end_dt = prev_end

                # If scheduling for "next occurrence"
                # If now > end_dt, it means the window has passed for today, schedule for tomorrow
                if now > end_dt:
                    start_dt += timedelta(days=1)
                    end_dt += timedelta(days=1)

            except ValueError:
                logger.error("Invalid time format. Stopping.")
                self.is_running = False
                return

        elif duration:
            # Duration mode (immediate)
            start_dt = datetime.now()
            end_dt = start_dt + timedelta(minutes=float(duration))

        if self.locked_mode:
            import sys
            import subprocess
            import os
            
            # Spawn watchdog
            # Command: [executable, --watchdog, pid, end_timestamp, --restore-session (optional logic)]
            # Simple integrity check: relaunch app if killed.
            # We pass the timestamp when this session is supposed to end.
            ts = end_dt.timestamp() if end_dt else (datetime.now() + timedelta(minutes=float(duration) if duration else 0)).timestamp()
            
            # handling frozen vs script
            if getattr(sys, 'frozen', False):
                 cmd = [sys.executable, "--watchdog", str(os.getpid()), str(ts)]
            else:
                 cmd = [sys.executable, "main.py", "--watchdog", str(os.getpid()), str(ts)]
            
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)

        # Main Loop
        while not self._stop_event.is_set():
            now = datetime.now()
            
            if start_dt and now < start_dt:
                # WAITING STATE
                self.is_waiting = True
                # Optional: Ensure blocking is OFF while waiting
                # (Self-correcting if loop restarts)
                # Sleep briefly
                time.sleep(1)
                continue
            
            # BLOCKING STATE
            self.is_waiting = False
            # Check if we need to enable blocking (idempotent usually, but good to check state)
            if not self.website_blocker.is_blocking: 
                self._enable_blocking()
            
            # Enforce dynamic blocks
            self.app_blocker.check_and_kill()
            self.keyword_blocker.check_and_close()
            
            # Self-healing: Re-enforce registry policies if safe search is on
            self.website_blocker.enforce_policies()
            
            # Check end time
            if end_dt and now >= end_dt:
                if start_str == "00:00" and end_str == "23:59":
                    start_dt += timedelta(days=1)
                    end_dt += timedelta(days=1)
                    logger.info("24/7 All-Day session rolled over to next day.")
                else:
                    logger.info("Time expired. Stopping service.")
                    self.stop(force=True) # Ensure we clean up
                    break
            
            time.sleep(1.0)

