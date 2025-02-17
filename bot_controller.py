import time
import requests
import numpy as np
import socket
import threading
from queue import Queue
from config import Config
from marker_detection import MarkerDetector

# def calculate_duration_for_rotation(angle_to_rotate):
#     return abs(int((2000/180)*angle_to_rotate))  # value is in milliseconds

def calculate_duration_for_rotation_left(angle_to_rotate):
    return abs(int((965/180)*angle_to_rotate))  # value is in milliseconds

def calculate_duration_for_rotation_right(angle_to_rotate):
    return abs(int((1110/180)*angle_to_rotate))  # value is in milliseconds

def calculate_duration_for_forward(distance):
    duration = int(5.8*distance)
    return   duration if duration < 3000 else 3000# value is in milliseconds


class BotController:
    def __init__(self, nodemcu_ip, port=8080):
        self.nodemcu_ip = nodemcu_ip
        self.port = port
        self.socket = None
        self.trap_start_time = None
        self.reconnect_attempts = 3
        self.reconnect_delay = 2  # seconds
        
        # Rate limiting and connection state
        self.connected = False
        
        # Response handling
        self.response_queue = Queue()
        self.receive_thread = None
        self.running = False
        
        # Initial connection
        self.connect()

    def receive_loop(self):
        """Background thread for receiving messages"""
        while self.running:
            if not self.connected:
                time.sleep(0.1)
                continue
                
            try:
                data = self.socket.recv(1024).decode().strip()
                if data:
                    print(f"Received response: {data}")
                    self.response_queue.put(data)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Receive error: {e}")
                self.connected = False
                break

    def connect(self):
        """Establish socket connection with reconnection logic"""
        attempt = 0
        while attempt < self.reconnect_attempts:
            try:
                if self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
                
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(1)  # 1 second timeout
                self.socket.connect((self.nodemcu_ip, self.port))
                self.connected = True
                print(f"Successfully connected to NodeMCU at {self.nodemcu_ip}:{self.port}")
                
                # Start receive thread if not already running
                if not self.running:
                    self.running = True
                    self.receive_thread = threading.Thread(target=self.receive_loop)
                    self.receive_thread.daemon = True
                    self.receive_thread.start()
                
                return True
                
            except socket.error as e:
                attempt += 1
                print(f"Connection attempt {attempt} failed: {e}")
                if attempt < self.reconnect_attempts:
                    print(f"Retrying in {self.reconnect_delay} seconds...")
                    time.sleep(self.reconnect_delay)
        
        print("Failed to establish connection after multiple attempts")
        self.connected = False
        return False

    def send_command(self, command, duration=1000):
        """Send command to NodeMCU with rate limiting"""
        if not self.connected:
            if self.receive_thread and self.receive_thread.is_alive():
                self.receive_thread.join(timeout=1)
            self.connect()

        try:
            full_command = f"{command}:{duration}\n" if duration else f"{command}\n"
            print(f"\n#### --{full_command} #####\n")
            self.socket.send(full_command.encode())
            time.sleep(duration/1000)
            time.sleep(0.4)
            return True                
        except Exception as e:
            print(f"Send error: {e}")
            self.connected = False
            return False

    def __del__(self):
        """Cleanup on destruction"""
        self.running = False
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1)
        if self.socket:
            self.socket.close()

    # def send_command(self, command, duration=0):
    #     try:
    #         response = requests.get(f"{self.nodemcu_ip}/navigate",
    #                              params={"command": command})
    #         if response.status_code == 200:
    #             print(f"Sent {command} to NodeMCU: {response.text}")
    #         else:
    #             print(f"Failed to send {command}. Status code: {response.status_code}")
    #     except Exception as e:
    #         print(f"Error sending command: {e}")

    def control_movement(self, target_ball, bot_center, goal_post_center, 
                        orientation_angle, ball_proximity_threshold):
        ball_center = (int((target_ball[0] + target_ball[2]) / 2), 
                      int((target_ball[1] + target_ball[3]) / 2))
        
        ball_vector = (ball_center[0] - bot_center[0], 
                      ball_center[1] - bot_center[1])
        goal_vector = (goal_post_center[0] - bot_center[0], 
                      goal_post_center[1] - bot_center[1])

        distance_to_ball = np.sqrt(ball_vector[0]**2 + ball_vector[1]**2)
        # Thresholds for proximity to the ball and goal post
        ball_proximity_threshold = 28  # Adjust as needed for ball proximity


        # Rotate the ball vector by the bot's orientation angle
        theta = np.radians(orientation_angle)
        rotated_x = ball_vector[0] * np.cos(theta) + ball_vector[1] * np.sin(theta)
        rotated_y = -ball_vector[0] * np.sin(theta) + ball_vector[1] * np.cos(theta)

        time_delay = 0.1 if ball_proximity_threshold > 200 else 0.05
        # Decision-making logic: move towards the ball or orient towards the goal post
        if distance_to_ball > ball_proximity_threshold or rotated_y < -10:
            print(f"\nbot Status: Far from the ball ({distance_to_ball:.2f} units) ➔ Moving towards the ball.\n")

            if rotated_x > 20:
                self.send_command("LEFT")
                time.sleep(time_delay)
                self.send_command("STOP")
                print("Action: **LEFT** ➔ Adjusting alignment (moving towards the ball)\n")            
            elif rotated_x < -20:
                self.send_command("RIGHT")
                time.sleep(time_delay)
                self.send_command("STOP")
                print("Action: **RIGHT** ➔ Adjusting alignment (moving towards the ball)\n") 

            # Forward or backward movement
            if rotated_y > 20:
                self.send_command("FORWARD")
                time.sleep(0.15 if distance_to_ball > 350 else time_delay)
                self.send_command("STOP")
                print("Action: **FORWARD** ➔ Approaching the ball\n")
            
            elif rotated_y < -20 and -20 <= rotated_x <= 20:
                print("\nStatus: Bot needs to align with goal post for backward movement.\n")
                
                # Calculate relative goal angle
                goal_theta = np.arctan2(goal_vector[1], goal_vector[0])
                relative_goal_angle = np.degrees(goal_theta) - orientation_angle
                relative_goal_angle = (relative_goal_angle + 180) % 360 - 180  # Normalize angle

                # Align with the goal post
                if relative_goal_angle > 10:
                    self.send_command("LEFT")
                    print("Aligning: **LEFT** ➔ Adjusting towards goal post\n")
                elif relative_goal_angle < -10:
                    self.send_command("RIGHT")
                    print("Aligning: **RIGHT** ➔ Adjusting towards goal post\n")
                else:
                    # Backward movement if aligned
                    self.send_command("BACKWARD")
                    time.sleep(0.1)
                    self.send_command("STOP")
                    print("Action: **BACKWARD** ➔ Moving backward towards the ball\n")

        else:
            print(f"\nStatus: Bot is near the ball ({distance_to_ball:.2f} units) ➔ Aligning towards goal post.\n")

            # Rotate to face the goal post based on the goal vector
            goal_theta = np.arctan2(goal_vector[1], goal_vector[0])
            relative_goal_angle = np.degrees(goal_theta) - orientation_angle

            if (95 < relative_goal_angle <= 270) or (-90 > relative_goal_angle > -265):
                # If angle falls within specified ranges for RIGHT movement
                self.send_command("RIGHT")
                time.sleep(0.08)
                self.send_command("STOP")

                print(f"**Action:** RIGHT ➔ Adjusting towards goal post alignment ⭕️ Angle: {relative_goal_angle}\n")

            elif (0 <= relative_goal_angle <= 85) or (270 < relative_goal_angle <= 360) or (-275 > relative_goal_angle >= -360) or (0 > relative_goal_angle >= -90):
                # If angle falls within specified ranges for LEFT movement
                self.send_command("LEFT")
                time.sleep(0.08)
                self.send_command("STOP")
                print(f"**Action:** LEFT ➔ Adjusting towards goal post alignment ⭕️ Angle: {relative_goal_angle}\n")

            else:
                print(f"**Action:** KICK ➔ Goal post within range! Taking the shot! ⚽️ {relative_goal_angle}\n")
                self.send_command("KICK")


    def control_movement2(self, target_ball, bot_center, goal_post_center, bot_orientation_angle, ball_proximity_threshold, t_forward):
        ball_center = (round((target_ball[0] + target_ball[2]) / 2),
                       round((target_ball[1] + target_ball[3]) / 2))

        ball_vector = (ball_center[0] - bot_center[0],
                       ball_center[1] - bot_center[1])

        distance_to_ball = np.sqrt(ball_vector[0] ** 2 + ball_vector[1] ** 2)

        ftrap_threshold = 50

        #The angle between the line connecting the bot center and the ball center and the x-axis.
        ball_orientation_angle= MarkerDetector.calculate_angle(bot_center,ball_center)

        #Calculate ball orientation angle with respect to bot orientation angle
        relative_ball_angle = ball_orientation_angle - bot_orientation_angle
        relative_ball_angle = (relative_ball_angle + 180) % 360 - 180  # Normalize angle

        time_delay = 0.1 if ball_proximity_threshold > 200 else 0.05

        if self.trap_start_time is None :
            if relative_ball_angle - 1.5 < -Config.BALL_ANGLE_THRESHOLD:
                duration = calculate_duration_for_rotation_left(relative_ball_angle)
                print(f"\nAligning: LEFT ➔ Adjusting bot towards the ball 👾 -->️ ⚽️ Angle: {relative_ball_angle} for {duration} milliseconds \n")
                self.send_command("LEFT",duration)
    
            elif relative_ball_angle + 2 > Config.BALL_ANGLE_THRESHOLD:

                duration = calculate_duration_for_rotation_right(relative_ball_angle)
                print(f"\nAligning: RIGHT ➔ Aligning bot towards the ball 👾 -->️ ⚽️ Angle: {relative_ball_angle} for {duration} milliseconds \n")
                self.send_command("RIGHT", duration)                  
            else:
                if distance_to_ball > ball_proximity_threshold:
                    print(f"\nbot Status: Far from the ball ({distance_to_ball:.2f} units) ➔ Moving towards the ball.\n")
                    duration = calculate_duration_for_forward(distance_to_ball)
                    self.send_command("FORWARD", duration)
                    print("Action: **FORWARD** ➔ Approaching the ball\n")
                else:
                    print(f"\nStatus: Bot is near the ball ({distance_to_ball:.2f} units) \n")
                    print("**Action:** TRAP ➔ Holding the ball in position\n")
                    duration = calculate_duration_for_forward(distance_to_ball)
                    self.send_command("FTRAP", duration + t_forward) #Trap the ball in position
                    self.trap_start_time = time.time()
                        # Move backwards after trapping the ball to avoid issues caused by the ball being near the edges.

        else:
            # The angle between the line connecting the bot center and the goal post center and the x-axis.
            goal_orientation_angle = MarkerDetector.calculate_angle(bot_center, goal_post_center)
            relative_goal_post_angle = goal_orientation_angle - bot_orientation_angle
            relative_goal_post_angle = (relative_goal_post_angle + 180) % 360 - 180  # Normalize angle
            trap_duration = time.time() - self.trap_start_time
            if trap_duration > Config.TRAP_DURATION:  # Check if the duration exceeds maximum trap duration
                print("**Action:** RELEASE ➔ Holding time exceeded, releasing the ball briefly.\n")
                self.send_command("RELEASE", 500)
                time.sleep(Config.RELEASE_DURATION)  # Release ball for 1 second
                self.send_command("TRAP", 500)
                self.trap_start_time = time.time()  # Reset trap start time

            if relative_goal_post_angle < -Config.GOAL_ANGLE_THRESHOLD:
                duration = calculate_duration_for_rotation_left(relative_goal_post_angle)
                print(
                    f"**Action:** LEFT ➔ Adjusting towards goal post alignment ⭕️ Angle: {relative_goal_post_angle} for {duration} milliseconds \n")
                self.send_command("LEFT", duration)

            elif relative_goal_post_angle > Config.GOAL_ANGLE_THRESHOLD:
                duration = calculate_duration_for_rotation_right(relative_goal_post_angle)
                print(
                    f"**Action:** RIGHT ➔ Adjusting towards goal post alignment ⭕️ Angle: {relative_goal_post_angle} for {duration} milliseconds\n")
                self.send_command("RIGHT", duration)
            else:
                self.send_command("RELEASE", 500)
                print(f"**Action:** KICK ➔ Goal post within range! Taking the shot! ⚽️ {relative_goal_post_angle}\n")
                self.send_command("FKICK", 700)
                self.trap_start_time = None

    # def defence_movement(self, bot_center, goal_post_center, bot_orientation_angle):
    #     ball_wrt_goal_vector= (goal_post_center[0] - bot_center[0],
    #                goal_post_center[1] - bot_center[1])
    #     distance_to_goal_post = np.sqrt(ball_wrt_goal_vector[0] ** 2 + ball_wrt_goal_vector[1] ** 2)
    #     if (distance_to_goal_post)
            
            









