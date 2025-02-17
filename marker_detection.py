# marker_detection.py
import cv2
import numpy as np
import math

class MarkerDetector:
    def __init__(self):
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_1000)
        self.aruco_params = cv2.aruco.DetectorParameters()

    def detect_markers(self, frame):
        return cv2.aruco.detectMarkers(frame, self.aruco_dict, parameters=self.aruco_params)

    @staticmethod
    def calculate_angle(pt1, pt2):
        delta_y = pt2[1] - pt1[1]
        delta_x = pt2[0] - pt1[0]
        return math.atan2(delta_y, delta_x) * 180 / np.pi

    @staticmethod
    def get_bot_front_center(top_left, top_right):
        return (round((top_left[0] + top_right[0]) / 2),
                round((top_left[1] + top_right[1]) / 2))

    def process_bot_marker(self, corner):
        marker_corners = corner[0]
        bottom_left = marker_corners[3]
        bottom_right = marker_corners[2]
        top_right = marker_corners[1]
        bot_front_center = self.get_bot_front_center(bottom_left, bottom_right)
        # orientation_angle = self.calculate_angle(bottom_left, bottom_right)
        orientation_angle = self.calculate_angle(top_right, bottom_right)
        return bot_front_center, orientation_angle

    @staticmethod
    def process_aruco_marker(corner):
        marker_corners = corner[0]
        top_left = marker_corners[0]
        top_right = marker_corners[1]
        # bottom_right = marker_corners[2]
        return (round((top_left[0] + top_right[0]) / 2),
                round((top_left[1] + top_right[1]) / 2))