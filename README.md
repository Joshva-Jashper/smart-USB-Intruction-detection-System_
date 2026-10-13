# Smart USB Intrusion Detection System

> Detect suspicious USB HID behavior before it becomes a security incident.

Smart USB Intrusion Detection System is a cross-platform defensive security project for detecting USB Rubber Ducky and other BadUSB-style keystroke attacks. It watches USB connection events, analyzes HID typing behavior with machine learning, verifies a human with a CAPTCHA, and applies an allow/block decision through a web dashboard.

**Supported platforms:** Windows and Linux
**Runtime:** Python 3.8+
**Database:** PostgreSQL, including Neon PostgreSQL

> **Important:** This software can capture keyboard events, temporarily block input, disable USB devices, modify Windows device-installation policy, and create Linux `udev` rules. Use it only on systems and devices that you own or are authorized to administer.

## Highlights

- Real-time USB add/remove monitoring
- Random Forest analysis of HID keystroke behavior
- Detection features including typing speed, command rate, keyword rate, errors, and timing variance
- CAPTCHA-based human verification with a timeout
- Windows enforcement through `devcon.exe` and registry policy
- Linux enforcement through `udev` rules and sysfs unbinding
- Flask dashboard for device inventory and manual actions
- PostgreSQL persistence for device identity, status, threat level, and last-seen time
- Automatic operating-system selection through `os_detect.py`

## How it works

```mermaid
flowchart LR
    A[USB connected] --> B[Monitor event]
    B --> C[Read VID, PID, serial]
    C --> D[(PostgreSQL)]
    D --> E[Capture 5-second HID window]
    E --> F[ML features and rules]
    F --> G[CAPTCHA verification]
    G -->|Passed| H[Allow and whitelist]
    G -->|Failed or timed out| I[Block and mark high risk]
    H --> J[Update dashboard]
    I --> J
    J --> B
```

For a new or reconnected device, the monitor:

1. Reads the USB vendor ID (VID), product ID (PID), and serial number.
2. Looks up or creates the device record in PostgreSQL.
3. Captures keystrokes for five seconds when HID activity is present.
4. Extracts behavioral features and runs the classifier plus hard safety rules.
5. Temporarily blocks keyboard input and displays a CAPTCHA.
6. Allows verified devices or blocks failed/expired verification attempts.
7. Saves the decision and keeps monitoring for the next event.

Previously blocked devices are re-enforced when they are connected again. The Linux monitor processes device checks in background threads so event monitoring can continue.

## Repository layout

| File | Purpose |
| --- | --- |
| `os_detect.py` | Selects the Windows or Linux monitor automatically |
| `usb_monitor.py` | Windows USB event loop |
| `usb_monitor_linux.py` | Linux `pyudev` event loop |
| `ml.py` / `ml_linux.py` | Keystroke capture and ML classification |
| `allow_block.py` | Windows `devcon` and registry enforcement |
| `allow_block_linux.py` | Linux `udev` and sysfs enforcement |
| `usb_verification_handler*.py` | Keyboard blocking and CAPTCHA orchestration |
| `server.py` / `server_linux.py` | Flask dashboard API |
| `db.py` / `db_linux.py` | PostgreSQL access helpers |
| `index.html` | Dashboard frontend |
| `requirements.txt` | Python dependencies |
| `usb_ducky_detector.pkl` | Optional local ML model artifact |

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Joshva-Jashper/smart-USB-Intruction-detection-System_.git
cd smart-USB-Intruction-detection-System_
```

### 2. Create an environment and install dependencies

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyudev
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install wmi pywin32
```

Linux also needs the system utilities used by the input and device adapters:

```bash
sudo apt-get install xinput xdotool
```

### 3. Configure PostgreSQL

Create a `.env` file in the project root. The repository ignores this file, so credentials do not need to be committed.

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

Create the table used by the application:

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

### 4. Prepare device-control permissions

**Windows**

