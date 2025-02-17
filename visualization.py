# visualization.py
import cv2

class Visualizer:
    @staticmethod
    def highlight_aruco(frame, ids, corners, bot_marker_id):
        if ids is not None:
            for i, id in enumerate(ids):
                if id == bot_marker_id:
                    cv2.putText(frame, f"Bot ID: {id[0]}", 
                              (int(corners[i][0][0][0]), int(corners[i][0][0][1]) - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.aruco.drawDetectedMarkers(frame, corners)

    @staticmethod
    def draw_ball_boxes(frame, results, target_ball):
        if results[0].boxes.data is not None and len(results[0].boxes.data) > 0:
            for box in results[0].boxes.data.cpu().numpy():
                x1, y1, x2, y2, conf, class_id = box
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), 
                            (255, 0, 0), 2)

                if target_ball is not None and (int(x1), int(y1), int(x2), int(y2)) == target_ball:
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), 
                                (0, 0, 255), 2)
