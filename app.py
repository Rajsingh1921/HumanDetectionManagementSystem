from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    Response,
    request,
    redirect,
    url_for,
    send_file,
    session
)

import mysql.connector
import csv
import io
from functools import wraps

from detection.live_detection import generate_frames


app = Flask(__name__)

# IMPORTANT:
# Change this to a random secret value for your project.
app.secret_key = "HDMS_SECRET_KEY_2026"


# =========================================
# DATABASE CONNECTION
# =========================================

import os

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "human_detection_db")
    )


# =========================================
# LOGIN REQUIRED DECORATOR
# =========================================

def login_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return decorated_function


# =========================================
# LOGIN
# =========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, username, role
            FROM users
            WHERE username = %s
            AND password = %s
            """,
            (username, password)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user:

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


# =========================================
# LOGOUT
# =========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================
# DASHBOARD
# =========================================

@app.route("/")
@login_required
def dashboard():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT COUNT(*) AS total FROM detections"
    )

    total_detections = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM detections
        WHERE detection_date = CURDATE()
        """
    )

    today_detections = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COALESCE(SUM(people_count), 0) AS total
        FROM detections
        """
    )

    total_people = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT
            id,
            detection_date,
            detection_time,
            people_count,
            camera_source
        FROM detections
        ORDER BY id DESC
        LIMIT 10
        """
    )

    detections = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "dashboard.html",
        total_detections=total_detections,
        today_detections=today_detections,
        total_people=total_people,
        detections=detections
    )


# =========================================
# LIVE DETECTION
# =========================================

@app.route("/live")
@login_required
def live():

    return render_template("detection.html")


@app.route("/video_feed")
@login_required
def video_feed():

    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# =========================================
# DETECTION HISTORY
# =========================================

@app.route("/history")
@login_required
def history():

    search = request.args.get("search", "").strip()
    selected_date = request.args.get("date", "").strip()

    page = request.args.get("page", 1, type=int)

    if page < 1:
        page = 1

    per_page = 10

    offset = (page - 1) * per_page

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    conditions = []
    parameters = []

    if search:

        conditions.append(
            "camera_source LIKE %s"
        )

        parameters.append(
            f"%{search}%"
        )

    if selected_date:

        conditions.append(
            "detection_date = %s"
        )

        parameters.append(
            selected_date
        )

    where_clause = ""

    if conditions:

        where_clause = (
            "WHERE " +
            " AND ".join(conditions)
        )

    count_query = f"""
        SELECT COUNT(*) AS total
        FROM detections
        {where_clause}
    """

    cursor.execute(
        count_query,
        tuple(parameters)
    )

    total_records = cursor.fetchone()["total"]

    history_query = f"""
        SELECT
            id,
            detection_date,
            detection_time,
            people_count,
            camera_source
        FROM detections
        {where_clause}
        ORDER BY id DESC
        LIMIT %s OFFSET %s
    """

    history_parameters = (
        parameters +
        [per_page, offset]
    )

    cursor.execute(
        history_query,
        tuple(history_parameters)
    )

    detections = cursor.fetchall()

    cursor.close()
    connection.close()

    total_pages = (
        total_records +
        per_page -
        1
    ) // per_page

    return render_template(
        "history.html",
        detections=detections,
        search=search,
        selected_date=selected_date,
        page=page,
        total_pages=total_pages,
        total_records=total_records
    )


# =========================================
# DELETE DETECTION
# =========================================

@app.route(
    "/delete/<int:detection_id>",
    methods=["POST"]
)
@login_required
def delete_detection(detection_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM detections WHERE id = %s",
        (detection_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(
        url_for("history")
    )


# =========================================
# REPORTS
# =========================================

@app.route("/reports")
@login_required
def reports():

    start_date = request.args.get(
        "start_date",
        ""
    ).strip()

    end_date = request.args.get(
        "end_date",
        ""
    ).strip()

    connection = get_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    conditions = []
    parameters = []

    if start_date:

        conditions.append(
            "detection_date >= %s"
        )

        parameters.append(
            start_date
        )

    if end_date:

        conditions.append(
            "detection_date <= %s"
        )

        parameters.append(
            end_date
        )

    where_clause = ""

    if conditions:

        where_clause = (
            "WHERE " +
            " AND ".join(conditions)
        )

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM detections
        {where_clause}
        """,
        tuple(parameters)
    )

    total_detections = (
        cursor.fetchone()["total"]
    )

    cursor.execute(
        f"""
        SELECT
            COALESCE(
                SUM(people_count),
                0
            ) AS total
        FROM detections
        {where_clause}
        """,
        tuple(parameters)
    )

    total_people = (
        cursor.fetchone()["total"]
    )

    cursor.execute(
        f"""
        SELECT
            COALESCE(
                AVG(people_count),
                0
            ) AS average
        FROM detections
        {where_clause}
        """,
        tuple(parameters)
    )

    average_people = (
        cursor.fetchone()["average"]
    )

    cursor.execute(
        f"""
        SELECT
            COALESCE(
                MAX(people_count),
                0
            ) AS maximum
        FROM detections
        {where_clause}
        """,
        tuple(parameters)
    )

    maximum_people = (
        cursor.fetchone()["maximum"]
    )

    cursor.execute(
        f"""
        SELECT
            detection_date,
            COUNT(*) AS detections,
            SUM(people_count) AS people
        FROM detections
        {where_clause}
        GROUP BY detection_date
        ORDER BY detection_date ASC
        """,
        tuple(parameters)
    )

    daily_data = cursor.fetchall()

    cursor.close()
    connection.close()

    dates = [
        str(row["detection_date"])
        for row in daily_data
    ]

    detection_counts = [
        row["detections"]
        for row in daily_data
    ]

    people_counts = [
        row["people"]
        for row in daily_data
    ]

    return render_template(
        "reports.html",
        start_date=start_date,
        end_date=end_date,
        total_detections=total_detections,
        total_people=total_people,
        average_people=round(
            float(average_people),
            2
        ),
        maximum_people=maximum_people,
        dates=dates,
        detection_counts=detection_counts,
        people_counts=people_counts,
        daily_data=daily_data
    )


# =========================================
# EXPORT CSV
# =========================================

@app.route("/export-report")
@login_required
def export_report():

    start_date = request.args.get(
        "start_date",
        ""
    ).strip()

    end_date = request.args.get(
        "end_date",
        ""
    ).strip()

    connection = get_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    conditions = []
    parameters = []

    if start_date:

        conditions.append(
            "detection_date >= %s"
        )

        parameters.append(
            start_date
        )

    if end_date:

        conditions.append(
            "detection_date <= %s"
        )

        parameters.append(
            end_date
        )

    where_clause = ""

    if conditions:

        where_clause = (
            "WHERE " +
            " AND ".join(conditions)
        )

    cursor.execute(
        f"""
        SELECT
            id,
            detection_date,
            detection_time,
            people_count,
            camera_source
        FROM detections
        {where_clause}
        ORDER BY
            detection_date DESC,
            detection_time DESC
        """,
        tuple(parameters)
    )

    records = cursor.fetchall()

    cursor.close()
    connection.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Detection Date",
        "Detection Time",
        "People Count",
        "Camera Source"
    ])

    for record in records:

        writer.writerow([
            record["id"],
            record["detection_date"],
            record["detection_time"],
            record["people_count"],
            record["camera_source"]
        ])

    output.seek(0)

    return send_file(
        io.BytesIO(
            output.getvalue().encode("utf-8")
        ),
        mimetype="text/csv",
        as_attachment=True,
        download_name="human_detection_report.csv"
    )


# =========================================
# RUN APPLICATION
# =========================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )