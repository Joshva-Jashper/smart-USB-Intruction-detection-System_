# Smart USB Intrusion Detection System

Smart USB Intrusion Detection System is a complete cross-platform security application for detecting and controlling USB Rubber Ducky and BadUSB-style attacks. It monitors USB devices in real time, analyzes HID keystroke behavior, verifies the user with a CAPTCHA, blocks suspicious devices, and displays device activity in a web dashboard.

The application is implemented for **Windows and Linux** with PostgreSQL persistence, machine-learning analysis, keyboard protection, and operating-system-level USB blocking.

> **Security use:** Run this application only on systems and USB devices that you own or are authorized to administer.

## Features

- Real-time USB device detection
- Windows and Linux support
- Machine-learning detection of suspicious HID keystroke behavior
- Five-second keystroke analysis window
- CAPTCHA verification for every detected device
- Temporary keyboard protection during verification
- Automatic allow or block decisions
- Windows device blocking with `devcon.exe` and registry policy
- Linux device blocking with `udev` rules and sysfs controls
- PostgreSQL device records and status history
- Flask web dashboard for monitoring and manual device control
- Automatic operating-system selection
- Persistent re-blocking of devices previously marked as blocked

## Workflow

```mermaid
flowchart TD
    A[USB device connected] --> B[USB monitor detects event]
    B --> C[Read VID, PID and serial number]
    C --> D[Read or create PostgreSQL record]
    D --> E[Capture HID keystrokes for 5 seconds]
    E --> F[Extract behavior features]
    F --> G[Machine-learning analysis]
    G --> H[CAPTCHA verification]
    H -->|Verified| I[Allow device]
    H -->|Not verified or timeout| J[Block device]
    I --> K[Save status and refresh dashboard]
    J --> K
    K --> B
```

When a USB device is connected, the system:

1. Detects the connection event.
2. Reads the device vendor ID, product ID, and serial number.
3. Checks the device record in PostgreSQL.
4. Captures and analyzes HID keystrokes.
5. Runs the machine-learning detector and security rules.
6. Shows a CAPTCHA while protecting keyboard input.
7. Allows verified devices and blocks devices that fail verification.
8. Saves the result and updates the dashboard.

Previously blocked devices are blocked again automatically when they are connected.

## Project structure

| File | Description |
| --- | --- |
| `os_detect.py` | Detects the operating system and starts the correct monitor |
| `usb_monitor.py` | Windows USB monitoring and device-processing workflow |
| `usb_monitor_linux.py` | Linux USB monitoring and device-processing workflow |
| `ml.py` | Windows keystroke capture and machine-learning analysis |
| `ml_linux.py` | Linux keystroke capture and machine-learning analysis |
| `allow_block.py` | Windows `devcon` and registry device control |
| `allow_block_linux.py` | Linux `udev` and sysfs device control |
| `key_board.py` | Windows keyboard protection |
| `key_board_linux.py` | Linux keyboard protection through `xinput` |
| `usb_verification_handler.py` | Windows CAPTCHA and verification workflow |
| `usb_verification_handler_linux.py` | Linux CAPTCHA and verification workflow |
| `captcha.py` | CAPTCHA interface and verification logic |
| `server.py` | Windows Flask dashboard server |
| `server_linux.py` | Linux Flask dashboard server |
| `db.py` | Windows PostgreSQL helper |
| `db_linux.py` | Linux PostgreSQL helper |
| `index.html` | Web dashboard frontend |
| `requirements.txt` | Python dependencies |
| `usb_ducky_detector.pkl` | Machine-learning model file |

## Requirements

- Python 3.8 or newer
- PostgreSQL database
- Existing `.env` file in the project root
- Administrator privileges on Windows
- Root privileges on Linux for USB enforcement
- A graphical desktop session for CAPTCHA verification

### Windows requirements

- Windows Administrator terminal
- `devcon.exe` in the project root or available on `PATH`
- Python packages from `requirements.txt`
- `wmi` and `pywin32`

### Linux requirements

