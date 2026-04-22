import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import threading
import cv2
import sv_ttk
import logging
from comtypes import CoInitialize, CoUninitialize
from pygrabber.dshow_graph import FilterGraph

from .tracker import ArUcoTracker
from .logger import village_logger as logger
from . import config

class LogHandler(logging.Handler):
    """Custom logging handler to redirect logs to a Tkinter Text widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.see(tk.END)
        self.text_widget.after(0, append)

class ArucoConfigApp:
    """Modern GUI settings application with Tabbed interface and Live Logs."""
    
    def __init__(self, root):
        self.root = root
        self.root.title(config.WINDOW_TITLE)
        self.root.geometry(config.WINDOW_SIZE)
        self.root.resizable(False, False)
        
        # High-DPI Fix (already in main.py, but good to ensure spacing)
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
        """Creates a modern tabbed interface with cards and live logs."""
        main_container = ttk.Frame(self.root, padding="15")
        main_container.pack(fill="both", expand=True)

        # --- PERSISTENT HEADER ---
        header = ttk.Frame(main_container)
        header.pack(fill="x", pady=(0, 10))
        
        title_row = ttk.Frame(header)
        title_row.pack(fill="x")
        ttk.Label(title_row, text="ArUco Tracker", font=("Segoe UI Variable Display", 18, "bold")).pack(side="left")
        self.pulse_label = ttk.Label(title_row, text=" ●", font=("Segoe UI", 14), foreground="#666666")
        self.pulse_label.pack(side="left", padx=5)

        ttk.Label(header, text=config.AUTHOR_INFO, font=("Segoe UI Variable Small", 9), foreground="#bbbbbb").pack(side="top", anchor="w", padx=(2, 0))

        # --- TABBED INTERFACE ---
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill="both", expand=True, pady=10)

        # TAB 1: SETTINGS
        self.tab_settings = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_settings, text=" ⚙ Settings ")

        # --- SETTINGS CARDS (inside tab_settings) ---
        # Camera Card
        cam_card = ttk.LabelFrame(self.tab_settings, text=" 📷 Camera & Lens ", padding="10")
        cam_card.pack(fill="x", pady=(0, 10))

        self.cameras_dict = self._get_cameras()
        camera_list = list(self.cameras_dict.keys())
        self.camera_var = tk.StringVar(value=camera_list[0] if camera_list else "")
        
        row1 = ttk.Frame(cam_card)
        row1.pack(fill="x")
        self.camera_menu = ttk.Combobox(row1, textvariable=self.camera_var, values=camera_list, state="readonly")
        self.camera_menu.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.camera_var.trace_add("write", self._update_resolutions)

        self.res_var = tk.StringVar()
        self.res_menu = ttk.Combobox(row1, textvariable=self.res_var, state="readonly", width=12)
        self.res_menu.pack(side="right")

        # Network Card
        net_card = ttk.LabelFrame(self.tab_settings, text=" 🌐 Stream & Network ", padding="10")
        net_card.pack(fill="x", pady=(0, 5))

        row2 = ttk.Frame(net_card)
        row2.pack(fill="x", pady=(0, 8))
        ttk.Label(row2, text="Mode:").pack(side="left", padx=(0, 5))
        self.mode_var = tk.StringVar(value=config.MODE_CENTER)
        self.mode_menu = ttk.Combobox(row2, textvariable=self.mode_var, 
                                         values=[config.MODE_CENTER, config.MODE_CORNERS], state="readonly", width=20)
        self.mode_menu.pack(side="left", fill="x", expand=True)

        row3 = ttk.Frame(net_card)
        row3.pack(fill="x")
        ttk.Label(row3, text="IP:").pack(side="left", padx=(0, 5))
        self.ip_entry = ttk.Entry(row3, width=15)
        self.ip_entry.insert(0, config.DEFAULT_IP)
        self.ip_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ttk.Label(row3, text="Port:").pack(side="left", padx=(0, 5))
        self.port_entry = ttk.Entry(row3, width=8)
        self.port_entry.insert(0, str(config.DEFAULT_PORT))
        self.port_entry.pack(side="left")

        # TAB 2: LOGS
        self.tab_logs = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_logs, text=" 📝 Logs ")

        self.log_text = scrolledtext.ScrolledText(self.tab_logs, height=10, state='disabled', font=("Consolas", 9), 
                                                   background="#1e1e1e", foreground="#d4d4d4", borderwidth=0)
        self.log_text.pack(fill="both", expand=True)

        # Setup Logging Handler
        self.log_handler = LogHandler(self.log_text)
        logger.addHandler(self.log_handler)

        # --- PERSISTENT FOOTER ---
        footer = ttk.Frame(main_container)
        footer.pack(fill="x", side="bottom")

        self.stats_label = ttk.Label(footer, text="FPS: -- | Packets: 0", font=("Segoe UI Variable Small", 9), foreground="#888888")
        self.stats_label.pack(side="left", pady=5)

        self.btn_stop = ttk.Button(footer, text="⏹ STOP", command=self.stop, state="disabled", width=10)
        self.btn_stop.pack(side="right", padx=(10, 0))

        self.btn_start = ttk.Button(footer, text="▶ START", command=self.start, style="Accent.TButton", width=12)
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
                args=(self._on_tracker_frame, self._on_tracker_stop, self._on_tracker_stats), 
                daemon=True
            )
            self.tracker_thread.start()
            
            self.pulse_label.config(foreground="#1DB954")
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            logger.info("Tracking session initiated.")
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid port number.")

    def stop(self):
        if self.is_running:
            self.stop_event.set()
            self.pulse_label.config(foreground="#999999")
            self.stats_label.config(text="FPS: -- | Packets: 0")
            logger.info("Stopping tracker...")

    def _on_tracker_stats(self, stats):
        fps = stats.get("fps", 0)
        fps_cam = stats.get("fps_cam", 0)
        packets = stats.get("packets", 0)
        self.root.after(0, lambda: self.stats_label.config(
            text=f"Logic: {fps} FPS | Cam: {fps_cam} FPS | Pkts: {packets}"
        ))

    def _on_tracker_frame(self, frame):
        # Only show preview if window is actually visible to save CPU
        # But cv2.imshow usually creates its own window.
        
        # Optimization: Resize is expensive for 4K. 
        # We could skip frames for preview if detection is more important.
        h, w = frame.shape[:2]
        scale = config.PREVIEW_MAX_SIZE / max(h, w)
        display_frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

        cv2.imshow(config.WINDOW_TITLE, display_frame)
        cv2.waitKey(1)

    def _on_tracker_stop(self):
        self.is_running = False
        cv2.destroyAllWindows()
        self.root.after(0, self._update_ui_to_idle)
        logger.info("Tracking stopped.")

    def _update_ui_to_idle(self):
        self.pulse_label.config(foreground="#999999")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def _update_resolutions(self, *args):
        cam_idx = self.cameras_dict.get(self.camera_var.get(), 0)
        self.res_menu.config(state="disabled")
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
