import cv2
import cv2.aruco as aruco
import socket
import math
from .logger import village_logger as logger
from . import config

class ArUcoTracker:
    """Class for video stream processing and marker detection."""
    
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
        self.detector = aruco.ArucoDetector(self.aruco_dict, aruco.DetectorParameters())
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cap = None

    def _calculate_angle(self, corners):
        """Calculate 2D marker rotation angle."""
        c = corners[0]
        dx = c[1][0] - c[0][0]
        dy = c[1][1] - c[0][1]
        angle = int(math.degrees(math.atan2(dy, dx)))
        return angle + 360 if angle < 0 else angle

    def run(self, on_frame_callback=None, on_stop_callback=None):
        """Main detection loop."""
        self.cap = cv2.VideoCapture(self.camera_idx, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            logger.error(f"Could not open camera {self.camera_idx}")
            if on_stop_callback:
                on_stop_callback()
            return

        # Set resolution if provided
        if self.width and self.height:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f"Tracking started: Cam {self.camera_idx}, Res {actual_w}x{actual_h}, UDP {self.udp_port}")

        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = self.detector.detectMarkers(gray)

            if ids is not None:
                aruco.drawDetectedMarkers(frame, corners, ids)
                for marker_corners, marker_id in zip(corners, ids):
                    c = marker_corners[0]
                    
                    if self.mode == config.MODE_CORNERS:
                        # All corners mode: id;x1;y1;x2;y2;x3;y3;x4;y4
                        pts = c.flatten().astype(int)
                        msg = f"{int(marker_id[0])};" + ";".join(map(str, pts))
                        cx = int(sum(pt[0] for pt in c) / 4)
                        cy = int(sum(pt[1] for pt in c) / 4)
                        angle = self._calculate_angle(marker_corners)
                    else:
                        # Center mode: id;cx;cy;angle
                        cx = int(sum(pt[0] for pt in c) / 4)
                        cy = int(sum(pt[1] for pt in c) / 4)
                        angle = self._calculate_angle(marker_corners)
                        msg = f"{int(marker_id[0])};{cx};{cy};{angle}"

                    try:
                        self.sock.sendto(msg.encode(), (self.udp_ip, self.udp_port))
                    except Exception as e:
                        logger.debug(f"UDP send error: {e}")
                    
                    cv2.putText(frame, f"ID:{int(marker_id[0])} ang:{angle}", (cx + 10, cy), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Pass frame to callback if it exists
            if on_frame_callback:
                on_frame_callback(frame)
            
            # Since the tracker no longer has a UI, we don't call waitKey(1) here.
            # The tracker runs in its own thread, and cv2.waitKey is handled by the caller/GUI.

        self.cap.release()
        self.sock.close()
        if on_stop_callback:
            on_stop_callback()
        logger.info("Tracking stopped.")
