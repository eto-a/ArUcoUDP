import cv2
import cv2.aruco as aruco
import socket
import math
import time
import threading
from .logger import village_logger as logger
from . import config

class BufferedCamera:
    """Thread-safe camera wrapper that always provides the latest frame."""
    def __init__(self, camera_idx, width=None, height=None):
        self.cap = cv2.VideoCapture(camera_idx, cv2.CAP_DSHOW)
        if width and height:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        self.ret = False
        self.frame = None
        self.running = True
        self.lock = threading.Lock()
        
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        
        # Stats
        self.fps_capture = 0
        self._frame_count = 0
        self._last_stats_time = time.time()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            with self.lock:
                self.ret = ret
                self.frame = frame
            
            self._frame_count += 1
            now = time.time()
            if now - self._last_stats_time >= 1.0:
                self.fps_capture = self._frame_count / (now - self._last_stats_time)
                self._frame_count = 0
                self._last_stats_time = now

    def read(self):
        with self.lock:
            return self.ret, self.frame

    def release(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.cap.release()

class ArUcoTracker:
    """Class for video stream processing and marker detection with ROI support."""
    
    def __init__(self, camera_idx, udp_port, udp_ip, stop_event, mode=config.MODE_CENTER, width=None, height=None):
        self.camera_idx = camera_idx
        self.udp_port = udp_port
        self.udp_ip = udp_ip
        self.mode = mode
        self.stop_event = stop_event
        self.width = width
        self.height = height
        
        # Marker dictionary initialization (AprilTag 36h11)
        self.aruco_dict = aruco.getPredefinedDictionary(config.ARUCO_DICT_TYPE)
        
        # Optimized parameters for speed and small markers
        params = aruco.DetectorParameters()
        params.adaptiveThreshWinSizeStep = config.DETECTION_ADAPTIVE_STEP
        # Increase subpixel accuracy as markers are small
        params.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX
        
        self.detector = aruco.ArucoDetector(self.aruco_dict, params)
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cap = None
        
        # ROI Tracking state
        self.roi_box = None # (x, y, w, h)
        self.roi_padding = config.ROI_PADDING
        self.consecutive_lost = 0
        self.max_lost_frames = config.ROI_LOST_FRAMES

    def _calculate_angle(self, corners):
        """Calculate 2D marker rotation angle."""
        c = corners[0]
        dx = c[1][0] - c[0][0]
        dy = c[1][1] - c[0][1]
        angle = int(math.degrees(math.atan2(dy, dx)))
        return angle + 360 if angle < 0 else angle

    def run(self, on_frame_callback=None, on_stop_callback=None, on_stats_callback=None):
        """Main detection loop."""
        self.cap = BufferedCamera(self.camera_idx, self.width, self.height)
        
        # Ensure we have a first frame to get dimensions
        ret, frame = False, None
        timeout = time.time() + 5.0
        while time.time() < timeout:
            ret, frame = self.cap.read()
            if ret and frame is not None: break
            time.sleep(0.1)
        
        if not ret or frame is None:
            logger.error(f"Could not open camera {self.camera_idx}")
            self.cap.release()
            if on_stop_callback:
                on_stop_callback()
            return

        actual_h, actual_w = frame.shape[:2]
        logger.info(f"Tracking started: Cam {self.camera_idx}, Res {actual_w}x{actual_h}, UDP {self.udp_port}")

        packet_count = 0
        logic_frame_count = 0
        last_stats_time = time.time()

        while not self.stop_event.is_set():
            ret, full_frame = self.cap.read()
            if not ret or full_frame is None:
                time.sleep(0.001)
                continue

            # 1. Prepare frame (ROI or Full)
            if self.roi_box:
                x, y, w, h = self.roi_box
                # Boundary checks
                x1, y1 = max(0, x), max(0, y)
                x2, y2 = min(actual_w, x + w), min(actual_h, y + h)
                roi_frame = full_frame[y1:y2, x1:x2]
                offset = (x1, y1)
            else:
                roi_frame = full_frame
                offset = (0, 0)

            # 2. Detect
            gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = self.detector.detectMarkers(gray)

            # 3. Process Results
            if ids is not None:
                self.consecutive_lost = 0
                # Transpose corners back to full frame coordinates
                if self.roi_box:
                    for i in range(len(corners)):
                        corners[i][:, :, 0] += offset[0]
                        corners[i][:, :, 1] += offset[1]

                aruco.drawDetectedMarkers(full_frame, corners, ids)
                
                # Update ROI for next frame based on detected markers
                min_x = int(min(c[0][:, 0].min() for c in corners)) - self.roi_padding
                max_x = int(max(c[0][:, 0].max() for c in corners)) + self.roi_padding
                min_y = int(min(c[0][:, 1].min() for c in corners)) - self.roi_padding
                max_y = int(max(c[0][:, 1].max() for c in corners)) + self.roi_padding
                self.roi_box = (min_x, min_y, max_x - min_x, max_y - min_y)

                for marker_corners, marker_id in zip(corners, ids):
                    c = marker_corners[0]
                    cx = int(sum(pt[0] for pt in c) / 4)
                    cy = int(sum(pt[1] for pt in c) / 4)
                    angle = self._calculate_angle(marker_corners)

                    if self.mode == config.MODE_CORNERS:
                        pts = c.flatten().astype(int)
                        msg = f"{int(marker_id[0])};" + ";".join(map(str, pts))
                    else:
                        msg = f"{int(marker_id[0])};{cx};{cy};{angle}"

                    try:
                        self.sock.sendto(msg.encode(), (self.udp_ip, self.udp_port))
                        packet_count += 1
                    except Exception as e:
                        logger.debug(f"UDP send error: {e}")
                    
                    cv2.putText(full_frame, f"ID:{int(marker_id[0])} ang:{angle}", (cx + 10, cy), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                self.consecutive_lost += 1
                if self.consecutive_lost >= self.max_lost_frames:
                    self.roi_box = None # Reset to full frame search

            # Draw ROI debug box if active
            if self.roi_box:
                rx, ry, rw, rh = self.roi_box
                cv2.rectangle(full_frame, (rx, ry), (rx + rw, ry + rh), (255, 0, 0), 2)

            # Pass frame's metadata/stats periodically
            logic_frame_count += 1
            curr_time = time.time()
            if curr_time - last_stats_time >= 0.5:
                fps_logic = logic_frame_count / (curr_time - last_stats_time)
                if on_stats_callback:
                    on_stats_callback({
                        "fps": round(fps_logic, 1), 
                        "fps_cam": round(self.cap.fps_capture, 1),
                        "packets": packet_count
                    })
                logic_frame_count = 0
                last_stats_time = curr_time

            # Pass frame to callback if it exists
            if on_frame_callback:
                on_frame_callback(full_frame)

        self.cap.release()
        self.sock.close()
        if on_stop_callback:
            on_stop_callback()
        logger.info("Tracking stopped.")
