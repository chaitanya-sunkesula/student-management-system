STUDENT MANAGEMENT SYSTEM

1. Open this folder in PyCharm or VS Code.
2. Open a terminal in this folder.
3. Install dependencies:
   pip install -r requirements.txt
4. Run:
   python app.py
5. Open:
   http://127.0.0.1:5000

Default demo login:
Email: admin@example.com
Password: 123

The SQLite database is created automatically as student_management.db.
Student and user data persists after restarting the Flask server.

Project structure:
app.py
requirements.txt
README.txt
templates/
    login.html
    register.html
    dashboard.html
    add_student.html
    students.html
    student_details.html
    edit_student.html
static/
    css/
        style.css