- Download the matching `devcon.exe` from the Windows Driver Kit.
- Put it in the project root or add its directory to `PATH`.
- Run the monitor from an elevated Administrator terminal.

**Linux**

- Run the monitor with `sudo` when device enforcement is required.
- Use an active X11 session for the `xinput` keyboard adapter.
- Wayland-only sessions may require adapter changes.

## Run the application

### Automatic platform selection

```bash
# Linux
sudo -E .venv/bin/python os_detect.py

# Windows Administrator PowerShell
python os_detect.py
```

The launcher starts `usb_monitor.py` on Windows and `usb_monitor_linux.py` on Linux.

### Direct launch

```bash
# Windows Administrator PowerShell
python usb_monitor.py

# Linux
sudo -E .venv/bin/python usb_monitor_linux.py
```

Startup initializes the database connection, loads or trains the model, starts the dashboard, and begins monitoring USB events. Stop the process with `Ctrl+C`.

## Dashboard

The dashboard shows known devices grouped by VID/PID and provides three actions:

| Action | Database result | Device result |
| --- | --- | --- |
| **Allow** | `whitelisted` / `low` | Enables the device through the platform adapter |
| **Block** | `blocked` / `high` | Disables the device and persists the block |
| **Remove** | Deletes VID/PID records | Does not undo an operating-system block; allow first if needed |

The Windows server uses `http://localhost:8000`. The Linux server selects a free local port and prints the URL at startup.

### API endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/` | `GET` | Serves the dashboard |
| `/devices` | `GET` | Returns grouped device records as JSON |
| `/device/<device_id>/action` | `POST` | Accepts `{"action":"allow"}`, `{"action":"block"}`, or `{"action":"remove"}` |

## Detection model

The classifier uses a five-second keystroke window and extracts features such as:

- `avg_speed` — average keys per second
- `error_rate` — backspace/delete frequency
- `command_rate` — Enter/Return frequency
- `keyword_rate` — suspicious command keyword frequency
- `variance` — timing irregularity
- `terminal_triggered` — terminal-opening pattern detection

The model predicts `HUMAN` or `USB_DUCKY`. Hard rules can override the model for extreme typing speeds or terminal-opening sequences. If `usb_ducky_detector.pkl` is missing, the applicable module trains a model at startup; model artifacts are ignored by Git by default.

## Platform support

| Capability | Windows | Linux |
| --- | --- | --- |
| USB events | `usb-monitor` polling | `pyudev` netlink events |
| Keyboard blocking | Win32 `BlockInput` | `xinput disable/enable` |
| Device enforcement | `devcon.exe` + registry policy | `udev` + sysfs unbind |
| Required privilege | Administrator | Root for enforcement |
| Dashboard port | Fixed `8000` | Dynamically selected free port |

## Troubleshooting

### Database connection errors

Check that `.env` is in the project root, `DATABASE_URL` is valid, PostgreSQL is reachable, SSL settings match the provider, and `device_details` exists.

### Devices are detected but not blocked

- Windows: confirm Administrator privileges and a compatible `devcon.exe`.
- Linux: confirm `sudo`, `udevadm`, and the generated rules under `/etc/udev/rules.d/`.
- Check that the device has a four-character VID and PID.

### CAPTCHA or keyboard blocking fails

Use a graphical session and verify the platform input utilities. Keep a recovery path available because keyboard blocking changes local input behavior.

### The dashboard is empty

The dashboard reads from PostgreSQL; it does not discover USB devices independently. Confirm that the monitor process is running and connected to the same database configured in `.env`.

## Contributing

1. Create a feature branch.
2. Test add/remove events and dashboard actions on non-critical devices.
3. Do not commit `.env`, credentials, private device identifiers, or local model artifacts.
4. Document platform-specific behavior.
5. Open a pull request with the operating system, Python version, test steps, and relevant logs.

```bash
git checkout -b feature/your-change
git add .
git commit -m "Describe your change"
git push origin feature/your-change
```

## License

This project is licensed under the [MIT License](LICENSE).
