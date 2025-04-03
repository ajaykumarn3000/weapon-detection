import time
from collections import deque

import cv2
import schedule
from ultralytics import YOLO

from telegram_bot import send_message, send_video, update_subscribers

# CONFIGURABLE PARAMETERS
DETECTION_CLASS_NAME = "weapon"  # Match your model's class label
BUFFER_SECONDS = 10  # Buffer for last 10 seconds
TRIGGER_SECONDS = 2  # Time weapon must persist to start recording
END_SECONDS = 20  # Time without weapon to stop recording
FRAME_WIDTH, FRAME_HEIGHT = 1080, 720
FPS = 10  # Approximate FPS

# Input source
camera = (
    input(
        "Enter camera URL (eg: http://192.168.1.1:8080/video) \n(or leave blank for webcam): "
    )
    or 0
)
cap = cv2.VideoCapture(camera)

# Load YOLO model
model = YOLO("./best.pt")

if not cap.isOpened():
    print("Error: Unable to access the camera.")
    exit()

# Rolling frame buffer
frame_buffer = deque(maxlen=BUFFER_SECONDS * FPS)

# State variables
recording = False
record_start_time = None
last_weapon_time = None
weapon_persistence_time = 0
video_writer = None


# Start recording
def start_recording():
    global video_writer, recording, record_start_time, filename
    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    record_start_time = time.strftime("%Y%m%d-%H%M%S")
    filename = f"weapon_detected_{record_start_time}.mp4"
    video_writer = cv2.VideoWriter(filename, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))
    for buffered_frame in frame_buffer:
        video_writer.write(buffered_frame)
    recording = True
    message = "🚨 ALERT: Weapon detected! Started recording."
    print(message)
    send_message(message)


# Stop recording
def stop_recording():
    global video_writer, recording, filename
    if video_writer:
        video_writer.release()
        video_writer = None
        print("✅ Saved video and stopped recording.")
        send_video(filename)  # Assuming the file is written to at this point
    recording = False


schedule.every().minute.do(update_subscribers)
# Main loop
while True:
    schedule.run_pending()
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
    frame_buffer.append(frame.copy())

    results = model(frame, stream=True, conf=0.5)

    weapon_detected = False

    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            conf = box.conf[0].item()
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            label = f"{result.names[cls]} {conf:.2f}"

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

            weapon_detected = True

    current_time = time.time()

    if weapon_detected:
        if last_weapon_time is None:
            last_weapon_time = current_time
        weapon_persistence_time = current_time - last_weapon_time

        if not recording and weapon_persistence_time > TRIGGER_SECONDS:
            start_recording()
    else:
        if last_weapon_time is not None:
            if (current_time - last_weapon_time) > END_SECONDS and recording:
                stop_recording()
            if not recording:
                last_weapon_time = None
                weapon_persistence_time = 0

    # Write frame to file if recording
    if recording and video_writer:
        video_writer.write(frame)

    # Display
    cv2.imshow("YOLOv8 Weapon Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Cleanup
cap.release()
if video_writer:
    video_writer.release()
cv2.destroyAllWindows()
