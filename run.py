import requests
import json
import time
import os
import base64

from camera import RealSenseCamera
from command_printer import PrinterControl
from image_analysis import SnapshotAnalysis #can be deleted
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
# It would probably be better to put it in command_printer.
def get_printer_state():
    try:
        r = requests.get(f"{URL}/printer/info", timeout=3)
        r.raise_for_status()
        return r.json()["result"]["state"]
    except requests.RequestException as e:
        print(f"Printer not connected: {e}")
        return "error"

# It would probably be better to put it in command_printer.
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

def wait_for_print_start(poll_interval=2):
    print("Waiting for print job to start...")

    while True:
        try:
            status = read_printer_status()
            state = status.get("state")

            if state == "printing":
                print("Print detected. Starting monitoring system.")
                return True

            print(f"Printer state: {state} | Waiting...")
            time.sleep(poll_interval)

        except Exception as e:
            print(f"Error checking printer state: {e}")
            time.sleep(poll_interval)

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

        printer.apply_recommended_adjustments(adjustments) # Need to add command_printer commands

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

def mid_layer_check(snapshot):
    global mid_layer_corrections_count

    print("Mid-layer check")

    prompt_mid = load_prompt("prompt_mid_print.txt")
    response_text = analyze_snapshot(snapshot, prompt_mid)

    if not response_text:
        print("No AI response. Pausing print.")
        printer.pause_print()
        return False

    ai_data = parse_ai_response(response_text)

    print("\n--- Parsed AI JSON ---")
    print(json.dumps(ai_data, indent=2))
    print("-----------------------\n")

    # Validation
    required_keys = [
        "print_status",
        "current_layer_assessment",
        "detected_issues",
        "severity_score",
        "confidence_score",
        "recommended_adjustments"
    ]

    for key in required_keys:
        if key not in ai_data:
            print(f"Missing key: {key}")
            printer.pause_print()
            return False

    status = ai_data["print_status"]
    issues = ai_data["detected_issues"]
    severity = ai_data["severity_score"]
    confidence = ai_data["confidence_score"]
    adjustments = ai_data["recommended_adjustments"]
    action = adjustments.get("action", "pause_print")

    # This is safety logic, when AI is not really sure (change confidence as you want)
    if confidence < 0.6:
        print("Low confidence. Pausing for manual inspection.")
        printer.pause_print()
        return False

    # This will stop if there is no way to fix the error.
    if "spaghetti_failure" in issues or "layer_shift" in issues:
        print("Catastrophic failure detected.")
        printer.stop_print()
        return False

    if status == "critical":
        if action == "stop_print":
            printer.stop_print()
        else:
            printer.pause_print()
        return False

    # If it's okay, don't interfere
    if status == "ok" and action == "none":
        print("Print stable. Continuing.")
        return True

    # Limit corrections, can be set in the main loop
    if mid_layer_corrections_count >= MAX_AUTOMATIC_CORRECTIONS:
        print("Maximum automatic corrections reached.")
        printer.pause_print()
        return False

    # Slow down the print
    if action == "slow_down":
        printer.send_gcode("M220 S80")  # 80% speed override
        mid_layer_corrections_count += 1
        return True

    # Adjustments
    if action == "adjust_parameters" and status in ["warning", "ok"]:
        print("Applying limited mid-layer adjustments.")

        safe_adjustments = {}

        # Permitted mid-layer modifications
        for key in [
            "flow_multiplier_percent",
            "pressure_advance",
            "retraction_length_mm",
            "retraction_speed_mm_per_s",
            "cooling_fan_percent",
            "print_speed_mm_per_s",
            "acceleration_mm_per_s2",
            "square_corner_velocity_mm_per_s"
        ]:
            value = adjustments.get(key, "no_change")
            if value != "no_change":
                safe_adjustments[key] = value

        # Safety temperature limit
        nozzle_temp = adjustments.get("nozzle_temperature_c", "no_change")
        if nozzle_temp != "no_change":
            current_status = read_printer_status()
            current_nozzle = current_status.get("extruder_temp", 0)

            if abs(nozzle_temp - current_nozzle) <= 15:
                safe_adjustments["nozzle_temperature_c"] = nozzle_temp
            else:
                print("Temperature change too large — ignored.")

        printer.apply_recommended_adjustments(safe_adjustments)

        mid_layer_corrections_count += 1
        return True

    # Pause
    if action == "pause_print":
        printer.pause_print()
        return False

    # ---- Fallback ----
    print("Unexpected AI output. Pausing.")
    printer.pause_print()
    return False

if __name__ == "__main__":
    MAX_AUTOMATIC_CORRECTIONS = 2
    mid_layer_corrections_count = 0
    # change this for read_printer_status() - progress

    milestones = [25, 50, 75]  # Multi-layer intervals

    print("=== 3D PRINT MONITOR STARTED ===")

    # Wait for print to start
    wait_for_print_start()

    first_layer_done = False

    # Multi - layer intervals
    while True:
        status = read_printer_status()
        state = status.get("state")

        # If print ends -> exit monitoring
        if state in ["complete", "error", "standby"]:
            print(f"\nPrint finished with state: {state}")
            break

        # If paused -> wait
        if state == "paused":
            print("\nPrint paused...")
            time.sleep(2)
            continue

        # read_printer_status()
        progress = int(status.get("progress", 0) * 100)

        # First layer check
        if not first_layer_done and progress >= 1:
            print("\n🔎 First layer check starting...")
            printer.pause_print()
            printer.home()
            snapshot_path = get_camera_snapshot()
            first_layer_check(snapshot_path)
            first_layer_done = True
            print("First layer check completed.\n")

        # Based on milestones it begins control
        if len(milestones) > 0 and progress >= milestones[0]:
            target = milestones.pop(0)

            print(f"\n🔔 Milestone {target}% -> Starting check!")

            # Logic
            printer.pause_print()
            printer.home()
            snapshot_path = get_camera_snapshot()
            mid_layer_check(snapshot_path)

            print("✅ Check ok, printing continues\n")

        print(f"\rPrinting: {progress}%", end="")

        time.sleep(2)  # polling interval

    print("100%: Printing complete!")