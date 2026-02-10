import cv2
import numpy as np
import tensorflow as tf
import os


class SnapshotAnalysis:
    def __init__(self, image=None, model_path=None):
        """
        Inicializuje objekt pro analýzu snapshotu a AI detekci.
        :param image: Obraz (numpy array). Pokud není zadán, metoda `load_image()` musí být zavolána.
        :param model_path: Cesta k předtrénovanému modelu AI pro analýzu (volitelné).
        """
        self.image = image
        self.model = self.load_model(model_path) if model_path else None

    def load_image(self, image_path):
        """
        Načte obrázek ze souboru.
        :param image_path: Cesta k souboru obrázku
        """
        self.image = cv2.imread(image_path)

    def load_model(self, model_path):
        """
        Načte předtrénovaný model pro AI analýzu.
        :param model_path: Cesta k souboru modelu
        :return: Načtený model
        """
        try:
            model = tf.keras.models.load_model(model_path)
            print("Model loaded successfully.")
            return model
        except Exception as e:
            print(f"Error loading model: {e}")
            return None

    def analyze_edges(self):
        """
        Analýza hran pomocí Canny detektoru.
        :return: Vrací snímek s detekovanými hranami.
        """
        if self.image is None:
            raise ValueError("Image not loaded. Please load an image first.")

        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)

        return edges

    def analyze_contours(self):
        """
        Analýza kontur na obrázku.
        :return: Snímek s nakreslenými konturami.
        """
        if self.image is None:
            raise ValueError("Image not loaded. Please load an image first.")

        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(self.image, contours, -1, (0, 255, 0), 3)

        return self.image

    def ai_inference(self):
        """
        Aplikuje AI model na obrázek pro detekci vad.
        :return: Predikce AI modelu (např. 0 = bez vady, 1 = vada).
        """
        if self.image is None:
            raise ValueError("Image not loaded. Please load an image first.")

        if self.model is None:
            raise ValueError("No AI model loaded. Please load a model first.")

        # Předzpracování obrázku pro model
        image_resized = cv2.resize(self.image, (224, 224))  # Změna velikosti pro model
        image_normalized = image_resized / 255.0  # Normalizace (pokud model trénován na normalizovaných datech)

        # Predikce
        prediction = self.model.predict(np.expand_dims(image_normalized, axis=0))

        # Pokud model vrátí 1 (vada), pokud 0 (bez vady)
        if prediction[0] > 0.5:
            print("Defect detected!")
            return 1  # Vada
        else:
            print("No defect detected.")
            return 0  # Bez vady

    def save_result(self, result_image, save_path="output.jpg"):
        """
        Uloží výsledek analýzy na disk.
        :param result_image: Obraz, který bude uložen
        :param save_path: Cesta k souboru pro uložení
        """
        cv2.imwrite(save_path, result_image)
        print(f"Result saved to {save_path}")

    def display_image(self, image_to_display=None):
        """
        Zobrazí obrázek pomocí OpenCV.
        :param image_to_display: Obraz k zobrazení, pokud není, použije se originální obrázek
        """
        if image_to_display is None:
            image_to_display = self.image

        if image_to_display is None:
            print("No image to display")
            return

        # Zobrazí obrázek v okně
        cv2.imshow("Image", image_to_display)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
