import cv2
import mediapipe as mp

class HandManager:
    def __init__(self):
        # Initialize the HandManager class
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5)
        self.mp_drawing = mp.solutions.drawing_utils
        # Initialize hand_objects to store Hand instances representing each detected hand
        self.hand_objects = [False, False]

    def process_hands(self, frame):
        # Convert the frame to RGB format
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame.flags.writeable = False
        # Process the hands in the frame using the MediaPipe Hands model
        result = self.hands.process(frame)
        if result.multi_hand_landmarks:
            # If multiple hand landmarks are detected
            for hand_landmark in result.multi_hand_landmarks:
                landmarks = hand_landmark.landmark
                # Determine the hand side (left or right)
                hand_side = 'left' if landmarks[0].x < landmarks[1].x else 'right'
                # Update or create Hand instance based on the detected hand side
                if self.hand_objects[0 if hand_side == 'left' else 1] is False:
                    self.hand_objects[0 if hand_side == 'left' else 1] = Hand(hand_side,landmarks)
                else:
                    self.hand_objects[0 if hand_side == 'left' else 1].update_fingers(landmarks)
                # Reset the other hand instance if only one hand is detected
                if len(result.multi_hand_landmarks) == 1:
                    self.hand_objects[0 if hand_side != 'left' else 1] = False
        else:
            # If no hand landmarks are detected, reset hand_objects
            self.hand_objects = [False, False]
        return result

    def draw_landmarks(self, frame):
        # Draw landmarks for each Hand instance on the frame
        for hand_landmark in self.hand_objects:
            if hand_landmark is not False:
                self.mp_drawing.draw_landmarks(image=frame, landmark_list=hand_landmark,
                                               connections=self.mp_hands.HAND_CONNECTIONS,
                                               landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(255, 0, 0),
                                                                                                 thickness=2,
                                                                                                 circle_radius=2),
                                               connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 0, 255),
                                                                                                   thickness=2,
                                                                                                   circle_radius=2))

    def count_fingers(self):
        # Count the number of fingers raised for each hand
        return sum(hand_landmark.count_fingers() for hand_landmark in self.hand_objects if hand_landmark is not False)


class Hand:
    def __init__(self, type, landmarks):
        # Initialize the Hand class
        self.type = type
        self.wrist = landmarks[0]
        self.thumb = Thumb(self.type, landmarks[1:5])
        self.index = Finger('index', landmarks[5:9])
        self.middle = Finger('middle', landmarks[9:13])
        self.ring = Finger('ring', landmarks[13:17])
        self.pinky = Finger('pinky', landmarks[17:21])
        self.fingers = [self.thumb, self.index, self.middle, self.ring, self.pinky]
        self.landmark = landmarks

    def count_fingers(self):
        # Count the number of fingers raised for the hand
        return sum(finger.fold_state() for finger in self.fingers)

    def update_fingers(self, landmarks):
        # Update finger landmarks for the hand
        start = 1
        for finger in self.fingers:
            finger.update(landmarks[start:start + 4])
            start += 4
        self.wrist = landmarks[0]
        self.landmark = landmarks

    def tip_above(self,coordinates,screen_size):
        # Check if the tip of any finger is above a specified region on the screen
        for finger in self.fingers:
            x,y,z = finger.calculate_local_position(finger.parts[3],screen_size)
            start_pos, end_pos = coordinates
            if start_pos[0] < x < end_pos[0] and start_pos[1] < y < end_pos[1]:
                return True
        return False

    def wrist_above(self,limit,screen_height):
        # Check if the wrist is above a specified limit on the screen
        if self.wrist.y * screen_height < limit:
            return True
        return False

    def hand_straight(self):
        for finger in self.fingers:
            for part in finger.parts:
                if self.wrist.y < part.y:
                    return False
        if self.middle.parts[3].x*1100 - 200 < self.wrist.x*1100 < self.middle.parts[3].x*1100 + 200:
            return True
        return False

class Finger:
    def __init__(self, type, landmarks):
        # Initialize the Finger class
        self.type = type
        self.parts = landmarks

    def calculate_local_position(self, coordinates, screen_size):
        # Calculate the local position of the finger on the screen
        x = coordinates.x
        y = coordinates.y
        z = coordinates.z
        width, height = screen_size
        x = x * width
        y = y * height
        return x, y, z

    def fold_state(self):
        # Check if the finger is folded
        # tip = self.parts[3]
        # for part in self.parts[:2]:
        #     if tip.y < part.y:
        #         return True
        # return False
        tip_y = self.parts[3].y * 1100
        base_y = self.parts[0].y * 1100
        return True if base_y - tip_y > 75 else False

    def update(self, landmarks):
        # Update finger landmarks
        self.parts = landmarks


class Thumb(Finger):
    def __init__(self, type, landmarks):
        super().__init__(type, landmarks)

    def fold_state(self):
        # Check if the thumb is folded
        tip = self.parts[3]
        mid = self.parts[2]
        return tip.x > mid.x if self.type == 'left' else tip.x < mid.x
