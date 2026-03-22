import tkinter as tk
from aruco_udp.interface import ArucoConfigApp

def main():
    """Application entry point."""
    # Fix blurry text on high DPI screens
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()
    ArucoConfigApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
