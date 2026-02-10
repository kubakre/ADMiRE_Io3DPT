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
        gcode = f"M104 S{target_temp}"  # M104 command for setting extruder temperature
        return self.send_gcode(gcode)

    def set_bed_temp(self, target_temp):
        #Sets the bed temperature.
        gcode = f"M140 S{target_temp}"  # M140 command for setting bed temperature
        return self.send_gcode(gcode)

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

