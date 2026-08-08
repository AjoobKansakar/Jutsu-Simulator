import cv2 
from cvzone.HandTrackingModule import HandDetector 
import math # distance calculation to handle overlapping of hands
import time # For combo timing
import random # chidori lighting
import pygame # sound effects
import numpy as np #image manipulation
import os # checking if the segmentation model file exists
import mediapipe as mp # person segmentation for solid clone cutouts

# sound engine initialize
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.mixer.init()
try:
    chidori_sound = pygame.mixer.Sound("chidori.mp3") # Chidori Sound track
    rasengan_charge_sfx = pygame.mixer.Sound("rasengan_charging.mp3") # Rasengan charge sound track
    rasengan_active_sfx = pygame.mixer.Sound("rasengan_activated.mp3") # Rasengan active sound track
    shadow_clone_sfx = pygame.mixer.Sound("shadowClone.mp3") # Shadow clone sound track
    rasengan_channel = pygame.mixer.Channel(1) # Separate channel for Rasengan
    clone_channel = pygame.mixer.Channel(2)    # FIXED: Separate channel for Shadow Clone clarity
except:
    print("Sound files not found. Please check the name and the location of chidori.mp3 and rasengan.mp3 in the folder.")
    chidori_sound = None
    rasengan_charge_sfx = None
    rasengan_active_sfx = None
    shadow_clone_sfx = None
    rasengan_channel = None
    clone_channel = None

# Shadow clone person segmentation setup
segmenter = None
SEGMENTER_MODEL_PATH = "selfie_segmenter.tflite"
if os.path.exists(SEGMENTER_MODEL_PATH):
    try:
        BaseOptions = mp.tasks.BaseOptions
        ImageSegmenter = mp.tasks.vision.ImageSegmenter
        ImageSegmenterOptions = mp.tasks.vision.ImageSegmenterOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        segmenter_options = ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=SEGMENTER_MODEL_PATH),
            running_mode=VisionRunningMode.IMAGE,
            output_confidence_masks=True)
        segmenter = ImageSegmenter.create_from_options(segmenter_options)
        print("Shadow Clone: person segmentation model loaded - solid clone cutouts enabled.")
    except Exception as e:
        segmenter = None
        print(f"Shadow Clone: failed to load {SEGMENTER_MODEL_PATH} ({e}). Using blend fallback.")
else:
    print(f"Shadow Clone: {SEGMENTER_MODEL_PATH} not found in this folder - using blend fallback.")
    print("For solid (non-transparent) clones, download it from:")
    print("https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite")


def get_person_mask(frame_bgr):
    """Shadow Clone helper: returns a soft-edged 0-255 single-channel mask that
    isolates you from the background using MediaPipe's Image Segmenter."""
    if segmenter is None:
        return None
    try:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = segmenter.segment(mp_image)
        person_conf = result.confidence_masks[0].numpy_view()  # 0..1 foreground confidence
        mask = (person_conf * 255).astype(np.uint8)
        # Shadow clone Mask using raw confidence to make the clones look real
        _, mask = cv2.threshold(mask, 130, 255, cv2.THRESH_BINARY)
        mask = cv2.GaussianBlur(mask, (9, 9), 0)
        return mask
    except Exception:
        return None


