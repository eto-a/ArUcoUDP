import tkinter as tk
from tkinter import messagebox, ttk
import threading
from pygrabber.dshow_graph import FilterGraph
from tracker import ArUcoTracker

class ArucoConfigApp:
    """Класс графического интерфейса настроек."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Aruco Config")
        self.root.geometry("350x300")
        
        self.tracker_thread = None
        self.stop_event = threading.Event()
        self.is_running = False

        self._setup_ui()
        
    def _get_cameras(self):
        """Получает список доступных камер через DirectShow."""
        try:
            devices = FilterGraph().get_input_devices()
            return {f"{i}: {name}": i for i, name in enumerate(devices)} or {"0: Default": 0}
        except Exception:
            return {"0: Default": 0}

    def _setup_ui(self):
        """Создает элементы управления."""
        tk.Label(self.root, text="Select Camera:").pack(pady=5)
        self.cameras_dict = self._get_cameras()
        camera_list = list(self.cameras_dict.keys())
        self.camera_var = tk.StringVar(value=camera_list[0])
        self.camera_menu = ttk.Combobox(self.root, textvariable=self.camera_var, 
                                        values=camera_list, state="readonly", width=40)
        self.camera_menu.pack(padx=10)

        tk.Label(self.root, text="UDP Port:").pack(pady=5)
        self.port_entry = tk.Entry(self.root)
        self.port_entry.insert(0, "5005")
        self.port_entry.pack()

        self.status_label = tk.Label(self.root, text="Status: IDLE", fg="gray")
        self.status_label.pack(pady=10)

        self.btn_start = tk.Button(self.root, text="START", command=self.start, bg="green", fg="white", width=15)
        self.btn_start.pack(pady=5)

        self.btn_stop = tk.Button(self.root, text="STOP", command=self.stop, bg="red", fg="white", width=15, state="disabled")
        self.btn_stop.pack(pady=5)

    def start(self):
        if self.is_running:
            return
        
        try:
            port = int(self.port_entry.get())
            cam_idx = self.cameras_dict[self.camera_var.get()]
            
            self.is_running = True
            self.stop_event.clear()
            
            tracker = ArUcoTracker(cam_idx, port, self.stop_event)
            self.tracker_thread = threading.Thread(target=tracker.run, args=(self._on_tracker_stop,), daemon=True)
            self.tracker_thread.start()
            
            self.status_label.config(text="Status: RUNNING", fg="green")
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid port number.")

    def stop(self):
        if self.is_running:
            self.stop_event.set()
            self.status_label.config(text="Status: STOPPING...", fg="orange")

    def _on_tracker_stop(self):
        """Вызывается по завершении потока детекции."""
        self.is_running = False
        self.root.after(0, self._update_ui_to_idle)

    def _update_ui_to_idle(self):
        self.status_label.config(text="Status: IDLE", fg="gray")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
