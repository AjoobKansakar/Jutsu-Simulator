import cv2 
from cvzone.HandTrackingModule import HandDetector 
import math # distance calculation to handle overlapping of hands
import time # For combo timing
import random # chidori lighting
import pygame # sound effects
import numpy as np #image manipulation

# sound engine initialize
pygame.mixer.init()
try:
    chidori_sound = pygame.mixer.Sound("chidori.mp3") # Chidori Sound track
    rasengan_charge_sfx = pygame.mixer.Sound("rasengan_charging.mp3") # Rasengan charge sound track
    rasengan_active_sfx = pygame.mixer.Sound("rasengan_activated.mp3") # Rasengan active sound track
    rasengan_channel = pygame.mixer.Channel(1) # Separate channel for Rasengan
except:
    print("Sound files not found. Please check the name and the location of chidori.mp3 and rasengan.mp3 in the folder.")
    chidori_sound = None
    rasengan_charge_sfx = None
    rasengan_active_sfx = None

# Chidori lighting effect function
def draw_jagged_bolt(img, start, end, color, thickness, branching=False):
    """Draws a multi-segment jagged line to look like real lightning"""
    points = [start]
    num_segments = 6 # Increased segments for longer, more realistic bolts
    
    current_pos = list(start)
    for i in range(1, num_segments):
        frac = i / num_segments
        target_x = start[0] + (end[0] - start[0]) * frac
        target_y = start[1] + (end[1] - start[1]) * frac
        jitter = int(35 * (1 + frac)) 
        offset_x = random.randint(-jitter, jitter)
        offset_y = random.randint(-jitter, jitter)
        next_pt = (int(target_x + offset_x), int(target_y + offset_y))
        points.append(next_pt)
        if branching and random.random() > 0.85:
            branch_end = (next_pt[0] + random.randint(-250, 250), next_pt[1] + random.randint(-250, 250))
            draw_jagged_bolt(img, next_pt, branch_end, color, thickness // 2, False)
    points.append(end)
    for i in range(len(points) - 1):
        cv2.line(img, points[i], points[i+1], color, thickness)
        cv2.line(img, points[i], points[i+1], (255, 255, 255), max(1, thickness // 3))

# for webcam
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

# Initializing Hand Detector
detector = HandDetector(detectionCon=0.8, maxHands=2)

# Chidori Combination
current_sequence = []     
last_seal = None          
chidori_ready = False     
chidori_active = False    
chidori_start_time = 0    
chidori_hand_type = None  
last_action_time = time.time() 
combo_start_time = 0      
time_limit = 7.0          
chidori_duration = 8.0   

# Ransengan variables for temporal gesture detection
rasengan_chakra = 0       
rasengan_active = False   
rasengan_start_time = 0   # Added to track activation start
rasengan_duration = 8.0 
last_p2_pos = [0, 0]      # track if hands are moving

# Shadow clone jutsu variables
clone_active = False      
clone_start_time = 0      
clone_duration = 8.0      
clone_frame = None # Store snapshot for the clones

# Jutsu Sequence stability
counter = 0               
selection_speed = 5       
candidate_seal = None     

print("Skeletal Tracking Activated... Press 'q' to quit.")

while True:
    success, img = cap.read()
    img = cv2.flip(img, 1)

    # Findin Hand using CVzone 
    hands, img = detector.findHands(img, draw=False) # draw=false to remove bounding box around the hannds

    # Variable to track if a 2-handed jutsu is already displayed
    jutsu_active = False
    current_frame_seal = None # Tracks what seal is held in this specific frame
    
    # ensuring 1 chidori is active per frame
    chidori_drawn_this_frame = False
    # ensuring 1 rasengan is active per frame
    rasengan_drawn_this_frame = False

    # Auto-reset logic for Chidori ( 8s timeout)
    if chidori_active:
        if time.time() - chidori_start_time > chidori_duration:
            chidori_active = False
            chidori_ready = False
            chidori_hand_type = None
            current_sequence = []
            last_seal = None
            combo_start_time = 0
            if chidori_sound: chidori_sound.stop()
            
    # Auto-reset logic for Rasengan ( 8s timeout)
    elif rasengan_active:
        if time.time() - rasengan_start_time > rasengan_duration:
            rasengan_active = False
            rasengan_chakra = 0
            current_sequence = []
            last_seal = None
            combo_start_time = 0
            if rasengan_channel.get_busy(): rasengan_channel.stop()

    elif time.time() - last_action_time > time_limit:
        current_sequence = []
        chidori_ready = False
        combo_start_time = 0

    # Rasengan slow decay logic so that chatra doesn't reset instantly
    if rasengan_chakra > 0 and not rasengan_active:
        rasengan_chakra -= 0.2 
        if rasengan_chakra < 20 and rasengan_channel.get_busy():
            rasengan_channel.stop()

    if hands:
        # Hand Sign Detection - happens if Chidori or Rasengan is NOT active
        if not chidori_active and not rasengan_active:
            # checking for 2-handed seals first
            if len(hands) == 2:
                hand1 = hands[0]
                hand2 = hands[1]
                fingers1 = detector.fingersUp(hand1)
                fingers2 = detector.fingersUp(hand2)

                # distance logic between hands
                p1, p2 = hand1['center'], hand2['center']
                dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

                # Chakra Resetn logic
                if fingers1 == [1, 1, 1, 1, 1] and fingers2 == [1, 1, 1, 1, 1] and dist > 400:
                    current_sequence, chidori_ready, last_seal, combo_start_time = [], False, None, 0
                    rasengan_chakra, rasengan_active = 0, False
                    if chidori_sound: chidori_sound.stop()
                    if rasengan_channel.get_busy(): rasengan_channel.stop()
                    msg = "CHAKRA RESET"
                    font = cv2.FONT_HERSHEY_TRIPLEX
                    text_x = (1280 - cv2.getTextSize(msg, font, 2.0, 2)[0][0]) // 2
                    cv2.putText(img, msg, (text_x, 150), font, 2.0, (255, 255, 255), 2)

                # Rasengan friction logic
                if 100 < dist < 350 and not chidori_ready and not rasengan_active:
                    movement = math.sqrt((p2[0]-last_p2_pos[0])**2 + (p2[1]-last_p2_pos[1])**2)
                    last_p2_pos = p2
                    if movement > 5: 
                        rasengan_chakra += 0.8
                        if rasengan_chakra >= 20 and rasengan_charge_sfx and not rasengan_channel.get_busy():
                            rasengan_channel.play(rasengan_charge_sfx)
                    
                    if rasengan_chakra >= 100:
                        rasengan_chakra, rasengan_active = 100, True
                        rasengan_start_time = time.time() # Set time of activation
                        if rasengan_active_sfx: 
                            rasengan_channel.stop() 
                            rasengan_channel.play(rasengan_active_sfx, loops=-1)
                    
                    cv2.putText(img, f"CONCENTRATING CHAKRA: {int(rasengan_chakra)}%", (350, 60), 
                                cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 255, 0), 2)
                    
                    if rasengan_chakra >= 20:
                        mx, my = (p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2 
                        t_form = cv2.getTickCount() / cv2.getTickFrequency()
                        scale_val = rasengan_chakra / 100.0
                        for i in range(4):
                            r_form = int((50 + i * 12) * scale_val)
                            if r_form > 0:
                                start_a = int(t_form * 600 + i * 45) % 360
                                cv2.ellipse(img, (mx, my), (r_form, r_form), i*24, start_a, start_a + 60, (255, 150, 0), 2)
                        core_r = int(55 * scale_val)
                        if core_r > 0:
                            cv2.circle(img, (mx, my), int(65 * scale_val), (255, 120, 50), 2)
                            cv2.circle(img, (mx, my), core_r, (255, 255, 255), -1)
                elif dist >= 350 and not rasengan_active:
                    if rasengan_channel.get_busy(): rasengan_channel.stop()

                # Shadow clone seal logic
                p_cl_l = [1, 1, 1, 0, 0] # Left Hand Pattern: [1, 1, 1, 0, 0]
                p_cl_r_list = [[0, 1, 0, 0, 0], [0, 1, 1, 0, 0]] # Right Hand Patterns: [0, 1, 0, 0, 0] OR [0, 1, 1, 0, 0]
                
                # Check for either combination regardless of AI hand label stability
                match_clone = (fingers1 == p_cl_l and fingers2 in p_cl_r_list) or \
                              (fingers2 == p_cl_l and fingers1 in p_cl_r_list)
                
                if match_clone and dist < 120:
                    msg = "SHADOW CLONE JUTSU"
                    jutsu_active = True
                    font = cv2.FONT_HERSHEY_TRIPLEX
                    text_x = (1280 - cv2.getTextSize(msg, font, 2.6, 2)[0][0]) // 2
                    cv2.putText(img, msg, (text_x, 100), font, 2.6, (255, 255, 255), 2)

                # fixing Tiger seal stability 
                idx1, idx2 = hand1["lmList"][8], hand2["lmList"][8]
                mid1, mid2 = hand1["lmList"][12], hand2["lmList"][12]
                dist_index = math.sqrt((idx1[0]-idx2[0])**2 + (idx1[1]-idx2[1])**2)
                dist_middle = math.sqrt((mid1[0]-mid2[0])**2 + (mid1[1]-mid2[1])**2)

                # Tiger Seal Logic 
                if not jutsu_active and dist_index < 60 and dist_middle < 60 and fingers1[1] == 1 and fingers2[1] == 1:
                    msg, jutsu_active, current_frame_seal = "TIGER", True, "TIGER"
                    (w, h), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_TRIPLEX, 2.6, 2)
                    cv2.putText(img, msg, ((1280 - w) // 2, 100), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (0, 0, 255), 2)
                    for h_data in [hand1, hand2]:
                        for id in [8, 12]:
                            cx_t, cy_t = h_data["lmList"][id][0], h_data["lmList"][id][1]
                            cv2.circle(img, (cx_t, cy_t), 20, (0, 0, 255), cv2.FILLED)

                elif fingers1[1] == 1 and fingers1[2:] == [0, 0, 0] and \
                    fingers2[1] == 1 and fingers2[2:] == [0, 0, 0] and dist_index < 100:
                    msg, jutsu_active, current_frame_seal = "HORSE", True, "HORSE"
                    if not current_sequence: combo_start_time = time.time()
                    (w, h), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_TRIPLEX, 2.6, 2)
                    cv2.putText(img, msg, ((1280 - w) // 2, 100), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (255, 255, 0), 2)
                    for h_data in [hand1, hand2]:
                        cv2.circle(img, (h_data["lmList"][8][0], h_data["lmList"][8][1]), 20, (255, 255, 0), cv2.FILLED)

                elif fingers1 == [0, 0, 0, 0, 0] and fingers2 == [0, 0, 0, 0, 0] and dist_index < 60: 
                    msg, jutsu_active, current_frame_seal = "SERPENT", True, "SERPENT"
                    (w, h), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_TRIPLEX, 2.6, 2)
                    cv2.putText(img, msg, ((1280 - w) // 2, 100), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (0, 255, 0), 2)
                    for h_data in [hand1, hand2]:
                        cv2.circle(img, (h_data["lmList"][0][0], h_data["lmList"][0][1]), 30, (0, 255, 0), cv2.FILLED)

        for hand in hands:
            lmList, fingers = hand["lmList"], detector.fingersUp(hand)
            handType = "Left" if hand["type"] == "Left" or (hand["type"] == "Unknown" and hand['center'][0] < 640) else "Right"
            # Skeletal landmarks
            for id, lm in enumerate(lmList):
                if id in [4, 8, 12, 16, 20]: cv2.circle(img, (lm[0], lm[1]), 12, (255, 0, 255), cv2.FILLED)
                else: cv2.circle(img, (lm[0], lm[1]), 5, (255, 255, 0), cv2.FILLED)

            if chidori_ready and fingers == [1, 1, 1, 1, 1] and not chidori_active:
                chidori_active, chidori_start_time, chidori_hand_type = True, time.time(), handType
                if chidori_sound: chidori_sound.play(-1) 

            if chidori_active and not chidori_drawn_this_frame and handType == chidori_hand_type:
                cx, cy = lmList[9][0], lmList[9][1] 
                cv2.circle(img, (cx, cy), random.randint(70, 100), (255, 255, 0), 2)
                cv2.circle(img, (cx, cy), random.randint(50, 70), (255, 255, 255), cv2.FILLED)
                for _ in range(20):
                    end_pt = (cx + random.randint(-450, 400), cy + random.randint(-450, 400))
                    draw_jagged_bolt(img, (cx, cy), end_pt, (255, 150, 0), 5, True)
                cv2.circle(img, (cx, cy), random.randint(40, 60), (255, 255, 255), cv2.FILLED)
                chidori_drawn_this_frame = True
                rem_chidori = max(0, chidori_duration - (time.time() - chidori_start_time))
                cv2.putText(img, f"DURATION: {rem_chidori:.1f}s", (500, 50), cv2.FONT_HERSHEY_TRIPLEX, 1.2, (0, 0, 0), 2)

            if rasengan_active and not chidori_active and not rasengan_drawn_this_frame:
                cx, cy = lmList[9][0], lmList[9][1] - 100
                t = cv2.getTickCount() / cv2.getTickFrequency()
                overlay = img.copy()
                for r in range(120, 60, -12):
                    alpha = max(0.04, (130 - r) / 500)
                    cv2.circle(overlay, (cx, cy), r, (255, 100, 0), -1)
                    img = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
                for i in range(15):
                    r = random.randint(70, 95)
                    start_angle = int(t * 800 + i * 45) % 360
                    rotation_angle = i * 24 
                    cv2.ellipse(img, (cx, cy), (r, r), rotation_angle, start_angle, start_angle + 60, (255, 150, 0), 2)
                    cv2.ellipse(img, (cx, cy), (r-2, r-2), rotation_angle, start_angle + 10, start_angle + 30, (255, 255, 255), 1)
                for i in range(25):
                    angle = t * 5 + i * 0.7
                    px = int(cx + (60 + 15 * math.sin(t * 4 + i)) * math.cos(angle))
                    py = int(cy + (60 + 15 * math.sin(t * 4 + i)) * math.sin(angle))
                    cv2.circle(img, (px, py), 2, (255, 255, 255), -1)
                for i in range(5):
                    start = int((t * 150 + i * 70) % 360)
                    cv2.ellipse(img, (cx, cy), (55 + i * 2, 55 + i * 2), start, 0, 220, (255, 180, 50), 2)
                pulse = int(5 * math.sin(t * 10))
                cv2.circle(img, (cx, cy), 65 + pulse, (255, 120, 50), 2)
                cv2.circle(img, (cx, cy), 55 + pulse, (255, 255, 255), -1)
                rasengan_drawn_this_frame = True
                rem_rasengan = max(0, rasengan_duration - (time.time() - rasengan_start_time))
                cv2.putText(img, f"DURATION: {rem_rasengan:.1f}s", (500, 50), cv2.FONT_HERSHEY_TRIPLEX, 1.2, (0, 0, 0), 2)

            if fingers == [0, 0, 0, 0, 0] and not jutsu_active and not chidori_active and not rasengan_active: 
                msg, current_frame_seal = "SERPENT", "SERPENT"
                (w, h), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_TRIPLEX, 2.6, 2)
                cv2.putText(img, msg, ((1280 - w) // 2, 100), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (0, 255, 0), 2)
                cv2.circle(img, (lmList[0][0], lmList[0][1]), 30, (0, 255, 0), cv2.FILLED)

            text_pos = (50, 500) if handType == "Left" else (980, 500)
            text_y = 650 if handType == "Right" else 690 
            cv2.putText(img, f'{handType}: {fingers}', text_pos, cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)

        if current_frame_seal and not chidori_active and not rasengan_active:
            if current_frame_seal == candidate_seal: counter += 1
            else: candidate_seal, counter = current_frame_seal, 0
            if counter > selection_speed and current_frame_seal != last_seal:
                current_sequence.append(current_frame_seal)
                last_seal, last_action_time = current_frame_seal, time.time()
                if current_sequence[-3:] == ["HORSE", "TIGER", "SERPENT"]: chidori_ready, combo_start_time = True, 0 
        
        if not chidori_active and not chidori_ready and not rasengan_active:
            cv2.putText(img, f"CHAKRA: {' -> '.join(current_sequence[-3:])}", (20, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 255), 2)
            if combo_start_time != 0:
                rem_time = max(0, time_limit - (time.time() - combo_start_time))
                cv2.putText(img, f"TIMER: {rem_time:.1f}s", (1000, 50), cv2.FONT_HERSHEY_TRIPLEX, 1.2, (0, 255, 255), 2)
        if chidori_ready and not chidori_active:
            ready_msg = " Chidori "
            (rw, rh), _ = cv2.getTextSize(ready_msg, cv2.FONT_HERSHEY_TRIPLEX, 1.5, 2)
            cv2.putText(img, ready_msg, ((1280 - rw) // 2, 60), cv2.FONT_HERSHEY_TRIPLEX, 1.5, (255, 255, 0), 2)

    cv2.imshow("Naruto-Jutsu Simulator", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        pygame.mixer.quit() 
        break

cap.release()
cv2.destroyAllWindows()