import pickle

import cv2
import mediapipe
import numpy as np

modelDict = pickle.load(open('./modelTa.p', 'rb'))
model = modelDict['modelT']

cap = cv2.VideoCapture(0)

hands = mediapipe.solutions.hands
drawing = mediapipe.solutions.drawing_utils
drawingStyles = mediapipe.solutions.drawing_styles

mpHands = hands.Hands(static_image_mode=True, min_detection_confidence=0.3)

labels_dict = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h', 8: 'i', 9: 'j', 10: 'k', 11: 'l', 12: 'm', 13: 'n', 14: 'o', 15: 'p', 16: 'q', 17: 'r', 18: 's', 19: 't', 20: 'u', 21: 'v', 22: 'w', 23: 'x', 24: 'y', 25:'z', 26: 'A', 27: 'B', 28: 'C'}
while True:

    landmarkCoords = []
    x_ = []
    y_ = []

    ret, frame = cap.read()

    H, W, _ = frame.shape

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = mpHands.process(frame_rgb)
    if results.multi_hand_landmarks:
        for handLandmarks in results.multi_hand_landmarks:
            drawing.draw_landmarks(
                frame,  # image to draw
                handLandmarks,  # model output
                hands.HAND_CONNECTIONS,  # hand connections
                drawingStyles.get_default_hand_landmarks_style(),
                drawingStyles.get_default_hand_connections_style())

        for handLandmarks in results.multi_hand_landmarks:
            for i in range(len(handLandmarks.landmark)):
                x = handLandmarks.landmark[i].x
                y = handLandmarks.landmark[i].y

                x_.append(x)
                y_.append(y)

            for i in range(len(handLandmarks.landmark)):
                x = handLandmarks.landmark[i].x
                y = handLandmarks.landmark[i].y
                landmarkCoords.append(x - min(x_))
                landmarkCoords.append(y - min(y_))

        x1 = int(min(x_) * W) - 10
        y1 = int(min(y_) * H) - 10

        x2 = int(max(x_) * W) - 10
        y2 = int(max(y_) * H) - 10
        if len(landmarkCoords) == 42:
            landmarkCoords = np.expand_dims(landmarkCoords, axis=0)
            prediction = model.predict([np.asarray(landmarkCoords)])
            predictedIndex = np.argmax(prediction[0])  # This finds the index of the highest probability
            predictedCharacter = labels_dict[predictedIndex]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), 4)
        cv2.putText(frame, predictedCharacter, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3,
                    cv2.LINE_AA)

    cv2.imshow('frame', frame)
    cv2.waitKey(1)


cap.release()
cv2.destroyAllWindows()