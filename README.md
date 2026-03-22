# ArUco & AprilTag UDP Tracker

A lightweight, real-time computer vision tool designed to detect **AprilTag (36h11)** and **ArUco** markers via webcam and broadcast their coordinates over the network using the **UDP protocol**.

Ideal for robotics, interactive installations, position tracking, and integrating computer vision data into engines like Unity, Unreal Engine, or TouchDesigner without the overhead of heavy frameworks.

---

## 🏁 Markers

This project is configured to work with the **AprilTag 36h11** dictionary.

- **Generate Markers**: You can generate tags online at [chev.me/arucogen](https://chev.me/arucogen/).
- **Selection**: Make sure to select **"AprilTag 36h11"** from the dictionary dropdown menu before printing.

---

## 🚀 Key Features

- **Multi-Marker Detection**: Simultaneously track multiple tags with high precision.
- **UDP Data Streaming**: Low-latency coordinate transmission (`id;x;y;angle`).
- **User Interface**: Simple GUI to select cameras, set destination IP/Port, and preview detection.
- **Pre-built Windows Binary**: No Python installation required for end-users (see [Releases](https://github.com/eto-a/ArUcoUDP/releases)).
- **Testing Tools**: Includes a built-in UDP receiver utility for verification.

---

## 🛠️ Installation

### From Source
1. Clone the repository:
   ```bash
   git clone https://github.com/eto-a/ArUcoUDP.git
   cd ArUcoUDP
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🖥️ Usage

### Run with Python
```bash
python main.py
```

### Protocol Format
The app sends UDP packets in the following plain text format:
`id;x;y;angle`
- **id**: Unique marker ID.
- **x, y**: Center coordinates of the tag in pixels.
- **angle**: Rotation angle in degrees (0-360°).

### Verification
To test if your system is receiving data, run the included receiver utility:
```bash
python udp_receiver.py
```

---

## 🔨 Build Instructions (EXE)

To bundle the application into a standalone Windows executable:
```bash
pyinstaller main.spec
```
The output file `ArUcoTracker.exe` will be generated in the `dist/` directory.

---

## 📁 Project Structure

- `tracker.py`: Core detection logic and UDP sender.
- `interface.py`: GUI implementation and threading.
- `main.py`: Application entry point.
- `udp_receiver.py`: Utility for testing incoming UDP data.
- `main.spec`: PyInstaller configuration.

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.
