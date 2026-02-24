import numpy as np
import cv2
import os
import requests
from datetime import datetime

class RealSenseCamera:
    # Kept the original class name so the main script doesn't need to be changed.
    # It now uses Klipper's camera API (Crowsnest) instead of a physical RealSense connection.
    def __init__(self, snapshot_url="http://localhost:8080/?action=snapshot"):
        self.snapshot_url = snapshot_url

    def start(self):
        # This method is no longer needed, Klipper's camera API is always running.
        pass

    def get_snapshot(self):
        # Returns a numpy array (image) or None
        try:
            # Download the current snapshot from Klipper's web UI (Crowsnest)
            response = requests.get(self.snapshot_url, timeout=5)
            response.raise_for_status()

            # Convert the downloaded byte data into a numpy array and decode into an OpenCV image
            image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if image is None:
                return None

            # Crop the snapshot (based on the camera position, you need to measure it. You can use snapshot_crop).
            # Make sure your Klipper camera is set to output 1920x1080, otherwise adjust these values.
            Y_START = 0
            Y_END = 930
            X_START = 570
            X_END = 1520

            cropped_image = image[Y_START:Y_END, X_START:X_END]

            return cropped_image

        except Exception as e:
            print("Camera get_snapshot error:", e)
            return None

    def save_snapshot(self, base_dir="Snapshot"):
        # Saves snapshot to disk.
        image = self.get_snapshot()
        if image is None:
            return None

        os.makedirs(base_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(base_dir, f"snapshot_{ts}.jpg")

        cv2.imwrite(path, image)
        return path

    def stop(self):
        # Nothing to stop.
        pass