def draw_smoke_cloud(img, center, progress, ground_y=700):
    """Shadow Clone helper: draws a Smoke that RISES from the ground
    (ground_y) up into a bumpy cartoon cloud cap at 'center', then dissipates
    -- instead of a static cloud that just fades in place.
    progress: 0 = just triggered (plume starts at the ground),
              0.5 = plume has fully risen, cap fully bloomed,
              1.0 = fully dissipated."""
    cx, cap_y = center

    grow = min(1.0, progress / 0.5)   # 1st half smoke effect: rises from ground to its full height
    fade = max(0.0, (progress - 0.5) / 0.5) # 2nd half smoke effect: fades away effect
    alpha = max(0.0, 1.0 - fade)
    if alpha <= 0.02:
        return

    current_top = ground_y - (ground_y - cap_y) * grow  # current height of the rising column
    base_r = int(55 + 45 * grow)  # cloud cap swells as it finishes rising

    overlay = img.copy()

    # Rising smoke effect 
    steps = 10
    for i in range(steps):
        f = i / steps
        y = int(ground_y - (ground_y - current_top) * f)
        half_w = max(3, int(base_r * (0.22 + 0.55 * f)))
        shade = 248 - int(12 * (1 - f))
        cv2.ellipse(overlay, (cx, y), (half_w, max(6, int(half_w * 0.55))), 0, 0, 360, (shade, shade, shade), cv2.FILLED)
    # cluster layout, to make smoke effect look solid rather then a scatter dots
    blob_layout = [
        (0, 0, 1.00), (-1.0, -0.30, 0.72), (1.0, -0.30, 0.72),
        (-1.7, 0.15, 0.55), (1.7, 0.15, 0.55),
        (0.0, -0.85, 0.68), (-0.55, 0.55, 0.60), (0.55, 0.55, 0.60),
    ]

    # Soft blue-grey shadow pass (slightly offset), giving the cloud edges depth
    for ox, oy, s in blob_layout:
        r = max(4, int(base_r * s))
        cv2.circle(overlay, (int(cx + ox * base_r) + 6, int(current_top + oy * base_r) + 8), r, (215, 190, 170), cv2.FILLED)
    # Light blue outline pass, matching the reference cloud art
    for ox, oy, s in blob_layout:
        r = max(4, int(base_r * s)) + 4
        cv2.circle(overlay, (int(cx + ox * base_r), int(current_top + oy * base_r)), r, (235, 195, 140), cv2.FILLED)
    # White cloud body on top
    for ox, oy, s in blob_layout:
        r = max(4, int(base_r * s))
        cv2.circle(overlay, (int(cx + ox * base_r), int(current_top + oy * base_r)), r, (250, 250, 250), cv2.FILLED)

    img[:] = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)


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
clone_hold_start = 0      # track seal held duration
clone_hold_threshold = 2.0 # Shadow clone seal duration threshold
clone_poof_duration = 1.4 # Smoke effect Duration
clone_offset = 340        # Horizontal distance (px) each clone stands from you

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
            if rasengan_channel and rasengan_channel.get_busy(): rasengan_channel.stop()

    # Auto-reset logic for Shadow Clone ( 8s timeout)
    elif clone_active:
        if time.time() - clone_start_time > clone_duration:
            clone_active = False
            clone_frame = None
            clone_hold_start = 0 # Reset hold timer for next use

    elif time.time() - last_action_time > time_limit:
        current_sequence = []
        chidori_ready = False
        combo_start_time = 0

    # Rasengan slow decay logic so that chatra doesn't reset instantly
    if rasengan_chakra > 0 and not rasengan_active:
        rasengan_chakra -= 0.2 
        if rasengan_chakra < 20 and rasengan_channel and rasengan_channel.get_busy():
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
                    rasengan_chakra, rasengan_active, clone_active = 0, False, False
                    if chidori_sound: chidori_sound.stop()
                    if rasengan_channel and rasengan_channel.get_busy(): rasengan_channel.stop()
                    if clone_channel and clone_channel.get_busy(): clone_channel.stop()
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
                        if rasengan_chakra >= 20 and rasengan_charge_sfx and rasengan_channel and not rasengan_channel.get_busy():
                            rasengan_channel.play(rasengan_charge_sfx)
                    
                    if rasengan_chakra >= 100:
                        rasengan_chakra, rasengan_active = 100, True
                        rasengan_start_time = time.time() # Set time of activation
                        if rasengan_active_sfx and rasengan_channel: 
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
                    if rasengan_channel and rasengan_channel.get_busy(): rasengan_channel.stop()

                # Shadow clone seal detection
                p_cl_l = [1, 1, 1, 0, 0] 
                p_cl_r_list = [[0, 1, 0, 0, 0], [0, 1, 1, 0, 0]]
                match_clone = (fingers1 == p_cl_l and fingers2 in p_cl_r_list) or \
                              (fingers2 == p_cl_l and fingers1 in p_cl_r_list)
                
                # Seal Block Logic: If matching clone seal and no chidori sequence started..
                if match_clone and dist < 120 and not current_sequence:
                    jutsu_active = True # blocks other seal detection
                    if clone_hold_start == 0:
                        clone_hold_start = time.time()
                    
                    elapsed_hold = time.time() - clone_hold_start
                    
                    if elapsed_hold < clone_hold_threshold:
                        # Seal Block logic: Displaying clone seal timer blocks other seals
                        msg = f"CHANNELING CLONE CHAKRA: {elapsed_hold:.1f}s"
                        text_x = (1280 - cv2.getTextSize(msg, cv2.FONT_HERSHEY_TRIPLEX, 1.2, 2)[0][0]) // 2
                        cv2.putText(img, msg, (text_x, 100), cv2.FONT_HERSHEY_TRIPLEX, 1.2, (255, 255, 255), 2)
                    else:
                        # Activate Jutsu and trigger the dedicated Shadow Clone SFX on its own channel
                        clone_active = True
                        clone_start_time = time.time()
                        if shadow_clone_sfx and clone_channel: clone_channel.play(shadow_clone_sfx)
                else:
                    clone_hold_start = 0

                # fixing Tiger seal stability 
                idx1, idx2 = hand1["lmList"][8], hand2["lmList"][8]
                mid1, mid2 = hand1["lmList"][12], hand2["lmList"][12]
                dist_index = math.sqrt((idx1[0]-idx2[0])**2 + (idx1[1]-idx2[1])**2)
                dist_middle = math.sqrt((mid1[0]-mid2[0])**2 + (mid1[1]-mid2[1])**2)

                # Tiger Seal Logic (Only triggers if not channeling clone chakra)
                if not jutsu_active and dist_index < 60 and dist_middle < 60 and fingers1[1] == 1 and fingers2[1] == 1:
                    msg, jutsu_active, current_frame_seal = "TIGER", True, "TIGER"
                    (w, h), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_TRIPLEX, 2.6, 2)
                    cv2.putText(img, msg, ((1280 - w) // 2, 100), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (0, 0, 255), 2)
                    for h_data in [hand1, hand2]:
                        for id in [8, 12]:
                            cx_t, cy_t = h_data["lmList"][id][0], h_data["lmList"][id][1]
                            cv2.circle(img, (cx_t, cy_t), 20, (0, 0, 255), cv2.FILLED)

                elif not jutsu_active and fingers1[1] == 1 and fingers1[2:] == [0, 0, 0] and \
                    fingers2[1] == 1 and fingers2[2:] == [0, 0, 0] and dist_index < 100:
                    msg, jutsu_active, current_frame_seal = "HORSE", True, "HORSE"
                    if not current_sequence: combo_start_time = time.time()
                    (w, h), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_TRIPLEX, 2.6, 2)
                    cv2.putText(img, msg, ((1280 - w) // 2, 100), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (255, 255, 0), 2)
                    for h_data in [hand1, hand2]:
                        cv2.circle(img, (h_data["lmList"][8][0], h_data["lmList"][8][1]), 20, (255, 255, 0), cv2.FILLED)

                elif not jutsu_active and fingers1 == [0, 0, 0, 0, 0] and fingers2 == [0, 0, 0, 0, 0] and dist_index < 60: 
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

            text_pos, text_y = (50, 500) if handType == "Left" else (980, 500), 650 if handType == "Right" else 690 
            cv2.putText(img, f'{handType}: {fingers}', text_pos, cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)

    # Live Shadow Clone logic
    if clone_active:
        elapsed_clone = time.time() - clone_start_time
        clone_src = img.copy()
        person_mask = get_person_mask(clone_src)
        # smoke --> clone transaction logic
        poof_mid = clone_poof_duration * 0.5
        reveal = max(0.0, (elapsed_clone - poof_mid) / poof_mid) if poof_mid > 0 else 1.0
        reveal = min(1.0, reveal)


        # clone formation left/right and scaled down + raised 
        clone_transforms = [
            {"dx": -260, "dy": -20, "scale": 0.92},
            {"dx":  260, "dy": -20, "scale": 0.92},
            {"dx": -470, "dy": -45, "scale": 0.80},
            {"dx":  470, "dy": -45, "scale": 0.80},
            {"dx": -660, "dy": -65, "scale": 0.68},
            {"dx":  660, "dy": -65, "scale": 0.68},
        ]

        for t in clone_transforms:
            # Clone positions
            M = cv2.getRotationMatrix2D((640, 720), 0, t["scale"])
            M[0, 2] += t["dx"]
            M[1, 2] += t["dy"]
            live_clone = cv2.warpAffine(clone_src, M, (1280, 720))

            if person_mask is not None:
                shifted_mask = cv2.warpAffine(person_mask, M, (1280, 720)).astype(np.float32) / 255.0
                shifted_mask *= reveal
                mask3 = cv2.merge([shifted_mask, shifted_mask, shifted_mask])
                img = (img.astype(np.float32) * (1 - mask3) + live_clone.astype(np.float32) * mask3).astype(np.uint8)
            else:
                img = cv2.addWeighted(img, 1.0, live_clone, 0.55 * reveal, 0)

            # Smoke effect on the clones --> rises from that clone's own ground spot
            if elapsed_clone < clone_poof_duration:
                puff_pt = M @ np.array([640, 380, 1.0])
                ground_pt = M @ np.array([640, 700, 1.0])
                draw_smoke_cloud(img, (int(puff_pt[0]), int(puff_pt[1])), elapsed_clone / clone_poof_duration, ground_y=int(ground_pt[1]))

        # Rendering all the clones behind the original body
        if person_mask is not None:
            real_mask3 = cv2.merge([person_mask, person_mask, person_mask]).astype(np.float32) / 255.0
            img = (img.astype(np.float32) * (1 - real_mask3) + clone_src.astype(np.float32) * real_mask3).astype(np.uint8)
        else:
            cv2.putText(img, "SOLID CLONE MODE OFF - selfie_segmenter.tflite missing/not loaded",
                        (20, 700), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

        rem_clone = max(0, clone_duration - elapsed_clone)
        cv2.putText(img, f"DURATION: {rem_clone:.1f}s", (500, 50), cv2.FONT_HERSHEY_TRIPLEX, 1.2, (0, 0, 0), 2)
        msg_active = "SHADOW CLONE JUTSU ACTIVE"
        text_x_active = (1280 - cv2.getTextSize(msg_active, cv2.FONT_HERSHEY_TRIPLEX, 1.5, 2)[0][0]) // 2
        cv2.putText(img, msg_active, (text_x_active, 100), cv2.FONT_HERSHEY_TRIPLEX, 1.5, (255, 255, 255), 2)

    if current_frame_seal and not chidori_active and not rasengan_active:
        if current_frame_seal == candidate_seal: counter += 1
        else: candidate_seal, counter = current_frame_seal, 0
        if counter > selection_speed and current_frame_seal != last_seal:
            current_sequence.append(current_frame_seal)
            last_seal, last_action_time = current_frame_seal, time.time()
            if current_sequence[-3:] == ["HORSE", "TIGER", "SERPENT"]: chidori_ready, combo_start_time = True, 0 
    
    if not chidori_active and not chidori_ready and not rasengan_active and not clone_active:
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