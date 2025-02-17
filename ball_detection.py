from ultralytics import YOLO
import numpy as np

class BallDetector:
    def __init__(self, model_path):
        self.model = YOLO(model_path)

    def detect(self, frame):
        return self.model(frame)

    @staticmethod
    def _is_point_in_rectangle(point, rect_corners):
        """Helper method to check if a point lies within a rectangle"""
        x, y = point
        x1, y1, x2, y2 = rect_corners
        return x1 <= x <= x2 and y1 <= y <= y2

    @staticmethod
    def _get_restricted_zone(court_bounds, buffer_percentage=0.2):
        """Helper method to calculate restricted zone bounds"""
        x1, y1, x2, y2 = court_bounds
        height = y2 - y1
        buffer = height * buffer_percentage
        # Modify y values (move inward from top and bottom), keep x values same as court
        return (x1, y1 + buffer, x2, y2 - buffer)

    @staticmethod
    def find_closest_ball(reference_point, yolo_results, min_balls_in_restricted=1, buffer_percentage=0.2):
        """
        Find closest ball to reference point, prioritizing restricted zone.
        Maintains original input/output structure while adding restricted zone logic.
        """
        # Early return if no valid data
        if yolo_results[0].boxes.data is None or len(yolo_results[0].boxes.data) == 0:
            return None

        # Find court boundaries
        court_bounds = None
        boxes = yolo_results[0].boxes.data.cpu().numpy()
        for box in boxes:
            x1, y1, x2, y2, conf, class_id = box
            if class_id == 0:  # Court detection
                court_bounds = (x1, y1, x2, y2)
                break

        if court_bounds is None:
            return None  # No court detected, maintain original behavior

        # Get restricted zone (only y values change, x remains same as court)
        restricted_zone = BallDetector._get_restricted_zone(court_bounds, buffer_percentage)

        # Track balls in restricted zone and court separately
        closest_restricted = None
        min_distance_restricted = float('inf')
        closest_court = None
        min_distance_court = float('inf')
        restricted_ball_count = 0

        # Process all balls
        for box in boxes:
            x1, y1, x2, y2, conf, class_id = box
            if class_id != 1:  # Not a ball
                continue

            ball_center = ((x1 + x2) / 2, (y1 + y2) / 2)
            
            # Skip if ball is outside court
            if not BallDetector._is_point_in_rectangle(ball_center, court_bounds):
                continue

            # Calculate distance
            distance = np.sqrt((reference_point[0] - ball_center[0])**2 +
                             (reference_point[1] - ball_center[1])**2)

            # Update closest ball in court
            if distance < min_distance_court:
                min_distance_court = distance
                closest_court = (int(x1), int(y1), int(x2), int(y2))

            # Check and update for restricted zone
            if BallDetector._is_point_in_rectangle(ball_center, restricted_zone):
                restricted_ball_count += 1
                if distance < min_distance_restricted:
                    min_distance_restricted = distance
                    closest_restricted = (int(x1), int(y1), int(x2), int(y2))

        # Return appropriate result based on restricted zone conditions
        if restricted_ball_count >= min_balls_in_restricted and closest_restricted is not None:
            return closest_restricted
        return closest_court

    @staticmethod
    def find_closest_ball_from_bot(bot_center, yolo_results):
        return BallDetector.find_closest_ball(bot_center, yolo_results)

    @staticmethod
    def find_closest_ball_from_goal_post(goal_post_center, yolo_results):
        return BallDetector.find_closest_ball(goal_post_center, yolo_results)