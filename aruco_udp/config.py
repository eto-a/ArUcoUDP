import cv2.aruco as aruco

# Configuration constants for ArUco UDP Tracker

# Networking
DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 5005

# Marker Dictionary (AprilTag 36h11)
ARUCO_DICT_TYPE = aruco.DICT_APRILTAG_36h11

# Data Modes
MODE_CENTER = "Center + Angle"
MODE_CORNERS = "All Corners"

# UI Settings
WINDOW_TITLE = "ArUco UDP Tracker"
WINDOW_SIZE = "480x320"
THEME = "dark"

# Detection Settings
PREVIEW_MAX_SIZE = 640
