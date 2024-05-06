import cv2
import time
import random
import ctypes
import numpy as np
from hand_manager import HandManager


class Core:
    def __init__(self, title, size):
        # Window attributes
        self.title = title
        self.size = size
        self.cam = cv2.VideoCapture(0)

        # Hands attributes
        self.hand_manager = HandManager()
        self.hand_visibility = False
        self.hand_process_cooldown = None

        # Buttons attriubutes
        self.delete_btn_state = False
        self.submit_btn_state = False

        # Game attributes
        self.question = ''
        self.answer = '0'
        self.result = 0
        self.last_question_result = False
        self.quesiton_cooldown_timer = None
        self.input = None
        self.input_timer = None
        self.score = 0

    def toggle_landmark(self):
        """
         Toggle hand landmark visibility.
         """
        self.hand_visibility = not self.hand_visibility

    def render(self):
        """
          Render the game interface.
          """
        # process frame
        ret, frame = self.cam.read()
        frame = cv2.flip(frame, 1)
        if not ret:
            frame = np.full((self.size[1],self.size[0],3),(0,0,0),dtype=np.uint8)
            text_size = cv2.getTextSize('Could not load video',1,4.0,2)[0]
            cv2.putText(frame,'Could not load video',((self.size[0]-text_size[0])//2,(self.size[1]+text_size[1])//2),1,4.0,(0,0,255),2)
        else:
            frame = cv2.resize(frame, self.size)
        text_color = (0, 0, 0)

        # process hands
        self.hand_manager.process_hands(frame)
        if self.hand_visibility:
            self.hand_manager.draw_landmarks(frame)

        # delete button
        self.draw_button(frame, (40, 20), (220, 80), 'Reset', (0, 0, 255), -1 if self.delete_btn_state else 1)

        # submit button
        self.draw_button(frame, (self.size[0] - 220, 20), (self.size[0] - 40, 80), 'Submit', (0, 255, 0),
                         -1 if self.submit_btn_state else 1)

        # question
        if self.question == '':
            self.question, self.result = self.get_question()

        # answer
        self.input = self.hand_manager.count_fingers()
        if self.hand_manager.hand_objects.count(False) != 2:
            if self.hand_process_cooldown is None:
                self.hand_process_cooldown = time.time()
            else:
                if time.time() - self.hand_process_cooldown > 0.2:
                    if self.input_timer is None:
                        self.input_timer = time.time()
                    else:
                        if time.time() - self.input_timer > 1.5:
                            for hand in self.hand_manager.hand_objects:
                                if hand:
                                    if not hand.wrist_above(450, 700) and hand.wrist_above(700, 700) and hand.hand_straight():
                                        if self.answer == '0':
                                            self.answer = ''
                                        if len(self.answer) < 4:
                                            self.answer += str(self.input)
                                            break
                            self.input_timer = None
                            self.input = None
            for hand in self.hand_manager.hand_objects:
                if hand is not False:
                    if hand.tip_above(((40, 20), (220, 80)), (1100, 700)):
                        self.delete_btn_state = True
                        if self.answer != '0':
                            self.answer = '0'
                    elif hand.tip_above(((self.size[0] - 220, 20), (self.size[0] - 40, 80)), (1100, 700)):
                        self.submit_btn_state = True
                        if self.quesiton_cooldown_timer is None:
                            self.last_question_result = self.check_answer()
                    else:
                        self.delete_btn_state = False
                        self.submit_btn_state = False
        else:
            self.hand_process_cooldown = None

        # correct/wrong answer color change
        if self.quesiton_cooldown_timer is not None:
            if time.time() - self.quesiton_cooldown_timer > 2.0:
                text_color = (0, 0, 0)
                self.question, self.result = self.get_question()
                self.quesiton_cooldown_timer = None
                self.answer = '0'
            else:
                if self.last_question_result:
                    text_color = (0, 255, 0)
                else:
                    text_color = (0, 0, 255)

        # draw questiom,answer,score,frame
        cv2.putText(frame, f'{self.question} = {self.answer}',
                    (450 - (10 * (len(self.question) + len(self.answer))), 75), 1, 3.5, text_color, 2)
        cv2.putText(frame, f'Score: {str(self.score)}', (self.size[0] - 250, self.size[1] - 30), 1, 3.0, text_color, 2)
        cv2.imshow(self.title, frame)

    def run(self):
        """
        Run the game loop.
        """
        while True:
            self.render()
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.toggle_landmark()
            elif key == 27:
                break
            if cv2.getWindowProperty('PyVideoMath', cv2.WND_PROP_VISIBLE) < 1:
                break

    def draw_button(self, frame, start_pos, end_pos, text, color, state):
        """
        Draw a button on the frame.
        """
        cv2.rectangle(frame, start_pos, end_pos, color, state)
        width = end_pos[0] - start_pos[0]
        height = end_pos[1] - start_pos[1]
        text_size = cv2.getTextSize(text, 1, 2.0, 2)
        if state == -1:
            color = (0, 0, 0)
        cv2.putText(frame, text,
                    (start_pos[0] + int((width - text_size[0][0]) // 2), start_pos[1] + int(height - text_size[0][1])),
                    1, 2.0, color, 2)

    def get_question(self):
        """
        Generate a new question.
        """
        while True:
            rand_num_1 = random.randint(1, 100)
            rand_num_2 = random.randint(1, 100)
            num_1, num_2 = max(rand_num_1, rand_num_2), min(rand_num_1, rand_num_2)
            action = random.choice(['+', '-', 'x', '/'])
            if action == '+':
                result = num_1 + num_2
            elif action == '-':
                result = num_1 - num_2
            elif action == 'x':
                result = num_1 * num_2
            elif action == '/':
                if num_2 == 0:
                    continue
                result = num_1 / num_2
            if 0 < result < 100 and result.is_integer():
                return f'{num_1} {action} {num_2}', int(result)

    def check_answer(self):
        """
        Check if the submitted answer is correct.
        """
        self.quesiton_cooldown_timer = time.time()
        if int(self.answer) == self.result:
            self.score += 1
            return True
        return False

    def reset_answer(self):
        """
        Reset the answer and start the cooldown timer.
        """
        self.answer = '0'
        self.hand_process_cooldown = time.time()


if __name__ == '__main__':
    window_manager = Core('PyVideoMath', (1100, 700))
    window_manager.run()
