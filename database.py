import mysql.connector
from datetime import datetime


def get_connection():

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="MyNewPassword@123",
        database="human_detection_db"
    )


def save_detection(people_count):

    connection = get_connection()
    cursor = connection.cursor()

    now = datetime.now()

    query = """
        INSERT INTO detections
        (
            detection_date,
            detection_time,
            people_count,
            camera_source
        )
        VALUES (%s, %s, %s, %s)
    """

    values = (
        now.date(),
        now.time(),
        people_count,
        "MacBook Camera"
    )

    cursor.execute(query, values)

    connection.commit()

    cursor.close()
    connection.close()

    print(f"✅ Saved detection: {people_count} people")