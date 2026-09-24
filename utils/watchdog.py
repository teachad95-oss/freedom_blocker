import sys
import time
import os
import psutil
import subprocess
import logging
from datetime import datetime

# Configure logging to file since it's a background process
logging.basicConfig(filename='watchdog.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def monitor(target_pid, end_timestamp, restore_cmd):
    logger.info(f"Watchdog started. Monitoring PID: {target_pid} until {end_timestamp}")
    
    while True:
        try:
            # Check if target process exists
            if not psutil.pid_exists(target_pid):
                logger.warning("Target process died! Restoring session...")
                # Relaunch
                subprocess.Popen(restore_cmd)
                return # Exit watchdog, new app instance will spawn a new watchdog if needed
            
            # Check time
            if time.time() > end_timestamp:
                logger.info("Session time expired. Watchdog exiting.")
                return

            time.sleep(2)
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    try:
        # Args: [script, target_pid, end_timestamp, *restore_cmd_parts]
        target_pid = int(sys.argv[1])
        end_timestamp = float(sys.argv[2])
        restore_cmd = sys.argv[3:]
        
        monitor(target_pid, end_timestamp, restore_cmd)
    except Exception as e:
        logger.error(f"Failed to start watchdog: {e}")
