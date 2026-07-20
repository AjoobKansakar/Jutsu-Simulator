import cv2 
from cvzone.HandTrackingModule import HandDetector 

# 1. Webcam setup
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

# 2. Initialize the Hand Detector
detector = HandDetector(detectionCon=0.8, maxHands=2)

print("Skeletal Tracking Activated... Press 'q' to quit.")

while True:
    success, img = cap.read()

    # Findin Hand using CVzone 
    hands, img = detector.findHands(img, draw=True) # draw=true to draw defualt green box and dots

    if hands:
        for hand in hands:
            # 21 landmark points using MediaPipe
            lmList = hand["lmList"] 
            
            # Custom Skeleton Overlay 
            # Landmark ids: 0: Wrist, 4: Thumbs up, 8: Index, 12: Middle, 16: Ring, 20: Pinky
            for id, lm in enumerate(lmList):
                # lm[0], lm[1] are X and Y coordinates
                cx, cy = lm[0], lm[1]
                
                # purple glow on the fingertips according to the finger Ids
                if id in [4, 8, 12, 16, 20]:
                    cv2.circle(img, (cx, cy), 12, (255, 0, 255), cv2.FILLED)
                else:
                    # small blue dots for joints
                    cv2.circle(img, (cx, cy), 5, (255, 255, 0), cv2.FILLED)

            # Logical Check for fingers
            fingers = detector.fingersUp(hand)
            
            # finger index count on the screen UI
            cv2.putText(img, f'Fingers: {fingers}', (hand['bbox'][0], hand['bbox'][1] - 50),
                        cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

    cv2.imshow("Naruto Jutsu Simulator", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()