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

# States
showFPS = True
showOverlay = True
manualMode = False
resolution = (1920, 1080)

# Detection variables
boxes = []
classes = []
scores = []
scoreThreshold = 0.4

# Center tracking
centers = []
nextId = 0
timeout = 2
baseDistance = 0.5

# FPS
captureFPS = 0
detectionFPS = 0
prevCapture = time.time()
prevDetection = time.time()

# Use VideoConfiguration for faster GPU capture (still outputs NumPy arrays)
cameraConfig = picam2.create_video_configuration(
    main={"size": resolution, "format": "RGB888"}
)
picam2.configure(cameraConfig)
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

# Detection
def detectPerson(frame):
    global boxes, classes, scores
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

# Detection results
def drawOverlay(frame):
    h, w, _ = frame.shape
    for i in range(len(boxes)):
        ymin, xmin, ymax, xmax = boxes[i]
        x1, y1 = int(xmin * w), int(ymin * h)
        x2, y2 = int(xmax * w), int(ymax * h)
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"Person {scores[i]:.2f}", (x1, max(y1 - 10, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    for c in centers:
        cx, cy = int(c["x"] * w), int(c["y"] * h)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
        cv2.putText(frame, f"ID {c['id']}", (cx + 5, cy - 5),
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

        if showOverlay:
            processedFrame = drawOverlay(frame)

        captureFPS = 1 / (time.time() - prevCapture)
        prevCapture = time.time()
        
        if showFPS:
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

    # Compute normalized centers and box sizes
    newCenters = []
    for box in boxes:
        ymin, xmin, ymax, xmax = box
        x = (xmin + xmax) / 2
        y = (ymin + ymax) / 2
        w = xmax - xmin
        h = ymax - ymin
        newCenters.append((x, y, w, h))

    for (x, y, w, h) in newCenters:
        matched = None
        minDistance = float("inf")

        for c in centers:
            distance = np.hypot(c["x"] - x, c["y"] - y)
            timeDiff = now - c["lastUpdated"]
            maxDistance = baseDistance * max(w, h) * (1.0 + timeDiff)

            if distance < minDistance and distance < maxDistance:
                minDistance = distance
                matched = c

        if matched:
            matched["x"], matched["y"], matched["lastUpdated"] = x, y, now
            updatedCenters.append(matched)
        else:
            updatedCenters.append({"id": nextId, "x": x, "y": y, "lastUpdated": now})
            nextId += 1

    for center in centers:
        if not any(center["id"] == c["id"] for c in updatedCenters):
            updatedCenters.append(center)

    # Remove expired centers
    centers = [c for c in updatedCenters if (now - c["lastUpdated"]) < timeout]

# Detection loop
def detectionLoop():
    global boxes, detectionFPS, prevDetection
    while True:
        if !manualMode:
            with lock:
                detectionFrame = None if latestFrame is None else latestFrame.copy()

            if detectionFrame is not None:
                detectPerson(detectionFrame)
                updateCenters(boxes)

            detectionFPS = 1 / (time.time() - prevDetection)
            prevDetection = time.time()
        else:
            detectionFPS = 0

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


@app.route('/api/toggle', methods=['POST'])
def handle_toggle():
    data = request.json
    key = data.get("key")
    value = data.get("value")

    if key == "fps":
        showFPS = value
    elif key == "overlay":
        showOverlay = value
    elif key == "manual":
        manualMode = value
    else:
        return jsonify({"status": "error", "message": "Unknown key"}), 400

    return jsonify({"status": "ok", key: value})

@app.route('/api/resolution', methods=['POST'])
def handle_resolution():
    global picam2
    
    data = request.json
    resolution = data.get("resolution")
    
    if resolution == "420p":
        resolution = (640, 480)
    elif resolution == "720p":
        resolution = (1280, 720)
    elif resolution == "1080p":
        resolution = (1920, 1080)
    else:
        return jsonify({"status": "error", "message": "Invalid resolution"}), 400

    with lock:
        picam2.stop()
        
        cameraConfig = picam2.create_video_configuration(
            main={"size": resolution, "format": "RGB888"}
        )
        picam2.configure(cameraConfig)
        picam2.start()
    
    return jsonify({"status": "ok", "resolution": resolution})

@app.route('/api/joystick', methods=['POST'])
def handle_joystick():
    data = request.json
    direction = data.get("direction")
    
    return jsonify({"status": "ok", "direction": direction})

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