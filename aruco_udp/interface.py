import tkinter as tk
from tkinter import messagebox, ttk
import threading
import cv2
import sv_ttk
from comtypes import CoInitialize, CoUninitialize
from pygrabber.dshow_graph import FilterGraph

from .tracker import ArUcoTracker
from .logger import village_logger as logger
from . import config

class ArucoConfigApp:
    """GUI settings application."""
    
    def __init__(self, root):
        self.root = root
        self.root.title(config.WINDOW_TITLE)
        self.root.geometry(config.WINDOW_SIZE)
        self.root.resizable(False, False)
        
        # Apply Sun Valley modern theme
        sv_ttk.set_theme(config.THEME)
        
        self.tracker_thread = None
        self.stop_event = threading.Event()
        self.is_running = False

        self._setup_ui()
        self._update_resolutions()
        
    def _get_cameras(self):
        try:
            devices = FilterGraph().get_input_devices()
            return {f"{i}: {name}": i for i, name in enumerate(devices)} or {"0: Default": 0}
        except Exception:
            return {"0: Default": 0}

    def _setup_ui(self):
        """Creates an ultra-compact user interface."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        # --- CAMERA & RESOLUTION ---
        cam_frame = ttk.LabelFrame(main_frame, text=" Camera & Resolution ", padding="8")
        cam_frame.pack(fill="x", pady=(0, 5))

        self.cameras_dict = self._get_cameras()
        camera_list = list(self.cameras_dict.keys())
        self.camera_var = tk.StringVar(value=camera_list[0] if camera_list else "")
        
        row1 = ttk.Frame(cam_frame)
        row1.pack(fill="x")
        
        self.camera_menu = ttk.Combobox(row1, textvariable=self.camera_var, values=camera_list, state="readonly")
        self.camera_menu.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.camera_var.trace_add("write", self._update_resolutions)

        self.res_var = tk.StringVar()
        self.res_menu = ttk.Combobox(row1, textvariable=self.res_var, state="readonly", width=12)
        self.res_menu.pack(side="right")

        # --- STREAM & NETWORK ---
        net_frame = ttk.LabelFrame(main_frame, text=" Stream & Network ", padding="8")
        net_frame.pack(fill="x", pady=5)

        row2 = ttk.Frame(net_frame)
        row2.pack(fill="x", pady=(0, 5))
        
        ttk.Label(row2, text="Mode:").pack(side="left", padx=(0, 2))
        self.mode_var = tk.StringVar(value=config.MODE_CENTER)
        self.mode_menu = ttk.Combobox(row2, textvariable=self.mode_var, 
                                        values=[config.MODE_CENTER, config.MODE_CORNERS], state="readonly", width=15)
        self.mode_menu.pack(side="left", fill="x", expand=True)

        row3 = ttk.Frame(net_frame)
        row3.pack(fill="x")
        
        ttk.Label(row3, text="IP:").pack(side="left", padx=(0, 2))
        self.ip_entry = ttk.Entry(row3, width=15)
        self.ip_entry.insert(0, config.DEFAULT_IP)
        self.ip_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ttk.Label(row3, text="Port:").pack(side="left", padx=(0, 2))
        self.port_entry = ttk.Entry(row3, width=6)
        self.port_entry.insert(0, str(config.DEFAULT_PORT))
        self.port_entry.pack(side="left")

        # --- FOOTER ---
        footer = ttk.Frame(main_frame)
        footer.pack(fill="x", pady=(10, 0))

        self.status_label = ttk.Label(footer, text="Status: IDLE", font=("Segoe UI", 9, "bold"))
        self.status_label.pack(side="left")

        self.btn_stop = ttk.Button(footer, text="STOP", command=self.stop, state="disabled", width=8)
        self.btn_stop.pack(side="right", padx=(5, 0))

        self.btn_start = ttk.Button(footer, text="START", command=self.start, style="Accent.TButton", width=10)
        self.btn_start.pack(side="right")

    def start(self):
        if self.is_running:
            return
        
        try:
            port = int(self.port_entry.get())
            ip = self.ip_entry.get().strip()
            mode = self.mode_var.get()
            cam_idx = self.cameras_dict[self.camera_var.get()]
            
            res_str = self.res_var.get()
            width, height = None, None
            if "x" in res_str:
                width, height = map(int, res_str.split("x"))
            
            self.is_running = True
            self.stop_event.clear()
            
            tracker = ArUcoTracker(cam_idx, port, ip, self.stop_event, mode=mode, width=width, height=height)
            self.tracker_thread = threading.Thread(
                target=tracker.run, 
                args=(self._on_tracker_frame, self._on_tracker_stop), 
                daemon=True
            )
            self.tracker_thread.start()
            
            self.status_label.config(text="Status: RUNNING")
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid port number.")

    def stop(self):
        if self.is_running:
            self.stop_event.set()
            self.status_label.config(text="Status: STOPPING...")

    def _on_tracker_frame(self, frame):
        """Draw frame in OpenCV window."""
        h, w = frame.shape[:2]
        if max(h, w) > config.PREVIEW_MAX_SIZE:
            scale = config.PREVIEW_MAX_SIZE / max(h, w)
            display_frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
        else:
            display_frame = frame

        cv2.imshow(config.WINDOW_TITLE, display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            self.root.after(0, self.stop)

    def _on_tracker_stop(self):
        """Called when tracking thread stops."""
        self.is_running = False
        cv2.destroyAllWindows()
        self.root.after(0, self._update_ui_to_idle)

    def _update_ui_to_idle(self):
        self.status_label.config(text="Status: IDLE")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def _update_resolutions(self, *args):
        cam_idx = self.cameras_dict.get(self.camera_var.get(), 0)
        self.res_menu.config(state="disabled")
        self.status_label.config(text="Checking camera...")
        
        thread = threading.Thread(target=self._probe_resolutions, args=(cam_idx,))
        thread.start()

    def _probe_resolutions(self, cam_idx):
        CoInitialize()
        supported = []
        try:
            graph = FilterGraph()
            graph.add_video_input_device(cam_idx)
            device = graph.get_input_device()
            formats = device.get_formats()
            
            unique_res = set()
            for f in formats:
                unique_res.add((f['width'], f['height']))
            
            sorted_res = sorted(list(unique_res), key=lambda x: x[0]*x[1], reverse=True)
            supported = [f"{w}x{h}" for w, h in sorted_res]
        except Exception as e:
            logger.debug(f"Resolution probe error: {e}")
            supported = ["640x480", "1280x720"]
        finally:
            CoUninitialize()
        
        self.root.after(0, lambda: self._finalize_resolutions(supported))

    def _finalize_resolutions(self, resolutions):
        self.res_menu.config(values=resolutions, state="readonly")
        if resolutions:
            self.res_var.set(resolutions[0])
        self.status_label.config(text="Status: IDLE")
