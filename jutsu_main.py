import cv2 
from cvzone.HandTrackingModule import HandDetector 
import math # distance calculation to handle overlapping of hands

# for webcam
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

# Initializing Hand Detector
detector = HandDetector(detectionCon=0.8, maxHands=2)

print("Skeletal Tracking Activated... Press 'q' to quit.")

while True:
    success, img = cap.read()
    # camera Flip to mirror
    img = cv2.flip(img, 1)

    # Findin Hand using CVzone 
    hands, img = detector.findHands(img, draw=False) # draw=false to remove bounding box around the hannds

    if hands:
        # Hand Sign Detection
        
        # checking for 2-handed seals first
        if len(hands) == 2:
            hand1 = hands[0]
            hand2 = hands[1]
            fingers1 = detector.fingersUp(hand1)
            fingers2 = detector.fingersUp(hand2)

            # fixing Tiger seal stability 
            # fingertip coordinates for both hands
            # ID 8 = Index Tip, ID 12 = Middle Tip
            idx1 = hand1["lmList"][8]
            idx2 = hand2["lmList"][8]
            mid1 = hand1["lmList"][12]
            mid2 = hand2["lmList"][12]

            # Calculate distance between matching fingertips
            dist_index = math.sqrt((idx1[0] - idx2[0])**2 + (idx1[1] - idx2[1])**2)
            dist_middle = math.sqrt((mid1[0] - mid2[0])**2 + (mid1[1] - mid2[1])**2)

            # Tiger Seal: If index tips are close AND middle tips are close AND they are pointing up
            if dist_index < 60 and dist_middle < 60 and fingers1[1] == 1 and fingers2[1] == 1:
                msg = "TIGER"
                # To center the Text UI
                font = cv2.FONT_HERSHEY_TRIPLEX
                scale = 2.6
                thick = 2
                # Get the width and height of the text box
                (w, h), _ = cv2.getTextSize(msg, font, scale, thick)
                # Calculate X to be exactly in the middle: (Screen Width / 2) - (Text Width / 2)
                text_x = (1280 - w) // 2
                cv2.putText(img, msg, (text_x, 100), font, scale, (0, 0, 255), thick) # Red for Tiger
                
                # changing the fingertip glow to Red
                for h_data in [hand1, hand2]:
                    for id in [8, 12]: # Index and Middle tips
                        cx, cy = h_data["lmList"][id][0], h_data["lmList"][id][1]
                        cv2.circle(img, (cx, cy), 20, (0, 0, 255), cv2.FILLED)

            # Horse Seal: Only Index UP, others DOWN 
            # checking index 1 (Index Finger) and indices 2,3,4 (Middle, Ring, Pinky)
            elif fingers1[1] == 1 and fingers1[2:] == [0, 0, 0] and \
                 fingers2[1] == 1 and fingers2[2:] == [0, 0, 0] and dist_index < 100:
                msg = "HORSE"
                font = cv2.FONT_HERSHEY_TRIPLEX
                scale = 2.6
                thick = 2
                (w, h), _ = cv2.getTextSize(msg, font, scale, thick)
                text_x = (1280 - w) // 2
                cv2.putText(img, msg, (text_x, 100), font, scale, (0, 255, 255), thick) # Yellow for horse
                
                # changing the fingertip glow to Yellow
                for h_data in [hand1, hand2]:
                    cx, cy = h_data["lmList"][8][0], h_data["lmList"][8][1] # Index tip
                    cv2.circle(img, (cx, cy), 20, (0, 255, 255), cv2.FILLED)

            # Serpent Seal: All fingers folded/interlaced, hands touching
            elif fingers1 == [0, 0, 0, 0, 0] and fingers2 == [0, 0, 0, 0, 0] and dist_index < 50: # to insure the hands are close enough
                msg = "SERPENT"
                font = cv2.FONT_HERSHEY_TRIPLEX
                scale = 2.6
                thick = 2
                (w, h), _ = cv2.getTextSize(msg, font, scale, thick)
                text_x = (1280 - w) // 2
                cv2.putText(img, msg, (text_x, 100), font, scale, (0, 255, 0), thick) # Green for Serpent
                
                # Green Hand glow
                for h_data in [hand1, hand2]:
                    cx, cy = h_data["lmList"][0][0], h_data["lmList"][0][1]
                    cv2.circle(img, (cx, cy), 30, (0, 255, 0), cv2.FILLED)

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

            # Serpent seal logic
            # If hands overlap and are detected as a single fist, activate Serpent
            if fingers == [0, 0, 0, 0, 0]: # Indexing for Serpent
                msg = "SERPENT"
                font = cv2.FONT_HERSHEY_TRIPLEX
                scale = 2.6
                thick = 2
                (w, h), _ = cv2.getTextSize(msg, font, scale, thick)
                text_x = (1280 - w) // 2
                cv2.putText(img, msg, (text_x, 100), font, scale, (0, 255, 0), thick) # Green UI
                # Visual glow on the center of the combined hands
                cx, cy = lmList[0][0], lmList[0][1]
                cv2.circle(img, (cx, cy), 30, (0, 255, 0), cv2.FILLED)

            handType = hand["type"]

            if handType == "Left" or (handType == "Unknown" and hand['center'][0] < 640):
                hand_label = "Left"
                text_pos = (50, 500) # Bottom Left
            else:
                hand_label = "Right"
                text_pos = (980, 500) # Bottom Right

            text_y = 650 if handType == "Right" else 690 
            cv2.putText(img, f'{hand_label}: {fingers}', text_pos,
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)

    cv2.imshow("Naruto Jutsu Simulator", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()