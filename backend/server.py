#!/usr/bin/env python3
import threading
import time
import cv2
import numpy as np
from flask import Flask, Response
from picamera2 import Picamera2, Preview
import tflite_runtime.interpreter as tflite

app = Flask(__name__)

# Camera setup
picam2 = Picamera2()

# Use VideoConfiguration for faster GPU capture (still outputs NumPy arrays)
camera_config = picam2.create_video_configuration(
    main={"size": (1920, 1080), "format": "RGB888"}
)
picam2.configure(camera_config)
picam2.start()

# TFLite setup
model_path = "model.tflite"
interpreter = tflite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Shared variables
lock = threading.Lock()
output_frame = None           # MJPEG frame for streaming
latest_frame = None           # Raw frame for detection
boxes = classes = scores = None  # Latest detection results

# Detection
def detect_person(frame):
    if frame is None:
        return None, None, None

    frame = np.ascontiguousarray(frame)
    img = cv2.resize(frame, (320, 320))
    input_data = np.expand_dims(img, axis=0).astype(np.uint8)

    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()

    boxes = interpreter.get_tensor(output_details[0]['index'])[0]
    classes = interpreter.get_tensor(output_details[1]['index'])[0].astype(int)
    scores = interpreter.get_tensor(output_details[2]['index'])[0]

    return boxes, classes, scores

# Detection results
def draw_boxes(frame, boxes, classes, scores):
    if boxes is None:
        return frame

    h, w, _ = frame.shape
    for i in range(len(scores)):
        if scores[i] > 0.40 and classes[i] == 0:
            ymin, xmin, ymax, xmax = boxes[i]
            x1, y1 = int(xmin * w), int(ymin * h)
            x2, y2 = int(xmax * w), int(ymax * h)
            if x1 < x2 and y1 < y2:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"Person {scores[i]:.2f}", (x1, max(y1 - 10, 0)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return frame

# Capture loop (produces MJPEG using CPU encoding)
def capture_loop():
    global latest_frame, output_frame

    while True:
        # Capture raw frame
        frame = picam2.capture_array()

        # Copy for detection thread
        with lock:
            latest_frame = frame.copy()
            current_boxes = boxes
            current_classes = classes
            current_scores = scores

        # Draw boxes on the frame
        frame_with_boxes = draw_boxes(frame, current_boxes, current_classes, current_scores)

        # Encode as JPEG
        ret, jpeg = cv2.imencode('.jpg', frame_with_boxes)
        if not ret:
            continue

        with lock:
            output_frame = jpeg.tobytes()

# Detection loop
def detection_loop():
    global boxes, classes, scores
    while True:
        with lock:
            frame_for_detection = None if latest_frame is None else latest_frame.copy()

        if frame_for_detection is not None:
            boxes, classes, scores = detect_person(frame_for_detection)
        time.sleep(0.03)

# MJPEG streaming
def generate_mjpeg():
    global output_frame
    while True:
        with lock:
            if output_frame is None:
                continue
            frame = output_frame
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    return Response(generate_mjpeg(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Start threads
if __name__ == '__main__':
    t1 = threading.Thread(target=capture_loop, daemon=True)
    t2 = threading.Thread(target=detection_loop, daemon=True)
    t1.start()
    t2.start()

    app.run(host='0.0.0.0', port=8000, threaded=True)