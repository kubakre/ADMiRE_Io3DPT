import cv2
import numpy as np
import tensorflow as tf
import os


class SnapshotAnalysis:
    def __init__(self, image=None, model_path=None):
        #Initialization
        self.image = image
        self.model = self.load_model(model_path) if model_path else None

    def load_image(self, image_path):
        self.image = cv2.imread(image_path)

    def load_model(self, model_path):
        #If any are available
        try:
            model = tf.keras.models.load_model(model_path)
            print("Model loaded successfully.")
            return model
        except Exception as e:
            print(f"Error loading model: {e}")
            return None

    def analyze_edges(self):
        if self.image is None:
            raise ValueError("Image not loaded. Please load an image first.")

        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)

        return edges

    def analyze_contours(self):
        if self.image is None:
            raise ValueError("Image not loaded. Please load an image first.")

        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(self.image, contours, -1, (0, 255, 0), 3)

        return self.image

    def ai_inference(self):
        #If any are available
        if self.image is None:
            raise ValueError("Image not loaded. Please load an image first.")

        if self.model is None:
            raise ValueError("No AI model loaded. Please load a model first.")

        #Image preporcessing
        image_resized = cv2.resize(self.image, (224, 224)) # based on the position of the camera
        image_normalized = image_resized / 255.0

        #Prediction
        prediction = self.model.predict(np.expand_dims(image_normalized, axis=0))

        #Prediction output
        if prediction[0] > 0.5:
            print("Defect detected!")
            return 1
        else:
            print("No defect detected.")
            return 0

    def save_result(self, result_image, original_image_path, suffix):
        #Saves the analysis result to the Snapshot_an folder with an added suffix for the specific analysis.

        output_dir = "Snapshot_an"
        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.basename(original_image_path)
        name_without_extension = os.path.splitext(base_name)[0]

        new_file_name = f"{name_without_extension}{suffix}.jpg"
        save_path = os.path.join(output_dir, new_file_name)

        cv2.imwrite(save_path, result_image)
        print(f"Result saved to {save_path}")

    def display_image(self, image_to_display=None):

        if image_to_display is None:
            image_to_display = self.image

        if image_to_display is None:
            print("No image to display")
            return

        cv2.imshow("Image", image_to_display)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
