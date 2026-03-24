import os
import subprocess
import time
import threading

_grabbed_devices = []
_grab_threads = []
_stop_event = threading.Event()

def get_keyboard_devices():
    keyboards = []
    try:
        with open("/proc/bus/input/devices", "r") as f:
            content = f.read()

        blocks = content.strip().split("\n\n")
        for block in blocks:
            if "EV=" not in block:
                continue
            lines = block.splitlines()

            name = ""
            handlers = []
            is_keyboard = False

            for line in lines:
                if line.startswith("N: Name="):
                    name = line.split("=", 1)[1].strip().strip('"')
                if line.startswith("H: Handlers="):
                    handlers = line.split("=", 1)[1].strip().split()
                if line.startswith("B: EV="):
                    ev_val = int(line.split("=")[1].strip(), 16)
                    if ev_val & 0x2:
                        is_keyboard = True

            skip_keywords = ["mouse", "pointer", "touchpad", "trackpad",
                             "trackpoint", "tablet", "stylus", "button"]
            if any(kw in name.lower() for kw in skip_keywords):
                continue

            if is_keyboard:
                for h in handlers:
                    if h.startswith("event"):
                        path = f"/dev/input/{h}"
                        if os.path.exists(path):
                            keyboards.append((path, name))

    except Exception as e:
        print(f"Error reading input devices: {e}")

    return keyboards


def _grab_and_hold(device_path, stop_event):
    import fcntl
    EVIOCGRAB = 0x40044590

    try:
        fd = open(device_path, "rb")
        fcntl.ioctl(fd, EVIOCGRAB, 1)

        while not stop_event.is_set():
            time.sleep(0.1)

        fcntl.ioctl(fd, EVIOCGRAB, 0)
        fd.close()

    except PermissionError:
        print(f"❌ Permission denied: {device_path} — run as root (sudo)")
    except Exception as e:
        print(f"❌ Error grabbing {device_path}: {e}")


def block_keyboard(seconds=None):
    global _grabbed_devices, _grab_threads, _stop_event

    if not os.geteuid() == 0:
        print("❌ Must run as root (sudo) to grab input devices")
        return False

    keyboards = get_keyboard_devices()
    if not keyboards:
        print("❌ No keyboard devices found")
        return False

    _stop_event = threading.Event()
    _grab_threads = []
    _grabbed_devices = keyboards

    for path, name in keyboards:
        t = threading.Thread(target=_grab_and_hold, args=(path, _stop_event), daemon=True)
        t.start()
        _grab_threads.append(t)

    time.sleep(0.3)
    print("🔒 KEYBOARD LOCKED")

    if seconds:
        threading.Timer(seconds, unblock_keyboard).start()

    return True


def unblock_keyboard():
    global _stop_event
    _stop_event.set()
    time.sleep(0.3)
    print("🔓 KEYBOARD UNLOCKED")
    return True


if __name__ == "__main__":
    print("Blocking keyboard for 10 seconds...")
    block_keyboard(seconds=10)
    time.sleep(12)
    print("Done.")
