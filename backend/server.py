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
    main={"size": (1280, 720), "format": "RGB888"}
)
picam2.configure(camera_config)
picam2.start()

# TFLite setup
modelPath = "model.tflite"
interpreter = tflite.Interpreter(model_path=modelPath)
interpreter.allocate_tensors()
inputDetails = interpreter.get_input_details()
outputDetails = interpreter.get_output_details()

# Streaming
lock = threading.Lock() # To prevent corruption
outputFrame = None # MJPEG frame for streaming
latestFrame = None # Raw frame for detection

# Detection variables
boxes = []
classes = []
scores = []
scoreThreshold = 0.3

# Center tracking
centers = []
nextId = 0
timeout = 1000
baseDistance = 200

# FPS
captureFPS = 0
detectionFPS = 0
prevCapture = time.time()
prevDetection = time.time()

# Detection
def detectPerson(frame):
    if frame is None:
        return [], [], []

    frame = np.ascontiguousarray(frame)
    img = cv2.resize(frame, (320, 320))
    input_data = np.expand_dims(img, axis=0).astype(np.uint8)

    interpreter.set_tensor(inputDetails[0]['index'], input_data)
    interpreter.invoke()

    boxes = interpreter.get_tensor(outputDetails[0]['index'])[0]
    classes = interpreter.get_tensor(outputDetails[1]['index'])[0].astype(int)
    scores = interpreter.get_tensor(outputDetails[2]['index'])[0]

    validIndices = np.where((scores >= scoreThreshold) & (classes == 0))[0]
    boxes = boxes[validIndices]
    classes = classes[validIndices]
    scores = scores[validIndices]

    return boxes, classes, scores

# Detection results
def drawBoxes(frame, boxes, classes, scores):
    if boxes is None:
        return frame

    h, w, _ = frame.shape
    for i in range(len(boxes)):
        ymin, xmin, ymax, xmax = boxes[i]
        x1, y1 = int(xmin * w), int(ymin * h)
        x2, y2 = int(xmax * w), int(ymax * h)
        if x1 < x2 and y1 < y2:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"Person {scores[i]:.2f}", (x1, max(y1 - 10, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    for c in centers:
        cv2.circle(frame, (c["x"], c["y"]), 5, (0, 0, 255), -1)
        cv2.putText(frame, f"ID {c['id']}", (c["x"] + 5, c["y"] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    return frame

# Capture loop (produces MJPEG using CPU encoding)
def captureLoop():
    global latestFrame, outputFrame, captureFPS, prevCapture

    while True:
        # Capture raw frame
        frame = picam2.capture_array()

        # Copy for detection thread
        with lock:
            latestFrame = frame.copy()
            currentBoxes = boxes
            currentClasses = classes
            currentScores = scores

        # Draw boxes on the frame
        processedFrame = drawBoxes(frame, currentBoxes, currentClasses, currentScores)

        captureFPS = 1 / (time.time() - prevCapture)
        prevCapture = time.time()
        
        cv2.putText(processedFrame, f"FPS: {captureFPS:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(processedFrame, f"Detection FPS: {detectionFPS:.1f}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        # Encode as JPEG
        ret, jpeg = cv2.imencode('.jpg', processedFrame)
        if not ret:
            continue

        with lock:
            outputFrame = jpeg.tobytes()

# Center tracking
def updateCenters(boxes):
    global centers, nextId

    now = time.time()
    updatedCenters = []

    # Compute centers from new boxes
    newCenters = []
    for box in boxes:
        ymin, xmin, ymax, xmax = box
        x = int((xmin + xmax) / 2 * 1280)  # assuming 1280x720 frame
        y = int((ymin + ymax) / 2 * 720)
        newCenters.append((x, y, abs(xmax - xmin), abs(ymax - ymin)))

    # Match new centers to existing ones
    for (x, y, boxWidth, boxHeight) in newCenters:
        matched = False
        for c in centers:
            distance = np.hypot(c["x"] - x, c["y"] - y)
            timeDiff = (now - c["lastUpdated"]) * 1000 
            boxSize = min(boxWidth, boxHeight)
        
            boxSizeFactor = max(0.5, boxSize / 200, 3.0)
            timeFactor = 1.0 + min(timeDiff / 100.0, 5.0) 

            maxDistance = baseDistance * boxSizeFactor * timeFactor

            # Update existing center
            if distance < maxDistance:
                c["x"], c["y"], c["lastUpdated"] = x, y, now
                updatedCenters.append(c)
                matched = True
                break

        # Create a new center
        if not matched:
            newCenter = {"id": nextId, "x": x, "y": y, "lastUpdated": now}
            nextId += 1
            updatedCenters.append(newCenter)

    # Remove expired centers
    centers = [c for c in updatedCenters if (now - c["lastUpdated"]) < timeout]

# Detection loop
def detectionLoop():
    global boxes, classes, scores, detectionFPS, prevDetection
    while True:
        with lock:
            frame_for_detection = None if latestFrame is None else latestFrame.copy()

        if frame_for_detection is not None:
            boxes, classes, scores = detectPerson(frame_for_detection)
            updateCenters(boxes)

        detectionFPS = 1 / (time.time() - prevDetection)
        prevDetection = time.time()

# MJPEG streaming
def generateMjpeg():
    global outputFrame
    while True:
        with lock:
            if outputFrame is None:
                continue
            frame = outputFrame
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.03)

@app.route('/video')
def videoFeed():
    return Response(generateMjpeg(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Start threads
if __name__ == '__main__':
    t1 = threading.Thread(target=captureLoop, daemon=True)
    t2 = threading.Thread(target=detectionLoop, daemon=True)
    t1.start()
    t2.start()

    app.run(host='0.0.0.0', port=8000, threaded=True)