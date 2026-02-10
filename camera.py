import pyrealsense2 as rs
import numpy as np
import cv2
import os
from datetime import datetime

class RealSenseCamera:
    def __init__(self, serial=None):
        self.pipeline = rs.pipeline()
        self.config = rs.config()

        if serial:
            self.config.enable_device(serial)

        self.config.enable_stream(
            rs.stream.color, 640, 480, rs.format.bgr8, 30
        )

        self.pipeline_started = False

    def start(self):
        if not self.pipeline_started:
            self.pipeline.start(self.config)
            for _ in range(10):
                self.pipeline.wait_for_frames()
            self.pipeline_started = True

    def get_snapshot(self):
        #Returns a numpy array (image) or None
        try:
            if not self.pipeline_started:
                self.start()

            frames = self.pipeline.wait_for_frames(timeout_ms=2000)
            color_frame = frames.get_color_frame()
            if not color_frame:
                return None

            return np.asanyarray(color_frame.get_data())

        except Exception as e:
            print("Camera get_snapshot error:", e)
            return None

    def save_snapshot(self, base_dir="Snapshot"):
        #Saves snapshot to disk.
        image = self.get_snapshot()
        if image is None:
            return None

        os.makedirs(base_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(base_dir, f"snapshot_{ts}.jpg")

        cv2.imwrite(path, image)
        return path

    def stop(self):
        if self.pipeline_started:
            self.pipeline.stop()
            self.pipeline_started = False
