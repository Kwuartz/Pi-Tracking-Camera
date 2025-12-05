#!/usr/bin/env python3
import os
import cv2
import time
import pigpio
import threading
import numpy as np
from flask_cors import CORS
from flask import Flask, Response, request, jsonify, send_from_directory
from picamera2 import Picamera2, Preview
import tflite_runtime.interpreter as tflite

app = Flask(__name__)
CORS(app)

FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")

# Camera setup
picam2 = Picamera2()

# Servo setup
pi = pigpio.pi()

# Servo settings
TILT_GPIO = 2
PAN_GPIO = 3

MIN_PULSE = 500
MAX_PULSE = 2400

PAN_SPEED = 20
TILT_SPEED = 20
Kp = 15

# States
showFPS = False
showOverlay = False
manual = False
tracking = False
resolution = (1600, 900)

# Detection variables
boxes = []
classes = []
scores = []
scoreThreshold = 0.4

# Center tracking
centers = []
currentTarget = 0
nextId = 0
timeout = 1
deadzone = 0.2
baseDistance = 1

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

# Conversion
def angleToMicro(angle):
    return MIN_PULSE + (angle / 180.0) * (MAX_PULSE - MIN_PULSE)

# Start angles
panAngle = 90
tiltAngle = 135
pi.set_servo_pulsewidth(PAN_GPIO, angleToMicro(panAngle))
pi.set_servo_pulsewidth(TILT_GPIO, angleToMicro(tiltAngle))

