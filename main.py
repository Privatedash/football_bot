# main.py
import cv2
import signal
import sys
from config import Config
from camera import CameraManager
from marker_detection import MarkerDetector
from ball_detection import BallDetector
from bot_controller import BotController
from visualization import Visualizer


class BotControlSystem:
    def __init__(self):
        self.camera = CameraManager(Config.VIDEO_URL)
        self.marker_detector = MarkerDetector()
        self.ball_detector = BallDetector(Config.YOLO_MODEL_PATH)
        self.bot_controller = BotController(Config.NODEMCU_IP)
        self.visualizer = Visualizer()
        self.goal_post_center = None
        self.target_ball = None
        self.reference_for_shortest_ball = None

    def cleanup_and_exit(self):
        """Helper function to clean up resources and exit"""
        print("\n📝 Cleaning up resources...")
        
        # Stop the bot
        print("🛑 Sending STOP command to NodeMCU...")
        self.bot_controller.send_command("STOP")
        
        # Stop the camera
        print("📷 Stopping camera capture...")
        self.camera.stop()
        
        # Close OpenCV windows
        print("🪟 Closing display windows...")
        cv2.destroyAllWindows()
        
        print("✅ Cleanup complete. System terminated safely.")
        sys.exit(0)

    def set_goal_post(self, event, x, y, flags, param):
        """Mouse callback function to set goal post position"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.goal_post_center = (x, y)
            print(f"🎯 Goal post marked at: {self.goal_post_center}")
            # Draw a marker on the frame
            frame = self.camera.get_frame()
            if frame is not None:
                cv2.circle(frame, (x, y), 10, (0, 0, 255), -1)
                cv2.putText(frame, "Goal Post", (x + 15, y), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                cv2.imshow("Bot Control System", frame)

    def signal_handler(self, sig, frame):
        """Signal handler for graceful shutdown"""
        print("\n\n🛑 Received Ctrl+C! Shutting down gracefully...")
        self.cleanup_and_exit()

    def initialize_system(self):
        """Initialize the system components and setup"""
        cv2.namedWindow("Bot Control System")
        cv2.setMouseCallback("Bot Control System", self.set_goal_post)
        signal.signal(signal.SIGINT, self.signal_handler)
        self.camera.start_capture()
        
        # Show initial frame and wait for goal post selection
        print("🖱️ Please click on the frame to mark the goal post center...")
        while self.goal_post_center is None:
            frame = self.camera.get_frame()
            if frame is not None:
                cv2.putText(frame, "Click to mark goal post center", (50, 50), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("Bot Control System", frame)
                cv2.waitKey(1)
        
        self.reference_for_shortest_ball = input(
            "🔍 Choose the reference point for finding the nearest ball: Type 'G' if near the 🥅 goal post, type any other value if near the 🤖 bot and then press Enter: ").lower()

    def process_frame(self, frame):
        """Process each frame for ball and marker detection"""
        yolo_results = self.ball_detector.detect(frame)
        corners, ids, _ = self.marker_detector.detect_markers(frame)
        bot_center = None
        bot_orientation_angle = None

        if ids is not None:
            self.visualizer.highlight_aruco(frame, ids, corners, Config.BOT_MARKER_ID)

            if Config.BOT_MARKER_ID in ids:
                bot_index = list(ids.flatten()).index(Config.BOT_MARKER_ID)
                bot_corners = corners[bot_index]
                bot_center, bot_orientation_angle = self.marker_detector.process_bot_marker(bot_corners)

            if self.reference_for_shortest_ball == 'b' and bot_center is not None:
                self.target_ball = self.ball_detector.find_closest_ball_from_bot(bot_center, yolo_results)
            else:
                self.target_ball = self.ball_detector.find_closest_ball_from_goal_post(self.goal_post_center, yolo_results)

            if self.target_ball:
                self.adjust_ball_threshold_and_control_bot(bot_center, bot_orientation_angle)

        self.visualizer.draw_ball_boxes(frame, yolo_results, self.target_ball)
        self.draw_reference_circles(frame)
        cv2.imshow("Bot Control System", frame)

    def adjust_ball_threshold_and_control_bot(self, bot_center, bot_orientation_angle):
        """Adjust ball threshold and control bot movement"""
        fixed_point = (640, 360)
        fixed_distance = 250
        x1, y1, x2, y2 = self.target_ball
        targ_ball_center = ((x1 + x2) // 2, (y1 + y2) // 2)
        target_centre_distance = ((targ_ball_center[0] - fixed_point[0])**2 + 
                                (targ_ball_center[1] - fixed_point[1])**2)**0.5
        
        ball_threshold = Config.BALL_PROXIMITY_THRESHOLD
        t_forward = 60
        if target_centre_distance > fixed_distance:
            ball_threshold -= 10
            t_forward += 60
        
        if self.goal_post_center and bot_center and self.target_ball:
            self.bot_controller.control_movement2(self.target_ball, bot_center,
                                            self.goal_post_center, bot_orientation_angle,
                                            ball_threshold, t_forward)

    def draw_reference_circles(self, frame):
        """Draw reference circles on the frame"""
        center_coordinates = (640, 360)
        cv2.circle(frame, center_coordinates, 200, (128, 255, 128), 4)
        cv2.circle(frame, center_coordinates, 300, (255, 128, 128), 4)

    def run(self):
        """Main loop to run the bot control system"""
        try:
            while True:
                frame = self.camera.get_frame()
                self.process_frame(frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except KeyboardInterrupt:
            print("\n\n🛑 Received Ctrl+C! Shutting down gracefully...")
        finally:
            self.cleanup_and_exit()


if __name__ == "__main__":
    print("\n⚙️  Powering up all systems...\n")
    print("🔥 Ignition sequence started... Engine is now running smoothly.\n")
    print("✅ Engine Status: ONLINE")
    print("Ready for operation. Let's go!\n")
    bot_control_system = BotControlSystem()
    bot_control_system.initialize_system()
    bot_control_system.run()
