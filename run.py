import requests
import json
import time
import os
import base64

from camera import RealSenseCamera
from command_printer import PrinterControl
from image_analysis import SnapshotAnalysis
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

#API key (Probably good idea to hide it)
load_dotenv()
OPENAI_API_KEY = "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"  # enter your openai api key here
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key.")

# Configuration Klipper/Moonraker
IP_ADDRESS = "localhost"
PORT = "7125"
URL = f"http://{IP_ADDRESS}:{PORT}"

# Initialization
camera = RealSenseCamera()
printer = PrinterControl(URL)
client = OpenAI(api_key=OPENAI_API_KEY)

def load_prompt(name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "prompts", name)

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Error: {name} not found.")
        return ""

def get_printer_state():
    try:
        r = requests.get(f"{URL}/printer/info", timeout=3)
        r.raise_for_status()
        return r.json()["result"]["state"]
    except requests.RequestException as e:
        print(f"Printer not connected: {e}")
        return "error"

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
        #Can I get that from initial data?
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
        path = camera.save_snapshot("Snapshot")
        return path
    except Exception as e:
        print("Camera error:", e)
        return None

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def analyze_snapshot(image_path, prompt_text):
    if not image_path or not os.path.exists(image_path):
        print("Error: There is no snapshot to analyze.")
        return

    # This is for local analysis
    # try:
    #     analyzer = SnapshotAnalysis(image=None)
    #     analyzer.load_image(image_path)
    #     edges = analyzer.analyze_edges()
    #     analyzer.save_result(edges, image_path, suffix="_ed")
    # except Exception as e:
    #     print(f"Error during CV analysis: {e}")

    # LLM analysis
    print("I am sending it to LLM for analysis...")
    base64_image = encode_image(image_path)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,  # This limits the length of the answer.
        )

        analysis_result = response.choices[0].message.content
        print(f"\n--- AI analysis result ---\n{analysis_result}\n---------------------------")
        return analysis_result

    except Exception as e:
        print(f"Error calling the OpenAI API: {e}")
        return None

def get_test_snapshot_path(filename):
    # For testing
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "Snapshot", filename)
    return path

def parse_ai_response(response_text):
    try:
        clean_text = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except json.JSONDecodeError:
        print("Error: AI did not return JSON.")
        return {"status": "UNKNOWN", "reason": response_text}

if __name__ == "__main__":
    total_layers = 200  # Celkový počet vrstev (simulace)
    current_layer = 0  # Aktuální vrstva
    milestones = [25, 50, 75]  # Kdy chceme kontrolovat (v %)
    # 1. Kontrola před tiskem (Bed clear?)
    print("Zahajuji kontrolu před tiskem...")

    # DŮLEŽITÉ: Odsunout hlavu, aby nebránila výhledu
    # printer.move_toolhead_to_maintenance() # Doporučuji implementovat/odkomentovat

    test_file = "snapshot_20260211_123345_626856.jpg"
    snapshot_path = get_test_snapshot_path(test_file)

    #If camera connected
    #snapshot_path = get_camera_snapshot()

    if snapshot_path:
        print(f"Snapshot uložen: {snapshot_path}")
        prompt_before = load_prompt("prompt_before_print.txt")
        result = analyze_snapshot(snapshot_path, prompt_before)

        # Zde by měla být logika: Pokud AI řekne "FAIL" nebo "OBSTRUCTION", zastav tisk.
        # if "STOP" in result:
        #    printer.emergency_stop()
        #    exit()

    # 2. Kontrola stavu tiskárny
    state = get_printer_state()
    print(f"Stav tiskárny: {state}")

    # ... Další logika pro první vrstvu ...
    current_layer = 1
    if current_layer == 1:
        prompt_first = load_prompt("prompt_first_layer.txt")
        analyze_snapshot(snapshot_path,prompt_first)
        current_layer = 50

    # ... Další logika pro zbytek tisku ...
    while current_layer <= total_layers:
        # 1. Výpočet aktuálního procenta
        progress = int((current_layer / total_layers) * 100)

        # 2. LOGIKA KONTROLY
        # Pokud seznam milníků není prázdný A aktuální procento je větší/rovno prvnímu milníku
        if len(milestones) > 0 and progress >= milestones[0]:
            target = milestones.pop(0)  # Odstraní aktuální milník ze seznamu (už ho nechceme znovu)

            print(f"\n🔔 DOSAŽENO {target}% -> SPOUŠTÍM KONTROLU...")

            # --- ZDE VLOŽÍŠ SVOU FUNKCI ---
            prompt_mid = load_prompt("prompt_mid_print.txt")
            result = analyze_snapshot(snapshot_path, prompt_mid)
            # ------------------------------

            time.sleep(1)  # Jen simulace času kontroly
            print("✅ Kontrola OK, pokračuji v tisku.\n")

        # 3. Výpis stavu a posun dál
        print(f"\rTiskne se: {progress}% (Vrstva {current_layer})", end="")

        current_layer += 1
        time.sleep(0.02)  # Rychlost simulace

    print("100%: Printing complete!")