from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "student_management.db"

app = Flask(__name__)
app.secret_key = "student-management-secret-key-change-this"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            department TEXT NOT NULL,
            year TEXT NOT NULL,
            marks REAL NOT NULL CHECK(marks >= 0 AND marks <= 100),
            attendance REAL NOT NULL CHECK(attendance >= 0 AND attendance <= 100)
        )
    """)
    # Keep the original demo login available.
    admin = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("admin@example.com",)
    ).fetchone()
    if admin is None:
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            ("Admin", "admin@example.com", generate_password_hash("123"))
        )
    conn.commit()
    conn.close()


def login_required():
    return "user_id" in session


@app.route("/")
def home():
    if login_required():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Login successful!")
            return redirect(url_for("dashboard"))

        flash("Invalid credentials")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("register"))

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password))
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("User already exists!")
            return redirect(url_for("register"))
        conn.close()

        flash("Registration successful! Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()
    total_students = conn.execute(
        "SELECT COUNT(*) AS count FROM students"
    ).fetchone()["count"]
    cse_students = conn.execute(
        "SELECT COUNT(*) AS count FROM students WHERE department = 'CSE'"
    ).fetchone()["count"]
    average_marks = conn.execute(
        "SELECT COALESCE(ROUND(AVG(marks), 2), 0) AS average FROM students"
    ).fetchone()["average"]
    low_attendance = conn.execute(
        "SELECT COUNT(*) AS count FROM students WHERE attendance < 75"
    ).fetchone()["count"]
    conn.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        cse_students=cse_students,
        average_marks=average_marks,
        low_attendance=low_attendance
    )


@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    if not login_required():
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll_number = request.form.get("roll_number", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        department = request.form.get("department", "").strip()
        year = request.form.get("year", "").strip()

        try:
            marks = float(request.form.get("marks", ""))
            attendance = float(request.form.get("attendance", ""))
        except ValueError:
            flash("Marks and attendance must be valid numbers.")
            return redirect(url_for("add_student"))

        if not name or not roll_number or not email or not phone or not department or not year:
            flash("Please fill all fields.")
            return redirect(url_for("add_student"))

        if not 0 <= marks <= 100 or not 0 <= attendance <= 100:
            flash("Marks and attendance must be between 0 and 100.")
            return redirect(url_for("add_student"))

        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO students
                (name, roll_number, email, phone, department, year, marks, attendance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, roll_number, email, phone, department, year, marks, attendance))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("Roll number already exists!")
            return redirect(url_for("add_student"))
        conn.close()

        flash("Student added successfully!")
        return redirect(url_for("students_list"))

    return render_template("add_student.html")


@app.route("/students")
def students_list():
    if not login_required():
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    department = request.args.get("department", "").strip()
    year = request.args.get("year", "").strip()

    query = "SELECT * FROM students WHERE 1=1"
    params = []

    if search:
        query += " AND (LOWER(name) LIKE ? OR LOWER(email) LIKE ? OR CAST(id AS TEXT) LIKE ?)"
        term = f"%{search.lower()}%"
        params.extend([term, term, term])

    if department:
        query += " AND department = ?"
        params.append(department)

    year_map = {"1": "1st Year", "2": "2nd Year", "3": "3rd Year", "4": "4th Year"}
    if year in year_map:
        query += " AND year = ?"
        params.append(year_map[year])

    query += " ORDER BY id ASC"

    conn = get_db()
    students = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "students.html",
        students=students,
        department=department,
        year=year,
        search=search
    )


@app.route("/student/<int:id>")
def student_details(id):
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE id = ?", (id,)
    ).fetchone()
    conn.close()

    if student is None:
        flash("Student not found")
        return redirect(url_for("students_list"))

    return render_template("student_details.html", student=student)


@app.route("/edit_student/<int:id>", methods=["GET", "POST"])
def edit_student(id):
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE id = ?", (id,)
    ).fetchone()

    if student is None:
        conn.close()
        flash("Student not found")
        return redirect(url_for("students_list"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        roll_number = request.form.get("roll_number", "").strip()
        phone = request.form.get("phone", "").strip()
        department = request.form.get("department", "").strip()
        year = request.form.get("year", "").strip()

        try:
            marks = float(request.form.get("marks", ""))
            attendance = float(request.form.get("attendance", ""))
        except ValueError:
            conn.close()
            flash("Marks and attendance must be valid numbers.")
            return redirect(url_for("edit_student", id=id))

        if not 0 <= marks <= 100 or not 0 <= attendance <= 100:
            conn.close()
            flash("Marks and attendance must be between 0 and 100.")
            return redirect(url_for("edit_student", id=id))

        try:
            conn.execute("""
                UPDATE students
                SET name=?, email=?, roll_number=?, phone=?,
                    department=?, year=?, marks=?, attendance=?
                WHERE id=?
            """, (name, email, roll_number, phone, department, year,
                  marks, attendance, id))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("Roll number already exists!")
            return redirect(url_for("edit_student", id=id))

        conn.close()
        flash("Student updated successfully!")
        return redirect(url_for("student_details", id=id))

    conn.close()
    return render_template("edit_student.html", student=student)


@app.route("/delete_student/<int:id>")
def delete_student(id):
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()
    conn.execute("DELETE FROM students WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Student deleted successfully!")
    return redirect(url_for("students_list"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!")
    return redirect(url_for("login"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
