# Implementation Plan

## Phase 1: Mock-Based Prototype

Objective: prove the workflow without physical robot dependency.

Tasks:

1. Implement wake command detection.
2. Implement confirmation step.
3. Implement FastAPI backend.
4. Implement React dashboard.
5. Implement SQLite-based calendar/reminders.
6. Implement mock emotion detection.

Deliverable:

- System can be demonstrated from a laptop browser.

## Phase 2: Speech and Robot I/O

Objective: connect command input and response output to the robot.

Tasks:

1. Replace dashboard command input with Jupiter microphone input where available.
2. Replace mock speak output with Jupiter speaker output.
3. Keep dashboard as visual feedback for demonstration.

Deliverable:

- User can speak to the robot and hear responses.

## Phase 3: Vision Integration

Objective: replace mock emotion detection with real camera-based inference.

Tasks:

1. Capture frames from Jupiter camera.
2. Use OpenCV for face detection.
3. Crop face region.
4. Run CNN emotion classification.
5. Smooth predictions across recent frames.

Deliverable:

- Dashboard displays real-time estimated emotion.

## Phase 4: Evaluation

Suggested evaluation metrics:

- Wake command success rate.
- Confirmation success rate.
- Intent classification accuracy on predefined commands.
- Timer reliability.
- User satisfaction.
- Emotion detection stability across lighting and face-angle conditions.
