import cv2 
from cvzone.HandTrackingModule import HandDetector 
import math # distance calculation to handle overlapping of hands
import time # For combo timing
import random # chidori lighting

# Chidori lighting effect function
def draw_jagged_bolt(img, start, end, color, thickness, branching=False):
    """Draws a multi-segment jagged line to look like real lightning"""
    points = [start]
    num_segments = 6 # lighting bolts effect
    
    current_pos = list(start)
    for i in range(1, num_segments):
        # Calculate progress towards end
        target_x = start[0] + (end[0] - start[0]) * i / num_segments
        target_y = start[1] + (end[1] - start[1]) * i / num_segments
        
        # Large random offsets to make it "spread" across the frame
        offset_x = random.randint(-40, 40)
        offset_y = random.randint(-40, 40)
        
        next_pt = (int(target_x + offset_x), int(target_y + offset_y))
        points.append(next_pt)
        
        # Occasional branching bolts to cover more screen area
        if branching and random.random() > 0.8:
            branch_end = (next_pt[0] + random.randint(-150, 150), next_pt[1] + random.randint(-150, 150))
            draw_jagged_bolt(img, next_pt, branch_end, color, thickness // 2, False)

    points.append(end)
    
    for i in range(len(points) - 1):
        cv2.line(img, points[i], points[i+1], color, thickness)

# for webcam
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

# Initializing Hand Detector
detector = HandDetector(detectionCon=0.8, maxHands=2)

# Chidori Combination
current_sequence = []     # Stores the order of seals performed
last_seal = None          # Prevents adding the same seal 30 times per second
chidori_ready = False     # Becomes True when HORSE -> TIGER -> SERPENT is done
chidori_active = False    # Becomes True when Chidori is actually active (after open palm)
chidori_start_time = 0    # Tracks the 20s duration
last_action_time = time.time() # Resets combo if user is too slow
combo_start_time = 0      # Tracks when the first seal (HORSE) started
time_limit = 7.0          # Seconds allowed to finish the sequence
chidori_duration = 20.0   # How long Chidori stays active

# Jutsu Sequence stability
counter = 0               # Frames a seal has been held
selection_speed = 5       # Number of frames to confirm a seal (Debounce)
candidate_seal = None     # The seal currently being performed before confirmation

print("Skeletal Tracking Activated... Press 'q' to quit.")

while True:
    success, img = cap.read()
    # camera Flip to mirror
    img = cv2.flip(img, 1)

    # Findin Hand using CVzone 
    hands, img = detector.findHands(img, draw=False) # draw=false to remove bounding box around the hannds

    # Variable to track if a 2-handed jutsu is already displayed
    jutsu_active = False
    current_frame_seal = None # Tracks what seal is held in this specific frame
    
    # ensuring 1 chidori is active per frame
    chidori_drawn_this_frame = False

    # Auto-reset logic ( 20s timeout)
    if chidori_active:
        if time.time() - chidori_start_time > chidori_duration:
            chidori_active = False
            chidori_ready = False
            current_sequence = []
            last_seal = None
            combo_start_time = 0
    elif time.time() - last_action_time > time_limit:
        current_sequence = []
        chidori_ready = False
        combo_start_time = 0

    if hands:
        # Hand Sign Detection - happens if Chidori is NOT active
        if not chidori_active:
            # checking for 2-handed seals first
            if len(hands) == 2:
                hand1 = hands[0]
                hand2 = hands[1]
                fingers1 = detector.fingersUp(hand1)
                fingers2 = detector.fingersUp(hand2)

                # Chakra Reset logic
                if fingers1 == [1, 1, 1, 1, 1] and fingers2 == [1, 1, 1, 1, 1]:
                    current_sequence = []
                    chidori_ready = False
                    last_seal = None
                    combo_start_time = 0
                    msg = "CHAKRA RESET"
                    font = cv2.FONT_HERSHEY_TRIPLEX
                    scale = 2.0
                    thick = 2
                    (w, h), _ = cv2.getTextSize(msg, font, scale, thick)
                    text_x = (1280 - w) // 2
                    cv2.putText(img, msg, (text_x, 150), font, scale, (255, 255, 255), thick)

                # fixing Tiger seal stability 
                idx1 = hand1["lmList"][8]
                idx2 = hand2["lmList"][8]
                mid1 = hand1["lmList"][12]
                mid2 = hand2["lmList"][12]

                dist_index = math.sqrt((idx1[0] - idx2[0])**2 + (idx1[1] - idx2[1])**2)
                dist_middle = math.sqrt((mid1[0] - mid2[0])**2 + (mid1[1] - mid2[1])**2)

                # Tiger Seal Logic
                if dist_index < 60 and dist_middle < 60 and fingers1[1] == 1 and fingers2[1] == 1:
                    msg = "TIGER"
                    jutsu_active = True
                    current_frame_seal = "TIGER"
                    font = cv2.FONT_HERSHEY_TRIPLEX
                    scale = 2.6
                    thick = 2
                    (w, h), _ = cv2.getTextSize(msg, font, scale, thick)
                    text_x = (1280 - w) // 2
                    cv2.putText(img, msg, (text_x, 100), font, scale, (0, 0, 255), thick)
                    for h_data in [hand1, hand2]:
                        for id in [8, 12]:
                            cx, cy = h_data["lmList"][id][0], h_data["lmList"][id][1]
                            cv2.circle(img, (cx, cy), 20, (0, 0, 255), cv2.FILLED)

                # Horse Seal Logic
                elif fingers1[1] == 1 and fingers1[2:] == [0, 0, 0] and \
                    fingers2[1] == 1 and fingers2[2:] == [0, 0, 0] and dist_index < 100:
                    msg = "HORSE"
                    jutsu_active = True
                    current_frame_seal = "HORSE"
                    if not current_sequence:
                        combo_start_time = time.time()
                    font = cv2.FONT_HERSHEY_TRIPLEX
                    scale = 2.6
                    thick = 2
                    (w, h), _ = cv2.getTextSize(msg, font, scale, thick)
                    text_x = (1280 - w) // 2
                    cv2.putText(img, msg, (text_x, 100), font, scale, (255, 255, 0), thick)
                    for h_data in [hand1, hand2]:
                        cx, cy = h_data["lmList"][8][0], h_data["lmList"][8][1]
                        cv2.circle(img, (cx, cy), 20, (255, 255, 0), cv2.FILLED)

                # Serpent Seal Logic 
                elif fingers1 == [0, 0, 0, 0, 0] and fingers2 == [0, 0, 0, 0, 0] and dist_index < 60: 
                    msg = "SERPENT"
                    jutsu_active = True
                    current_frame_seal = "SERPENT" 
                    font = cv2.FONT_HERSHEY_TRIPLEX
                    scale = 2.6
                    thick = 2
                    (w, h), _ = cv2.getTextSize(msg, font, scale, thick)
                    text_x = (1280 - w) // 2
                    cv2.putText(img, msg, (text_x, 100), font, scale, (0, 255, 0), thick)
                    for h_data in [hand1, hand2]:
                        cx, cy = h_data["lmList"][0][0], h_data["lmList"][0][1]
                        cv2.circle(img, (cx, cy), 30, (0, 255, 0), cv2.FILLED)

        for hand in hands:
            lmList = hand["lmList"] 
            for id, lm in enumerate(lmList):
                cx, cy = lm[0], lm[1]
                if id in [4, 8, 12, 16, 20]:
                    cv2.circle(img, (cx, cy), 12, (255, 0, 255), cv2.FILLED)
                else:
                    cv2.circle(img, (cx, cy), 5, (255, 255, 0), cv2.FILLED)

            fingers = detector.fingersUp(hand)
            handType = hand["type"]

            # Side check for stable UI labeling
            if handType == "Left" or (handType == "Unknown" and hand['center'][0] < 640):
                current_hand_side = "Left"
            else:
                current_hand_side = "Right"

            # Chidori activation trigger
            if chidori_ready and fingers == [1, 1, 1, 1, 1] and not chidori_active:
                chidori_active = True
                chidori_start_time = time.time()
                chidori_hand_type = current_hand_side

            # 1 chidori per frame logic
            if chidori_active and not chidori_drawn_this_frame and current_hand_side == chidori_hand_type:
                cx, cy = lmList[9][0], lmList[9][1] # Palm center
                
                # Multi-layered Core for Bright Flare
                cv2.circle(img, (cx, cy), random.randint(70, 100), (255, 255, 0), 2) # Outer Cyan ring
                cv2.circle(img, (cx, cy), random.randint(50, 70), (255, 255, 255), cv2.FILLED) # Pure white core
                
                # frame-spreading bolts (20 bolts)
                for _ in range(20):
                    dist_x = random.randint(-450, 400)
                    dist_y = random.randint(-450, 400)
                    end_pt = (cx + dist_x, cy + dist_y)
                    
                    # core layer 1: Thick Glowing Cyan/Blue
                    draw_jagged_bolt(img, (cx, cy), end_pt, (255, 150, 0), 5, branching=True)
                    # core layer 2: Thin Sharp White Core
                    draw_jagged_bolt(img, (cx, cy), end_pt, (255, 255, 255), 1, branching=False)

                #  Palm Overlap to cover the palm 
                cv2.circle(img, (cx, cy), random.randint(40, 60), (255, 255, 255), cv2.FILLED)
                
                # Mark as drawn so other hands in this frame don't get the effect
                chidori_drawn_this_frame = True
                
                # Title and Duration UI
                c_msg = "CHIDORI"
                (cw, ch), _ = cv2.getTextSize(c_msg, cv2.FONT_HERSHEY_TRIPLEX, 3.0, 4)
                cv2.putText(img, c_msg, ((1280 - cw) // 2, 200), cv2.FONT_HERSHEY_TRIPLEX, 3.0, (255, 255, 0), 4)
                rem_chidori = max(0, chidori_duration - (time.time() - chidori_start_time))
                cv2.putText(img, f"DURATION: {rem_chidori:.1f}s", (500, 50), 
                            cv2.FONT_HERSHEY_TRIPLEX, 1.2, (255, 200, 0), 2)

            # Serpent fallback
            if fingers == [0, 0, 0, 0, 0] and not jutsu_active and not chidori_active: 
                msg = "SERPENT"
                current_frame_seal = "SERPENT" 
                font = cv2.FONT_HERSHEY_TRIPLEX
                scale = 2.6
                thick = 2
                (w, h), _ = cv2.getTextSize(msg, font, scale, thick)
                text_x = (1280 - w) // 2
                cv2.putText(img, msg, (text_x, 100), font, scale, (0, 255, 0), thick) 
                cx, cy = lmList[0][0], lmList[0][1]
                cv2.circle(img, (cx, cy), 30, (0, 255, 0), cv2.FILLED)

            # UI labels
            if current_hand_side == "Left":
                hand_label, text_pos = "Left", (50, 500)
            else:
                hand_label, text_pos = "Right", (980, 500)
            text_y = 650 if current_hand_side == "Right" else 690 
            cv2.putText(img, f'{hand_label}: {fingers}', text_pos,
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)

        # Combo Sequence Stability
        if current_frame_seal and not chidori_active:
            if current_frame_seal == candidate_seal:
                counter += 1
            else:
                candidate_seal, counter = current_frame_seal, 0

            if counter > selection_speed and current_frame_seal != last_seal:
                current_sequence.append(current_frame_seal)
                last_seal, last_action_time = current_frame_seal, time.time()
                if current_sequence[-3:] == ["HORSE", "TIGER", "SERPENT"]:
                    chidori_ready, combo_start_time = True, 0 
        
        # Chidori UI
        if not chidori_active:
            cv2.putText(img, f"CHAKRA: {' -> '.join(current_sequence[-3:])}", (20, 50), 
                        cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 255), 2)
            if combo_start_time != 0 and not chidori_ready:
                rem_time = max(0, time_limit - (time.time() - combo_start_time))
                cv2.putText(img, f"TIMER: {rem_time:.1f}s", (1000, 50), 
                            cv2.FONT_HERSHEY_TRIPLEX, 1.2, (0, 255, 255), 2)
            if chidori_ready:
                ready_msg = "⚡ CHAKRA CHARGED: OPEN PALM ⚡"
                (rw, rh), _ = cv2.getTextSize(ready_msg, cv2.FONT_HERSHEY_TRIPLEX, 1.5, 2)
                cv2.putText(img, ready_msg, ((1280 - rw) // 2, 60), cv2.FONT_HERSHEY_TRIPLEX, 1.5, (255, 255, 0), 2)

    cv2.imshow("Naruto Jutsu Simulator", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()