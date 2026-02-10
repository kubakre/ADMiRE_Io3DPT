import requests
import json
import time
import cv2
import os
from datetime import datetime

from mock_printer import MockPrinter
from camera import RealSenseCamera
from command_printer import PrinterControl
from image_analysis import SnapshotAnalysis

#Setting up the printer
IP_ADRESS = "localhost" #When it is running on your pc
PORT = "7125"  # Moonraker
URL = f"http://{IP_ADRESS}:{PORT}"

camera = RealSenseCamera()
printer = PrinterControl(URL)

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

def get_layer():
    try:
        #Must use Timelapse plugin in Klipper or find a different way
        response = requests.get(f"{URL}/printer/objects/query?objects={{'timelapse': null}}")
        response.raise_for_status()

        data = response.json()
        layer = data.get("result", {}).get("status", {}).get("timelapse", {}).get("current_layer", None)

        return layer
    except Exception as e:
        print(f"Error getting layer info: {e}")
        return None

def get_camera_snapshot():
    try:
        return camera.save_snapshot("Snapshot")
    except Exception as e:
        print("Snapshot error:", e)
        return None

def get_latest_snapshot(directory="Snapshot"):
    #Finds the most recent snapshot in the directory based on the filename timestamp.
    snapshot_files = [f for f in os.listdir(directory) if f.startswith("snapshot_") and f.endswith(".jpg")]

    if not snapshot_files:
        print("No snapshots found in the directory.")
        return None

    snapshot_files.sort(key=lambda f: datetime.strptime(f, "snapshot_%Y%m%d_%H%M%S_%f.jpg"), reverse=True)

    latest_snapshot = os.path.join(directory, snapshot_files[0])
    print(f"Latest snapshot found: {latest_snapshot}")

    return latest_snapshot

def analyze_snapshot():
    latest_snapshot = get_latest_snapshot("Snapshot")

    if latest_snapshot is not None:
        analyzer = SnapshotAnalysis(image=None)
        analyzer.load_image(latest_snapshot)

        edges = analyzer.analyze_edges()
        analyzer.save_result(edges, latest_snapshot, suffix="_ed")

        contours = analyzer.analyze_contours()
        analyzer.save_result(contours, latest_snapshot, suffix="_cont")

        #AI analysis (need to decide whether find some model or train my own)
        #result = analyzer.ai_inference()
        #analyzer.save_result(result, latest_snapshot, suffix="_ai")

    else:
        print("No snapshot found to analyze.")

if __name__ == "__main__":
    #before the print starts (head is home)
    #printer.move_toolhead() #set the home coordinates
    print("Printer:", get_printer_state())
    path=get_camera_snapshot()
    print("Snapshot saved:", path, flush=True)
    #check if the area is clear? (NN)
    #check the other values
    #Then proceed for the first layer
    current_layer = 1 #get_layer()
    if current_layer == 1:
        print("First layer check")
        printer.stop_print()
        #printer.move_toolhead() #set the home coordinates
        path = get_camera_snapshot()
        print("Snapshot saved:", path, flush=True)
        analyze_snapshot()

    #check (head home, snapshot, analyze)
    #LLM or NN?
    print("Continuing printing...", flush=True)
    while True:
        s = read_printer_status()
        print(s)
        time.sleep(2)