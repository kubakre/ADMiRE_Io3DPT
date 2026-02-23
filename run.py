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
Baseline_printer_status = None

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

    printer_status = read_printer_status()

    # This is for local analysis
    # try:
    #     analyzer = SnapshotAnalysis(image=None)
    #     analyzer.load_image(image_path)
    #     edges = analyzer.analyze_edges()
    #     analyzer.save_result(edges, image_path, suffix="_ed")
    # except Exception as e:
    #     print(f"Error during CV analysis: {e}")

    # LLM analysis
    base64_image = encode_image(image_path)

    structured_context = {
        "printer_status": printer_status
    }

    combined_prompt = f"""
        {prompt_text}

        PRINTER TELEMETRY (JSON):
        {json.dumps(structured_context, indent=2)}

        Use both the image and the telemetry data to make your decision.
        Return ONLY valid JSON.
        """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": combined_prompt},
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

def zero_layer_check(snapshot):
    global Baseline_printer_status
    print("Starting pre-print check")
    current_status = read_printer_status()
    if Baseline_printer_status is None:
        Baseline_printer_status = current_status
        print("Baseline printer status stored.")
    else:
        print("Baseline already exists. Not overwriting.")

    print("Baseline status:")
    print(json.dumps(Baseline_printer_status, indent=2))
    state = get_printer_state()
    print(f"Printer state: {state}")

    prompt_before = load_prompt("prompt_before_print.txt")
    response_text = analyze_snapshot(snapshot, prompt_before)

    if not response_text:
        print("AI returned no response. Pausing print...")
        printer.pause_print()
        return False

    ai_data = parse_ai_response(response_text)

    required_keys = [
        "bed_status",
        "detected_issues",
        "coverage_percent",
        "severity_score",
        "recommended_action",
        "confidence_score"
    ]

    for key in required_keys:
        if key not in ai_data:
            print(f"Missing key in AI response: {key}")
            printer.pause_print()
            return False

    print("\n--- Parsed AI JSON ---")
    print(json.dumps(ai_data, indent=2))
    print("-----------------------\n")

    recommended_action = ai_data["recommended_action"]
    confidence = ai_data["confidence_score"]

    # This is safety logic, when AI is not really sure (change confidence as you want)
    if confidence < 0.6:
        print("Low confidence from AI. Pausing print for manual inspection.")
        printer.pause_print()
        return False
    if recommended_action == "none":
        print("Bed status OK. Continuing print.")
        printer.resume_print()
        return True
    else:
        print(f"Issue detected: {recommended_action}")
        print("Pausing print until issue is resolved.")
        printer.pause_print()
        return False


def first_layer_check(snapshot):
    print("Starting first layer check")
    prompt_first = load_prompt("prompt_first_layer.txt")
    response_text = analyze_snapshot(snapshot, prompt_first)

    if not response_text:
        print("AI returned no response. Pausing print.")
        printer.pause_print()
        return False

    ai_data = parse_ai_response(response_text)

    print("\n--- Parsed AI JSON ---")
    print(json.dumps(ai_data, indent=2))
    print("-----------------------\n")

    required_keys = ["print_status", "confidence_score", "recommended_adjustments"]
    for key in required_keys:
        if key not in ai_data:
            print(f"Missing key: {key}")
            printer.pause_print()
            return False

    status = ai_data["print_status"]
    confidence = ai_data["confidence_score"]
    adjustments = ai_data["recommended_adjustments"]
    action = adjustments.get("action", "pause_print")

    # This is safety logic, when AI is not really sure (change confidence as you want)
    if confidence < 0.6:
        print("Low confidence. Pausing for manual inspection.")
        printer.pause_print()
        return False

    if status == "ok" and action == "none":
        print("First layer OK. Continuing print.")
        printer.resume_print()
        return True

    if status in ["warning", "ok"] and action == "pause_print":
        print("Adjustments required. Pausing print.")
        printer.pause_print()

        apply_recommended_adjustments(adjustments) # Need to add command_printer commands

        print("Resuming print after adjustments.")
        printer.resume_print()
        return True

    if status == "critical" or action == "stop_print":
        print("Critical issue detected.")
        printer.stop_print()
        print("Print stopped. Waiting for operator.")
        return False

    print("Unexpected AI output. Pausing for safety.")
    printer.pause_print()
    return False

if __name__ == "__main__":
    total_layers = 200  # Total number of layers (simulation)
    current_layer = 0  # Current layer
    # change this for read_printer_status() - progress

    milestones = [25, 50, 75]  # Multi-layer intervals

    test_file = "snapshot_20260211_123345_626856.jpg" #

    # First layer check
    current_layer = 1
    if current_layer == 1:
        printer.pause_print()
        #printer.move_toolhead() #head home
        snapshot_path = get_test_snapshot_path(test_file)
        #snapshot_path = get_camera_snapshot()
        first_layer_check(snapshot_path)
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