import requests
import json

class PrinterControl:
    def __init__(self, url):
        #Initialize PrinterControl with the Moonraker URL.
        self.url = url

    def send_gcode(self, gcode):
        #Sends a G-code command to the printer via Moonraker API.
        try:
            endpoint = f"{self.url}/printer/gcode/script"
            response = requests.post(endpoint, json={"script": gcode})

            response.raise_for_status()  # Raise error if request fails
            return response.json()
        except Exception as e:
            print(f"Error sending G-code: {e}")
            return None

    def set_extruder_temp(self, target_temp):
        #Sets the extruder temperature.
        gcode = f"M104 S{target_temp}"  # M104 command for setting extruder temperature, maybe use M109
        return self.send_gcode(gcode)

    def set_bed_temp(self, target_temp):
        #Sets the bed temperature.
        gcode = f"M140 S{target_temp}"  # M140 command for setting bed temperature, maybe use M190
        return self.send_gcode(gcode)

    def home(self):
        # headhome
        return self.send_gcode("G28")

    def move_toolhead(self, x=None, y=None, z=None, feedrate=1500):
        #Moves the toolhead to specified coordinates.
        gcode = f"G1"
        if x is not None:
            gcode += f" X{x}"
        if y is not None:
            gcode += f" Y{y}"
        if z is not None:
            gcode += f" Z{z}"
        gcode += f" F{feedrate}"  # Set feedrate

        return self.send_gcode(gcode)

    def pause_print(self):
        #Pauses the print.
        return self.send_gcode("M25")  # M25 command pauses the print

    def resume_print(self):
        #Resumes a paused print.
        return self.send_gcode("M24")  # M24 command resumes the print

    def stop_print(self):
        #Stops the print.
        return self.send_gcode("M112")  # M112 command stops the printer completely

    def apply_recommended_adjustments(self, adjustments):
        # Based on Klipper G-code manual
        print("\nApplying recommended parameter adjustments via G-code...")

        try:
            # Wait for the movements to finish
            self.send_gcode("M400")

            # Nozzle temperature
            nozzle_temp = adjustments.get("nozzle_temperature_c", 0)
            if nozzle_temp > 0:
                self.send_gcode(f"M104 S{nozzle_temp}")

            # Bed temperature
            bed_temp = adjustments.get("bed_temperature_c", 0)
            if bed_temp > 0:
                self.send_gcode(f"M140 S{bed_temp}")

            # Flow
            flow = adjustments.get("flow_multiplier_percent", 0)
            if flow > 0:
                self.send_gcode(f"M221 S{flow}")

            # Print speed override
            speed_percent = adjustments.get("print_speed_mm_per_s", 0)
            if speed_percent > 0:
                self.send_gcode(f"M220 S{speed_percent}")

            # Acceleration
            acceleration = adjustments.get("acceleration_mm_per_s2", 0)
            if acceleration > 0:
                self.send_gcode(f"M204 S{acceleration}")

            # Fan
            fan = adjustments.get("cooling_fan_percent", 0)
            if fan > 0:
                fan_value = int((fan / 100) * 255)
                self.send_gcode(f"M106 S{fan_value}")

            # Z offset
            z_offset = adjustments.get("z_offset_mm", 0.0)
            if z_offset != 0:
                self.send_gcode("G91")
                self.send_gcode(f"G1 Z{z_offset} F300")
                self.send_gcode("G90")

            # Action
            action = adjustments.get("action", "none")

            if action == "pause_print":
                self.pause_print()

            elif action == "stop_print":
                self.send_gcode("M112")

            # Wait
            self.send_gcode("M400")

            print("Adjustments applied successfully.")

        except Exception as e:
            print(f"Error while applying adjustments: {e}")
            self.pause_print()