manualIncrement = -1

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
    if boxes is None or len(boxes) != len(scores):
        return frame

    h, w, _ = frame.shape

    for i in range(len(boxes)):
        try:
            ymin, xmin, ymax, xmax = boxes[i]
            x1, y1 = int(xmin * w), int(ymin * h)
            x2, y2 = int(xmax * w), int(ymax * h)
        
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        except:
            pass
        
        try:
            cv2.putText(frame, f"Person {scores[i]:.2f}", (x1, max(y1 - 10, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        except IndexError:
            pass
    
    for c in centers:
        if c["active"]:
            cx, cy = int(c["x"] * w), int(c["y"] * h)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"ID {c['id']}", (cx + 5, cy - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    return frame

# Capture loop (produces MJPEG using CPU encoding)
def captureLoop():
    global latestFrame, outputFrame, captureFPS, prevCapture

    while True:
        time.sleep(0.03)

        # Capture raw frame
        frame = picam2.capture_array()

        # Copy for detection thread
        with lock:
            latestFrame = frame.copy()
            currentBoxes = boxes
            currentClasses = classes
            currentScores = scores
            
        deltaTime = time.time() - prevCapture
        captureFPS = 1 / (deltaTime)
        prevCapture = time.time()
        
        if showFPS:
            cv2.putText(frame, f"FPS: {captureFPS:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame, f"Detection FPS: {detectionFPS:.1f}", (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        if showOverlay:
            frame = drawOverlay(frame)

        # Encode as JPEG
        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not ret:
            continue

        with lock:
            outputFrame = jpeg.tobytes()

def trackCenters(dt):
    global panAngle, tiltAngle, currentTarget
    
    if len(centers) > 0:
        target = next((center for center in centers if center["id"] == currentTarget), None)
        
        if not target:
            target = centers[0]
            currentTarget = target["id"]

        if target["active"]:
            cx, cy = target["x"], target["y"]

            xError = 0.5 - cx
            yError = 0.5 - cy
            
            panDelta = Kp * xError
            tiltDelta = Kp * -yError


            if abs(panDelta) > deadzone:
                panAngle += max(-PAN_SPEED * dt, min(PAN_SPEED * dt, panDelta))
                panAngle = max(0, min(180, panAngle))
                pi.set_servo_pulsewidth(PAN_GPIO, angleToMicro(panAngle))

            if abs(tiltDelta) > 0.4:
                tiltAngle += max(-TILT_SPEED * dt, min(TILT_SPEED * dt, tiltDelta))  
                tiltAngle = max(0, min(180, tiltAngle))
                pi.set_servo_pulsewidth(TILT_GPIO, angleToMicro(tiltAngle))

# Center tracking
def updateCenters(boxes):
    global centers, nextId

    now = time.time()
    updatedCenters = []

    # Compute normalized centers and box sizes
    newCenters = []
    for box in boxes:
        ymin, xmin, ymax, xmax = box
        w = xmax - xmin
        h = ymax - ymin

        x = xmin + (w / 2)
        y = ymin + (h / 3)

        newCenters.append((x, y))

    for (x, y) in newCenters:
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
            matched["x"], matched["y"], matched["lastUpdated"], matched["active"] = x, y, now, True
            updatedCenters.append(matched)
        else:
            updatedCenters.append({"id": nextId, "x": x, "y": y, "lastUpdated": now, "active": True})
            nextId += 1

    for center in centers:
        if not any(center["id"] == c["id"] for c in updatedCenters):
            center["active"] == False
            updatedCenters.append(center)

    # Remove expired centers
    centers = [c for c in updatedCenters if (now - c["lastUpdated"]) < timeout]

# Detection loop
def detectionLoop():
    global boxes, detectionFPS, prevDetection
    while True:
        if tracking:
            with lock:
                detectionFrame = None if latestFrame is None else latestFrame.copy()

            deltaTime = (time.time() - prevDetection)
            detectionFPS = 1 / deltaTime
            prevDetection = time.time()

            if detectionFrame is not None:
                detectPerson(detectionFrame)
                updateCenters(boxes)

                if not manual:
                    trackCenters(deltaTime)
        else:
            detectionFPS = 0
            time.sleep(0.2)

# MJPEG streaming
def generateMjpeg():
    global outputFrame
    while True:
        with lock:
            frame = outputFrame
        if frame is None:
            time.sleep(0.01)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.03)


@app.route('/api/toggle', methods=['POST'])
def handleToggle():
    global showFPS, showOverlay, manual, tracking
    data = request.json
    key = data.get("key")
    value = data.get("value")

    if key == "fps":
        showFPS = value
    elif key == "overlay":
        showOverlay = value
    elif key == "manual":
        manual = value
    elif key == "tracking":
        tracking = value
    else:
        return jsonify({"status": "error", "message": "Unknown key"}), 400

    return jsonify({"status": "ok", key: value})

@app.route('/api/resolution', methods=['POST'])
def handleResolution():
    global picam2
    
    data = request.json
    resolution = data.get("resolution")

    if resolution == "900p":
        resolution = (1600, 900)
    elif resolution == "720p":
        resolution = (1280, 720)
    elif resolution == "1080p":
        resolution = (1920, 1080)
    else:
        print("not work")
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
def handleJoystick():
    global panAngle, tiltAngle

    data = request.json
    direction = data.get("direction")
    
    if direction:  # Discrete mode
        if direction == "left":
            panAngle = max(0, panAngle - manualIncrement)
            pi.set_servo_pulsewidth(PAN_GPIO, angleToMicro(panAngle))
        elif direction == "right":
            panAngle = min(180, panAngle + manualIncrement)
            pi.set_servo_pulsewidth(PAN_GPIO, angleToMicro(panAngle))
        elif direction == "up":
            tiltAngle = min(180, tiltAngle + manualIncrement)
            pi.set_servo_pulsewidth(TILT_GPIO, angleToMicro(tiltAngle))
        elif direction == "down":
            tiltAngle = max(0, tiltAngle - manualIncrement)
            pi.set_servo_pulsewidth(TILT_GPIO, angleToMicro(tiltAngle))
        else:
            return jsonify({"status": "error", "message": "Invalid direction"}), 400
        
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "error", "message": "Missing direction or x/y"}), 400

    time.sleep(0.01)

@app.route('/video')
def videoFeed():
    return Response(generateMjpeg(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path == "" or path == "index.html":
        return send_from_directory(FRONTEND_DIST, "index.html")
    return send_from_directory(FRONTEND_DIST, path)

# Start threads
if __name__ == '__main__':
    t1 = threading.Thread(target=captureLoop, daemon=True)
    t2 = threading.Thread(target=detectionLoop, daemon=True)
    t1.start()
    t2.start()

    app.run(host='0.0.0.0', port=8000, threaded=True)