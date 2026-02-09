import requests
import time

# Configuration
IP_ADDRESS = "localhost"
PORT = "7125"
URL = f"http://{IP_ADDRESS}:{PORT}"


def send_gcode(gcode):
    """Sends a G-code command to the printer via Moonraker API."""
    try:
        endpoint = f"{URL}/printer/gcode/script"
        response = requests.post(endpoint, json={"script": gcode})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error sending G-code: {e}")


def run_test_loop():
    print(f"Connecting to printer at {URL}...")
    print("Starting test loop. Press Ctrl+C to stop.")

    # --- INIT ---
    send_gcode("G90")      # absolute positioning
    send_gcode("M83")      # relative extrusion (safe default)
    send_gcode("G28")      # home axes

    temp_target = 200

    try:
        while True:
            print(f"Move X10 | Target Temp: {temp_target}°C")
            send_gcode(f"M104 S{temp_target}")
            send_gcode("G1 X10 F3000")

            time.sleep(2)

            print("Move X100")
            send_gcode("G1 X100 F3000")

            temp_target = 210 if temp_target == 200 else 200
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nStopping test loop")
        send_gcode("M104 S0")
        send_gcode("M140 S0")



if __name__ == "__main__":
    run_test_loop()