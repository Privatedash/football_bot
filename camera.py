# camera.py
import cv2
import queue
import threading

class CameraManager:
    def __init__(self, video_url):
        self.video_url = video_url
        self.frame_queue = queue.Queue(maxsize=1)
        self.is_running = True

    def start_capture(self):
        self.capture_thread = threading.Thread(target=self._capture_frames)
        self.capture_thread.start()

    def _capture_frames(self):
        cap = cv2.VideoCapture(self.video_url)
        while self.is_running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if self.frame_queue.full():
                _ = self.frame_queue.get()
            self.frame_queue.put(frame)

        cap.release()

    def get_frame(self):
        return self.frame_queue.get()

    def stop(self):
        self.is_running = False
        self.capture_thread.join()
