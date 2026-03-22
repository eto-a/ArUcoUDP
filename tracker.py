import cv2
import cv2.aruco as aruco
import socket
import math

class ArUcoTracker:
    """Класс для обработки видеопотока и детекции маркеров."""
    
    def __init__(self, camera_idx, udp_port, stop_event):
        self.camera_idx = camera_idx
        self.udp_port = udp_port
        self.stop_event = stop_event
        self.udp_ip = "127.0.0.1"
        
        # Инициализация словаря (AprilTag 36h11)
        self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_APRILTAG_36h11)
        self.detector = aruco.ArucoDetector(self.aruco_dict, aruco.DetectorParameters())
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cap = None

    def _calculate_angle(self, corners):
        """Вычисляет 2D угол поворота маркера."""
        c = corners[0]
        dx = c[1][0] - c[0][0]
        dy = c[1][1] - c[0][1]
        angle = int(math.degrees(math.atan2(dy, dx)))
        return angle + 360 if angle < 0 else angle

    def run(self, on_stop_callback=None):
        """Основной цикл детекции."""
        self.cap = cv2.VideoCapture(self.camera_idx)
        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.camera_idx}")
            if on_stop_callback:
                on_stop_callback()
            return

        print(f"Tracking started: Cam {self.camera_idx}, UDP {self.udp_port}")

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
                    cx = int(sum(pt[0] for pt in c) / 4)
                    cy = int(sum(pt[1] for pt in c) / 4)
                    angle = self._calculate_angle(marker_corners)
                    
                    msg = f"{int(marker_id[0])};{cx};{cy};{angle}"
                    try:
                        self.sock.sendto(msg.encode(), (self.udp_ip, self.udp_port))
                    except Exception:
                        pass
                    
                    cv2.putText(frame, f"ID:{int(marker_id[0])} ang:{angle}", (cx + 10, cy), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            cv2.imshow("ArUco Reader", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()
        self.sock.close()
        if on_stop_callback:
            on_stop_callback()
        print("Tracking stopped.")
