from ultralytics import YOLO
import cv2
import time
from database import save_detection


# Load YOLO model
model = YOLO("yolo11n.pt")

# Open MacBook camera
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("❌ Camera could not be opened")
    exit()

print("======================================")
print(" HUMAN DETECTION MANAGEMENT SYSTEM")
print("======================================")
print("✅ Camera started")
print("✅ YOLO model loaded")
print("Press Q to quit")
print("======================================")


# Last time data was saved
last_saved_time = 0

# Save detection every 5 seconds
SAVE_INTERVAL = 5


while True:

    success, frame = camera.read()

    if not success:
        print("❌ Failed to read camera")
        break

    # Run YOLO
    results = model(frame, verbose=False)

    person_count = 0

    # Process YOLO results
    for result in results:

        for box in result.boxes:

            class_id = int(box.cls[0])
            confidence = float(box.conf[0])

            # COCO class 0 = person
            if class_id == 0 and confidence > 0.5:

                person_count += 1

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                # Draw bounding box
                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                # Person label
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
    cv2.putText(
        frame,
        f"People Detected: {person_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    # Current time
    current_time = time.time()

    # Save to database every 5 seconds
    if person_count > 0:

        if current_time - last_saved_time >= SAVE_INTERVAL:

            try:

                save_detection(person_count)

                last_saved_time = current_time

                print(
                    f"💾 Saved: {person_count} people"
                )

            except Exception as error:

                print(
                    f"❌ Database error: {error}"
                )

    # Display camera
    cv2.imshow(
        "Human Detection Management System",
        frame
    )

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


camera.release()
cv2.destroyAllWindows()

print("👋 Human Detection System stopped")