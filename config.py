class Config:
    NODEMCU_IP = "192.168.0.100"  #INSTANTA2 IP
    VIDEO_URL = "http://192.168.0.101:8080/video"
    # VIDEO_URL = 0
    BOT_MARKER_ID = 600
    GOAL_POST_MARKER_ID = 360
    BALL_PROXIMITY_THRESHOLD = 45
    YOLO_MODEL_PATH = "yolo_models/v1/best.pt"
    BALL_ANGLE_THRESHOLD = 10 # Offset for bot-ball align angle (-5 degree to 5 degree)
    GOAL_ANGLE_THRESHOLD = 10 # Offset for bot-goalpost align angle (-5 degree to 5 degree)
    TRAP_DURATION = 7  # Maximum number of seconds the bot is allowed to hold the ball
    RELEASE_DURATION = 1 # Number of seconds the bot releases the ball after the holding time exceeds 4spython3