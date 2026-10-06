from ultralytics import YOLO
import cv2
import time

from detection.database import save_detection


# Load YOLO model
model = YOLO("yolo11n.pt")

# Camera
camera = cv2.VideoCapture(0)

# Save to database every 5 seconds
last_saved_time = 0
SAVE_INTERVAL = 5


def generate_frames():

    global last_saved_time

    while True:

        success, frame = camera.read()

        if not success:
            break

        # Run YOLO
        results = model(frame, verbose=False)

        person_count = 0

        for result in results:

            for box in result.boxes:

                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                # Person class
                if class_id == 0 and confidence > 0.5:

                    person_count += 1

                    x1, y1, x2, y2 = map(
                        int,
                        box.xyxy[0]
                    )

                    # Bounding box
                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2
                    )

                    # Label
                    label = f"Person {confidence:.2f}"

                    cv2.putText(
                        frame,
                        label,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

        # Display people count
        cv2.rectangle(
            frame,
            (10, 10),
            (300, 60),
            (0, 0, 0),
            -1
        )

        cv2.putText(
            frame,
            f"People Detected: {person_count}",
            (20, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        # Save detection every 5 seconds
        current_time = time.time()

        if (
            person_count > 0
            and current_time - last_saved_time >= SAVE_INTERVAL
        ):

            try:

                save_detection(person_count)

                last_saved_time = current_time

                print(
                    f"Saved detection: {person_count} people"
                )

            except Exception as error:

                print(
                    f"Database error: {error}"
                )

        # Encode frame
        success, buffer = cv2.imencode(
            ".jpg",
            frame
        )

        if not success:
            continue

        frame_bytes = buffer.tobytes()

        # Send frame to browser
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )


def release_camera():

    global camera

    if camera.isOpened():
        camera.release()