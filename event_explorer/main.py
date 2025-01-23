"""Main entry point for Event Explorer application"""
import sys
import tkinter as tk
from event_explorer.ui.event_explorer import EventExplorer

def main():
    try:
        root = tk.Tk()
        app = EventExplorer(root)
        root.mainloop()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()