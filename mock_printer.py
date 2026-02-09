import time
import math
import random

class MockPrinter:
    def __init__(self):
        self.start_time = time.time()
        self.layer = 0
        self.max_layers = 120
        self.filename = "test_print.gcode"

    def get_state(self):
        elapsed = time.time() - self.start_time

        # ---- PRINT STATE ----
        if elapsed < 2:
            state = "standby"
        elif elapsed < 5:
            state = "printing"
        elif elapsed < 60:
            state = "printing"
        else:
            state = "complete"

        # ---- PROGRESS ----
        progress = min(elapsed / 60, 1.0)

        # ---- LAYER SIMULATION ----
        self.layer = min(int(progress * self.max_layers), self.max_layers)

        # ---- TEMPERATURES ----
        extruder_temp = 200 + 10 * math.sin(elapsed / 5)
        bed_temp = 60 + 5 * math.sin(elapsed / 10)

        # ---- POSITION ----
        x = 100 * abs(math.sin(elapsed / 3))
        y = 100 * abs(math.cos(elapsed / 3))
        z = round(self.layer * 0.2, 2)

        return {
            "result": {
                "status": {
                    "print_stats": {
                        "state": state,
                        "filename": self.filename,
                        "print_duration": round(elapsed, 1),
                        "total_duration": 60
                    },
                    "virtual_sdcard": {
                        "progress": round(progress, 3),
                        "is_active": state == "printing"
                    },
                    "extruder": {
                        "temperature": round(extruder_temp, 1),
                        "target": 205
                    },
                    "heater_bed": {
                        "temperature": round(bed_temp, 1),
                        "target": 60
                    },
                    "toolhead": {
                        "position": [
                            round(x, 2),
                            round(y, 2),
                            z
                        ]
                    }
                }
            }
        }
