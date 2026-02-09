import requests
import json
import time
import cv2

from mock_printer import MockPrinter
from camera import RealSenseCamera

# Setting up the printer
IP_ADRESS = "localhost" #When it is running on your pc
PORT = "7125"  # Moonraker
URL = f"http://{IP_ADRESS}:{PORT}"

camera = RealSenseCamera()

def get_printer_state():
    r = requests.get(f"{URL}/printer/info", timeout=3)
    r.raise_for_status()
    return r.json()["result"]["state"]

def read_printer_status():
    objects = {
        "print_stats": None,
        "virtual_sdcard": None,
        "extruder": None,
        "heater_bed": None,
        "toolhead": None
    }

    r = requests.get(
        f"{URL}/printer/objects/query",
        params={"objects": json.dumps(objects, separators=(",", ":"))},
        timeout=3
    )
    r.raise_for_status()

    status = r.json().get("result", {}).get("status", {})

    return {
        "state": status.get("print_stats", {}).get("state", "idle"),
        "filename": status.get("print_stats", {}).get("filename"),
        "progress": status.get("virtual_sdcard", {}).get("progress"),
        "extruder_temp": status.get("extruder", {}).get("temperature"),
        "extruder_target": status.get("extruder", {}).get("target"),
        "bed_temp": status.get("heater_bed", {}).get("temperature"),
        "bed_target": status.get("heater_bed", {}).get("target"),
        "position": status.get("toolhead", {}).get("position"),
    }

def get_camera_snapshot():
    try:
        return camera.save_snapshot("Snapshot")
    except Exception as e:
        print("Snapshot error:", e)
        return None

if __name__ == "__main__":
    # before the print starts (head is home)
    print("Printer:", get_printer_state())
    path=get_camera_snapshot()
    print("Snapshot saved:", path, flush=True)
    # check if the area is clear?
    # check the other values
    # Then proceed for the first layer
    # pause the print after the first layer
    # check (head home, snapshot, analyze)

    while True:
        s = read_printer_status()
        print(s)
        time.sleep(2)