- `sudo` access
- `pyudev`
- `xinput`
- `xdotool`
- An active X11 desktop session

## Installation

### Clone the repository

```bash
git clone https://github.com/Joshva-Jashper/smart-USB-Intruction-detection-System_.git
cd smart-USB-Intruction-detection-System_
```

### Create the Python environment

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyudev
sudo apt-get install xinput xdotool
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install wmi pywin32
```

### Configure the existing `.env` file

The application reads the PostgreSQL connection string from the `.env` file in the project root:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

Keep the existing `.env` file private and never commit its credentials.

The required PostgreSQL table is:

```sql
CREATE TABLE IF NOT EXISTS device_details (
    id           SERIAL PRIMARY KEY,
    usb_vid      VARCHAR(4) NOT NULL,
    usb_pid      VARCHAR(4) NOT NULL,
    usb_serial   TEXT,
    device_type  VARCHAR(50) DEFAULT 'unknown',
    threat_level VARCHAR(50) DEFAULT 'unknown',
    last_seen    REAL
);
```

### Configure Windows device control

Place the correct `devcon.exe` file in the project root or add it to the system `PATH`. The Windows monitor must be started from an Administrator terminal.

## Start the application

### Automatic operating-system detection

Linux:

```bash
sudo -E .venv/bin/python os_detect.py
```

Windows Administrator PowerShell:

```powershell
python os_detect.py
```

The launcher starts `usb_monitor.py` on Windows and `usb_monitor_linux.py` on Linux.

### Start the platform monitor directly

Windows Administrator PowerShell:

```powershell
python usb_monitor.py
```

Linux:

```bash
sudo -E .venv/bin/python usb_monitor_linux.py
```

The application connects to PostgreSQL, loads the machine-learning model, starts the Flask dashboard, and begins monitoring USB events.

Stop the application with `Ctrl+C`.

## Dashboard

The dashboard displays detected devices grouped by VID and PID. It provides the following actions:

| Action | Result |
| --- | --- |
| **Allow** | Marks the device `whitelisted` with `low` threat and enables it |
| **Block** | Marks the device `blocked` with `high` threat and disables it |
| **Remove** | Removes the device records for the selected VID/PID |

Dashboard URLs:

- **Windows:** `http://localhost:8000`
- **Linux:** the application prints the selected local port at startup

### Dashboard API

| Endpoint | Method | Description |
| --- | --- | --- |
| `/` | `GET` | Opens the dashboard |
| `/devices` | `GET` | Returns the device list as JSON |
| `/device/<device_id>/action` | `POST` | Performs an allow, block, or remove action |

Example request:

```json
{
  "action": "block"
}
```

## Machine-learning detection

The detector captures HID activity for five seconds and analyzes:

| Feature | Description |
| --- | --- |
| `avg_speed` | Average keys per second |
| `error_rate` | Backspace and delete frequency |
| `command_rate` | Enter and Return frequency |
| `keyword_rate` | Frequency of suspicious command keywords |
| `variance` | Timing variation between keystrokes |
| `terminal_triggered` | Terminal-opening pattern detection |

The model classifies activity as `HUMAN` or `USB_DUCKY`. Security rules also identify extreme typing speeds and terminal-opening sequences.

## Platform implementation

| Capability | Windows | Linux |
| --- | --- | --- |
| USB event monitoring | `usb-monitor` | `pyudev` |
| Keyboard protection | Win32 `BlockInput` | `xinput` |
| USB blocking | `devcon.exe` and registry policy | `udev` and sysfs controls |
| Database helper | `db.py` | `db_linux.py` |
| Dashboard server | Port `8000` | Automatically selected local port |

## License

This project is licensed under the [MIT License](LICENSE).

## Contributing

1. Create a feature branch.
2. Test changes on a non-critical device.
3. Keep `.env` credentials and private device information out of commits.
4. Include platform details and test steps in pull requests.

```bash
git checkout -b feature/your-change
git add .
git commit -m "Describe your change"
git push origin feature/your-change
```
