# 🛡️ USB Rubber Ducky Intrusion Detection System

A real-time USB threat detection system that uses **Machine Learning**, **CAPTCHA verification**, and **hardware-level blocking** to protect against USB Rubber Ducky / BadUSB attacks. 
  Supports both **Windows** and **Linux**.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Dashboard](#dashboard)
- [Database](#database)
- [Platform Notes](#platform-notes)
- [Contributing](#contributing)

---

## Overview

USB Rubber Ducky attacks disguise malicious HID (Human Interface Device) payloads as innocent USB devices. Once plugged in, they inject keystrokes at superhuman speeds to execute malicious 
  scripts — often within seconds.

This system detects such attacks by:
- Monitoring USB plug/unplug events in real time
- Capturing and analyzing keystroke patterns using a trained ML model
- Presenting a CAPTCHA challenge to verify a human is present
- Blocking or allowing the device based on the result
- Logging all device activity to a cloud PostgreSQL database
- Providing a web dashboard for manual device management

---

## Features

- 🤖 **ML-based detection** — Random Forest classifier trained on human vs. Rubber Ducky keystroke profiles
- ⌨️ **Keystroke analysis** — Measures typing speed, error rate, command rate, keyword rate, and timing variance
- 🔐 **CAPTCHA verification** — Human-presence check triggered on every new USB device
- 🔒 **Hardware-level blocking** — Uses `devcon.exe` (Windows) or `udev` rules (Linux) to physically disable devices
- 📋 **Registry policy enforcement** — Windows Group Policy deny-list via registry (survives reboots)
- 🌐 **Web dashboard** — Flask API + HTML frontend for real-time monitoring and manual allow/block/remove
- ☁️ **Cloud database** — Neon PostgreSQL for persistent device history
- 🖥️ **Cross-platform** — Full support for Windows and Linux

---

## Architecture
```
USB Device Plugged In
        │
        ▼
  USB Monitor (pyudev / usbmonitor)
        │
        ▼
  DB Lookup (Neon PostgreSQL)
  ┌─────────────────────────┐
  │ Known?  → Re-enforce    │
  │ New?    → Insert        │
  └─────────────────────────┘
        │
        ▼
  ML Analysis (5s keystroke capture)
  ┌──────────────────────────────┐
  │ Speed / Error / Command /    │
  │ Keyword Rate / Variance      │
  │ → RandomForestClassifier     │
  └──────────────────────────────┘
        │
        ▼
  CAPTCHA Verification (10s timeout)
        │
      ┌─┴─┐
   Pass   Fail / Timeout
      │         │
  ALLOW       BLOCK
  (whitelist) (devcon/udev disable + registry)
        │
        ▼
  Dashboard Updated (Flask API)
```

---

## Project Structure
```
.
├── os_detect.py                       # Entry point — auto-detects OS and launches correct monitor
│
├── # ── Windows ──────────────────────────────────────────────────
├── usb_monitor.py                     # Main USB monitoring loop (Windows)
├── ml.py                              # ML detector + keystroke capture (Windows)
├── allow_block.py                     # devcon-based allow/block (Windows)
├── registry_block.py                  # Windows registry deny-list policy
├── key_board.py                       # Keyboard input blocking via BlockInput API
├── usb_verification_handler.py        # Orchestrates keyboard block + CAPTCHA
├── captcha.py                         # CAPTCHA UI/logic
├── server.py                          # Flask API server (Windows)
├── db.py                              # Neon PostgreSQL helper (Windows)
│
├── # ── Linux ────────────────────────────────────────────────────
├── usb_monitor_linux.py               # Main USB monitoring loop (Linux / pyudev)
├── ml_linux.py                        # ML detector + keystroke capture (Linux)
├── allow_block_linux.py               # udev-based allow/block (Linux)
├── key_board_linux.py                 # Keyboard blocking via xinput (Linux)
├── usb_verification_handler_linux.py  # Orchestrates keyboard block + CAPTCHA (Linux)
├── server_linux.py                    # Flask API server (Linux)
├── db_linux.py                        # Neon PostgreSQL helper (Linux)
│
├── # ── Shared ───────────────────────────────────────────────────
├── index.html                         # Web dashboard frontend
└── usb_ducky_detector.pkl             # Pre-trained ML model (auto-generated if missing)
```

---

## Requirements

### Python 3.8+

**Common (both platforms):**
```
flask
flask-cors
psycopg2-binary
scikit-learn
numpy
pynput
```

**Windows only:**
```
usbmonitor
wmi
pywin32
```

**Linux only:**
```
pyudev
xdotool      # system package, for auto-keystroke injection during capture
```

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/usb-ducky-ids.git
cd usb-ducky-ids
```

### 2. Install Python dependencies
```bash
pip install flask flask-cors psycopg2-binary scikit-learn numpy pynput
```

**Windows:**
```bash
pip install usbmonitor wmi pywin32
```

**Linux:**
```bash
pip install pyudev
sudo apt install xdotool
```

### 3. Windows — place `devcon.exe`

Download `devcon.exe` from the Windows Driver Kit (WDK) and place it in the project root, or ensure it is on your system `PATH`.

### 4. Database

Update `DATABASE_URL` in `db.py` / `db_linux.py` with your own Neon PostgreSQL connection string.

Expected table schema:
```sql
CREATE TABLE device_details (
    id           SERIAL PRIMARY KEY,
    usb_vid      VARCHAR(4),
    usb_pid      VARCHAR(4),
    usb_serial   TEXT,
    device_type  VARCHAR(50) DEFAULT 'unknown',
    threat_level VARCHAR(50) DEFAULT 'unknown',
    last_seen    REAL
);
```

---

## Usage

### Auto-detect OS and run (recommended)
```bash
python os_detect.py
```

### Run directly

**Windows (must run as Administrator):**
```bash
python usb_monitor.py
```

**Linux:**
```bash
sudo python usb_monitor_linux.py
```

On startup the system will:
1. Connect to the database
2. Load (or train) the ML model
3. Start the Flask dashboard at `http://localhost:8000`
4. Begin monitoring USB events

---

## How It Works

### 1. Device Detection
- **Windows:** `usbmonitor` polls for USB add/remove events
- **Linux:** `pyudev` listens to kernel netlink events for the `usb_device` subsystem

### 2. ML Keystroke Analysis

When a new device is detected, the system listens for keystrokes for **5 seconds** and extracts:

| Feature | Description |
|---|---|
| `avg_speed` | Keys per second |
| `error_rate` | Backspace/Delete frequency |
| `command_rate` | Enter/Return frequency |
| `keyword_rate` | Frequency of known attack commands (e.g. `powershell`, `wget`, `reg`) |
| `variance` | Timing irregularity between keystrokes |
| `terminal_triggered` | Whether a terminal-opening pattern was detected |

A **Random Forest** classifier (100 estimators) predicts `HUMAN` or `USB_DUCKY`. Hard rules override the model for extreme cases (speed ≥ 100 keys/s or terminal sequence detected).

### 3. CAPTCHA Verification

After ML analysis, a CAPTCHA challenge is shown. The keyboard is blocked during this window (Windows: `BlockInput` API; Linux: `xinput disable`). If the user solves it within the timeout,
  the device is allowed; otherwise it is blocked.

### 4. Device Blocking

- **Windows:** Registry deny-list (`HKLM\...\DeviceInstall\Restrictions`) + `devcon.exe disable` + `gpupdate /force`
- **Linux:** `udev` rule injection + device unbind

Blocked status persists in the database and is re-enforced on every future plug-in of the same device.

---

## Dashboard

The web dashboard at `http://localhost:8000` shows all detected devices and supports three actions:

| Action | Effect |
|---|---|
| ✅ Allow | Sets `whitelisted` / `low` threat, enables device via devcon/udev |
| 🔒 Block | Sets `blocked` / `high` threat, disables device via devcon/udev |
| 🗑️ Remove | Deletes all records for that VID:PID from the database |

---

## Database

All device state is stored in Neon PostgreSQL. The helper modules include a simple 3-second cache to avoid excessive queries during dashboard refreshes.

Key operations: `insert_device`, `update_device_status`, `get_device_by_vid_pid`, `delete_device`.

---

## Platform Notes

| Feature | Windows | Linux |
|---|---|---|
| USB event source | `usbmonitor` | `pyudev` |
| Hardware block | `devcon.exe` + Registry | `udev` rules |
| Keyboard block | `BlockInput` (WinAPI) | `xinput disable` |
| Admin requirement | Run as Administrator | Run as root (`sudo`) |
| ML model file | `usb_ducky_detector.pkl` | `usb_ducky_detector.pkl` |

> ⚠️ **Windows:** Must be run as Administrator for registry writes, devcon, and keyboard blocking to work.
>
> ⚠️ **Linux:** Must be run as root (`sudo`) for udev rule enforcement. Keyboard blocking requires an active X session.

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first.

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## ⚠️ Disclaimer

This tool is intended for **defensive security research and legitimate system protection** on machines you own or have explicit authorization to monitor. Unauthorized interception of input
  devices or blocking of hardware on systems you do not own may violate applicable laws.
