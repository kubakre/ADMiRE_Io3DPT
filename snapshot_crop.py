import cv2
import numpy as np

# ==========================================
# ADJUST CROP VALUES HERE (in pixels)
# ==========================================
Y_START = 0
Y_END = 930
X_START = 570
X_END = 1520
# ==========================================

def main():
    # cv2.VideoCapture(0) opens the default camera.
    # If you have multiple cameras connected (e.g., built-in laptop webcam),
    # you might need to change 0 to 1, 2, etc., to target the RealSense.
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not connect to the camera. Try changing the index in cv2.VideoCapture().")
        return

    print("Camera connected!")
    print("-> Press 's' to take a snapshot and show the crop.")
    print("-> Press 'q' to quit the script.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame.")
            break

        height, width = frame.shape[:2]

        # Protection against out-of-bounds cropping
        y1 = max(0, min(Y_START, height))
        y2 = max(0, min(Y_END, height))
        x1 = max(0, min(X_START, width))
        x2 = max(0, min(X_END, width))

        # Draw a rectangle on the live preview
        preview = frame.copy()
        cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.imshow('Live Preview (Green box = crop) | Q = Quit, S = Snapshot', preview)

        # Wait for key press (1 ms)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('s'):
            # Crop the current frame
            cropped_img = frame[y1:y2, x1:x2]
            cv2.imshow('Final Crop', cropped_img)
            print(f"Snapshot taken. Crop size: {x2 - x1}x{y2 - y1}")

        elif key == ord('q'):
            break

    # Safe termination
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()