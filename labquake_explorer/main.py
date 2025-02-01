"""Main entry point for Labquake Explorer application"""
import sys
import tkinter as tk
from labquake_explorer.ui.labquake_explorer import LabquakeExplorer

def main():
    try:
        root = tk.Tk()
        app = LabquakeExplorer(root)
        root.mainloop()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()