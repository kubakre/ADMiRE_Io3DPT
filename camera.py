import cv2
import numpy as np
import os
from datetime import datetime


class RealSenseCamera:
    # Initialize local USB camera instead of network stream
    def __init__(self, camera_index=4):
        self.camera_index = camera_index

    def start(self):
        pass

    def get_snapshot(self):
        try:
            # Connecting
            cap = cv2.VideoCapture(self.camera_index)

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            ret, frame = cap.read()

            cap.release()

            if not ret or frame is None:
                print("Cannot connect to the camera.")
                return None

            # Crop
            Y_START = 0
            Y_END = 930
            X_START = 570
            X_END = 1520

            h, w = frame.shape[:2]
            y2 = min(Y_END, h)
            x2 = min(X_END, w)

            cropped_image = frame[Y_START:y2, X_START:x2]

            return cropped_image

        except Exception as e:
            print(f"Camera get_snapshot error: {e}")
            return None

    def save_snapshot(self, base_dir="Snapshot"):
        image = self.get_snapshot()
        if image is None:
            return None

        os.makedirs(base_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(base_dir, f"snapshot_{ts}.jpg")

        cv2.imwrite(path, image)
        return path

    def stop(self):
        pass