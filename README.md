# USB Rubber Ducky Intrusion Detection System

A cross-platform defensive security tool that monitors USB devices, analyzes HID keystroke behavior, verifies human presence with a CAPTCHA, and records or enforces the resulting device decision. The project supports **Windows** and **Linux** and includes a Flask dashboard for reviewing and managing detected devices.

> **Security notice:** Use this project only on computers and USB devices that you own or are explicitly authorized to monitor. It can intercept keyboard input, disable hardware, write Windows policy, and create Linux `udev` rules.

## What the system does

The application follows a dynamic, event-driven workflow whenever a USB device is connected:

1. Detect the USB add event.
2. Read the device vendor ID (VID), product ID (PID), and serial number.
3. Look up the device in PostgreSQL and update its last-seen information.
4. Capture keystrokes for five seconds and extract behavioral features.
5. Classify the behavior as human-like or potentially Rubber Ducky-like.
6. Temporarily block keyboard input and show a CAPTCHA challenge.
7. Allow or block the device according to the verification result.
8. Persist the status and expose it through the dashboard.
9. Re-enforce a previous block when the same device is plugged in again.

The monitor continues running after each device is processed. On Linux, each device is processed in a background thread so the event listener can continue receiving new USB events.

## Features

- **Real-time USB monitoring** using `usb-monitor` on Windows and `pyudev` on Linux.
- **Keystroke behavior analysis** with a Random Forest model.
- **Rule-based overrides** for extreme typing speeds and terminal-opening sequences.
- **CAPTCHA verification** with a ten-second timeout.
- **Device enforcement** through `devcon.exe` and Windows registry policy, or Linux `udev` rules and sysfs unbinding.
- **Flask dashboard** for viewing detected devices and manually allowing, blocking, or removing them.
- **Neon/PostgreSQL persistence** for device identity, status, threat level, serial numbers, and last-seen time.
- **Automatic OS selection** through `os_detect.py`.
- **Pre-trained model support** through `usb_ducky_detector.pkl` when a model artifact is available.

## Architecture and dynamic workflow

```mermaid
flowchart TD
    A[USB device connected] --> B{Operating system}
    B -->|Windows| C[usb_monitor.py<br/>usb-monitor polling]
    B -->|Linux| D[usb_monitor_linux.py<br/>pyudev events]
    C --> E[Normalize VID PID serial]
    D --> E
    E --> F{Known VID/PID?}
    F -->|Yes| G[Load status<br/>and update serial/last_seen]
    F -->|No| H[Insert device<br/>as unknown]
    G --> I[Capture keystrokes<br/>for 5 seconds]
    H --> I
    I --> J[Extract speed, errors,<br/>commands, keywords, variance]
    J --> K[Random Forest +<br/>hard-rule checks]
    K --> L[Block keyboard<br/>and show CAPTCHA]
    L -->|Verified| M[Allow device<br/>whitelisted / low]
    L -->|Failed or timeout| N[Block device<br/>blocked / high]
    M --> O[Persist decision]
    N --> O
    O --> P[Dashboard refreshes<br/>GET /devices]
    P --> Q{Device unplugged?}
    Q -->|Yes| R[Clear active tracking key]
    R --> A
    Q -->|No| A
```

### Decision states

| State | Database values | Enforcement behavior |
| --- | --- | --- |
| New | `unknown` / `unknown` | Analyze and verify before allowing or blocking |
| Verified | `whitelisted` / `low` | Enable the device through the platform adapter |
| Blocked | `blocked` / `high` | Disable the device and re-enforce the block on later plug-ins |

The dashboard groups records by VID/PID and shows multiple serials/interfaces together. A dashboard **Remove** action deletes all database records matching that VID/PID; it does not itself undo an operating-system block, so use **Allow** first when appropriate.

## Project structure

```text
.
├── os_detect.py                         # Selects the Windows or Linux monitor
├── usb_monitor.py                       # Windows event loop and processing pipeline
├── usb_monitor_linux.py                 # Linux pyudev event loop and processing pipeline
├── ml.py                                # Windows keystroke capture and classifier
├── ml_linux.py                          # Linux keystroke capture and classifier
├── allow_block.py                       # Windows devcon and registry enforcement
├── allow_block_linux.py                 # Linux udev and sysfs enforcement
├── key_board.py                         # Windows keyboard blocking
├── key_board_linux.py                   # Linux xinput keyboard blocking
├── usb_verification_handler.py          # Windows CAPTCHA orchestration
├── usb_verification_handler_linux.py    # Linux CAPTCHA orchestration
├── captcha.py                           # CAPTCHA UI and verification logic
├── server.py                            # Windows Flask dashboard API
├── server_linux.py                      # Linux Flask dashboard API
├── db.py                                # Windows database helper
├── db_linux.py                          # Linux database helper
├── index.html                           # Dashboard frontend
├── requirements.txt                     # Python dependencies
├── devcon.exe                           # Windows device-control binary, if supplied
└── usb_ducky_detector.pkl               # Optional generated/model artifact
```

## Requirements

- Python **3.8 or newer** (Python 3.11+ recommended).
- A PostgreSQL database. The code is designed for Neon PostgreSQL but any compatible PostgreSQL connection can be used.
- Administrator/root privileges for device enforcement.
- A graphical session for the CAPTCHA UI.

### Platform dependencies

| Platform | Python dependencies | System requirements |
| --- | --- | --- |
| Windows | Dependencies in `requirements.txt`; `wmi` and `pywin32` may be needed by the Windows modules | Run as Administrator; `devcon.exe` from the Windows Driver Kit (WDK) in the project root or on `PATH` |
| Linux | Dependencies in `requirements.txt`; install `pyudev` if it is not already available | `udevadm`, `xinput`, an active X session, and root privileges for enforcement |

