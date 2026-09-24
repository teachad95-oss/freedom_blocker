try:
    from core.blocker import WebsiteBlocker, AppBlocker, KeywordBlocker
    from core.service import ServiceManager
    from utils.config import ConfigManager
    from ui.main_window import MainWindow
    print("Imports successful")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"Error: {e}")
