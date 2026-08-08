# Naruto Jutsu Simulator 

A real-time Computer Vision application that allows users to perform iconic Naruto Jutsus using hand gestures and seals. This project utilizes MediaPipe for landmark tracking, OpenCV for procedural VFX, and Pygame for an immersive audio experience.

## Features

### 1. Chidori
*   **Activation:** Perform the seal sequence: `Horse` --> `Tiger` --> `Serpent`.
*   **Mechanic:** Once the sequence is complete, open your palm to release the chakra.
*   **VFX:** Real-time procedural jagged lightning bolts that arc across the screen with randomized branching.
*   **SFX:** High-intensity electric chirping sound triggered upon activation.

### 2. Rasengan 
*   **Activation:** Hold your hands together and perform a "rubbing" or "concentrating" motion.
*   **Mechanic:** Chakra levels increase from 0% to 100% based on hand movement velocity. 
*   **VFX:** A high-speed rotating chakra shell consisting of 15+ overlapping energy streams and a pulsing white core.
*   **SFX:** Wind-tunnel charging audio that transitions into a high-density energy hum at 100%.

### 3. Shadow Clone Jutsu 
*   **Activation:** Cross your fingers to form the Clone Seal and hold for **2 seconds**.
*   **Mechanic:** Utilizes AI Selfie Segmentation to "cut out" the user and duplicate them in real-time.
*   **VFX:** Animated smoke clouds that rise from the ground to reveal live-moving clones positioned behind the original user.
*   **SFX:** Iconic "Poof" sound effect synced with the smoke appearance.


## Tech Stack
*   **Language:** Python 3.13
*   **Libraries:** 
    *   `OpenCV`: Image processing and VFX rendering.
    *   `MediaPipe`: Hand landmark detection and selfie segmentation.
    *   `Pygame`: Background audio and channel management.
    *   `NumPy`: Matrix calculations for clone positioning.
    *   `cvzone`: Landmark wrapper logic.

## Installation & Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install opencv-python mediapipe pygame cvzone numpy

# Developed by AjoobKansakar