The repository's `requirements.txt` contains the shared runtime dependencies. Platform-specific packages may need to be installed separately because the source has separate Windows and Linux adapters.

## Installation

### 1. Clone and enter the repository

```bash
git clone https://github.com/Joshva-Jashper/smart-USB-Intruction-detection-System_.git
cd smart-USB-Intruction-detection-System_
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\\Scripts\\activate    # Windows PowerShell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install platform-specific packages when needed:

```bash
# Windows PowerShell
python -m pip install wmi pywin32

# Linux
python -m pip install pyudev
sudo apt-get install xinput xdotool
```

### 3. Configure PostgreSQL

Create a `.env` file in the repository root. Do not commit it.

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

Create the database table before the first run:

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

`db.py` and `db_linux.py` load `DATABASE_URL` from `.env` and maintain a short in-memory cache for dashboard reads. Keep database credentials private.

### 4. Windows device control

Download the matching `devcon.exe` from the Windows Driver Kit and place it in the repository root, or add its directory to `PATH`. Run the monitor from an **elevated Administrator terminal**.

## Running the system

### Recommended: automatic OS selection

```bash
# Linux: use an elevated shell for enforcement
sudo -E .venv/bin/python os_detect.py

# Windows: run PowerShell as Administrator
python os_detect.py
```

`os_detect.py` selects `usb_monitor.py` on Windows and `usb_monitor_linux.py` on Linux.

### Run a platform monitor directly

```bash
# Windows, Administrator PowerShell
python usb_monitor.py

# Linux
sudo -E .venv/bin/python usb_monitor_linux.py
```

At startup, the monitor initializes the database, loads or trains the model, starts the Flask dashboard, and begins listening for USB events. Open the dashboard at:

- **Windows:** `http://localhost:8000`
- **Linux:** the monitor prints the dynamically selected local port, for example `http://127.0.0.1:49152`

Stop the monitor with `Ctrl+C`.

## Dashboard API

The Flask dashboard is served by the platform-specific server module.

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/` | `GET` | Serves `index.html` |
| `/devices` | `GET` | Returns grouped device records as JSON |
| `/device/<device_id>/action` | `POST` | Performs `allow`, `block`, or `remove` |

Example action payload:

```json
{"action": "block"}
```

Dashboard actions update PostgreSQL first. Allow/block enforcement then runs in a background operation using the platform adapter.

## Machine-learning workflow

For HID-like devices, the monitor captures a five-second keystroke window and extracts features such as:

| Feature | Meaning |
| --- | --- |
| `avg_speed` | Average keys per second |
| `error_rate` | Backspace/delete frequency |
| `command_rate` | Enter/Return frequency |
| `keyword_rate` | Frequency of suspicious command keywords |
| `variance` | Timing irregularity between keystrokes |
| `terminal_triggered` | Whether a terminal-opening pattern was observed |

The classifier predicts `HUMAN` or `USB_DUCKY`. Extreme patterns can trigger hard-rule decisions independently of the model. Non-HID devices or devices that produce no captured keystrokes continue to the CAPTCHA step.

If `usb_ducky_detector.pkl` is absent, the relevant ML module trains a model at startup. Model artifacts are ignored by Git by default; keep a known-good artifact locally if you want to avoid retraining.

## Platform behavior and limitations

| Capability | Windows | Linux |
| --- | --- | --- |
| USB event source | `usb-monitor` polling | `pyudev` netlink events |
| Keyboard blocking | Win32 `BlockInput` | `xinput disable/enable` |
| Device blocking | `devcon.exe` plus registry policy | `udev` rule plus sysfs unbind |
| Privilege | Administrator | Root for enforcement |
| Dashboard port | Fixed port `8000` | Dynamically selected free port |

Important limitations:

- Keyboard blocking and CAPTCHA behavior require a usable graphical session.
- Linux keyboard blocking depends on X11-compatible `xinput`; Wayland environments may require adaptation.
- Missing `devcon.exe`, missing `udev` permissions, or missing system utilities can leave hardware enforcement unavailable even if the dashboard and database are working.
- The project is a defensive prototype. Test with non-critical devices in an isolated environment before enabling enforcement on a daily-use computer.

## Troubleshooting

### `DATABASE_URL` is missing or PostgreSQL cannot connect

Confirm that `.env` is in the repository root, the URL is valid, SSL settings match your provider, and the `device_details` table exists.

### The dashboard loads but no devices appear

Check that the monitor process is running, that the correct platform module was selected, and that the database connection is available. The dashboard reads from PostgreSQL; it does not discover USB devices by itself.

### Devices are detected but not blocked

- Windows: verify Administrator privileges and that `devcon.exe` is present and compatible.
- Linux: run with `sudo`, confirm `udevadm` is available, and inspect the generated rules under `/etc/udev/rules.d/`.
- Confirm that the device has a valid four-character VID and PID.

### CAPTCHA or keyboard blocking fails

Use a graphical session, verify the required input utilities, and test the platform keyboard adapter independently. Always keep a recovery path available because keyboard blocking changes local input behavior.

## Development and contribution

Before opening a pull request:

1. Run the appropriate monitor in a safe test environment.
2. Test device add/remove events and dashboard actions.
3. Confirm that `.env`, credentials, and local model artifacts are not committed.
4. Document platform-specific changes.

```bash
git checkout -b feature/your-change
git add .
git commit -m "Describe your change"
git push origin feature/your-change
```

Pull requests and issue reports are welcome. Include your operating system, Python version, command used, and relevant logs when reporting a problem. Do not include database credentials or private device identifiers.

## License

No license file is currently included in the repository. Until a license is added, treat the source as available for review and collaboration only, and obtain permission before redistributing it.
