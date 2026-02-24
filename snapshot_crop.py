import cv2
import numpy as np

# ==========================================
# ZDE SI UPRAVUJ HODNOTY PRO OŘEZ (v pixelech)
# ==========================================
Y_START = 0
Y_END = 930
X_START = 570
X_END = 1520


# ==========================================

def main():
    # cv2.VideoCapture(0) otevře výchozí kameru.
    # Pokud máš k PC připojených více kamer (např. integrovanou v notebooku),
    # možná budeš muset změnit 0 na 1, 2 atd., abys trefil tu RealSense.
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Chyba: Nepodařilo se připojit ke kameře. Zkus změnit číslo v cv2.VideoCapture().")
        return

    print("Kamera připojena!")
    print("-> Stiskni 's' pro vyfocení a zobrazení ořezu.")
    print("-> Stiskni 'q' pro ukončení skriptu.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Chyba: Nepodařilo se načíst snímek.")
            break

        height, width = frame.shape[:2]

        # Ochrana proti přetečení mimo obraz
        y1 = max(0, min(Y_START, height))
        y2 = max(0, min(Y_END, height))
        x1 = max(0, min(X_START, width))
        x2 = max(0, min(X_END, width))

        # Vykreslení obdélníku do živého náhledu
        preview = frame.copy()
        cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.imshow('Zivy nahled (Zeleny ramecek = orez) | Q = Konec, S = Vyfotit', preview)

        # Čekání na stisk klávesy (1 ms)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('s'):
            # Provedeme ořez aktuálního snímku
            cropped_img = frame[y1:y2, x1:x2]
            cv2.imshow('Vysledny orez', cropped_img)
            print(f"Snímek vyfocen. Velikost ořezu: {x2 - x1}x{y2 - y1}")

        elif key == ord('q'):
            break

    # Bezpečné ukončení
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()