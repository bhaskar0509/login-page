# 🧠 Face Recognition-Based Attendance System

This is a Flask-based web application that uses facial recognition to automate attendance marking. It detects faces via webcam, matches them against stored data, logs attendance into a MySQL database, and sends email notifications.

---

## 📌 Features

- 🎥 Real-time face detection & recognition
- 📅 Automatic attendance logging
- 🧑‍🎓 Student registration & management
- 🧠 Face model training with KNN
- 📊 View attendance by date or student
- 📧 Email notification on attendance marking
- 🔐 Secure login & authentication system

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/bhaskar0509/login-page.git
cd login-page
2️⃣ Create Virtual Environment (optional but recommended)


python -m venv venv
venv\Scripts\activate  # On Windows
# OR
source venv/bin/activate  # On macOS/Linux
3️⃣ Install Dependencies

pip install -r requirements.txt
4️⃣ Configure MySQL Database
Open MySQL and create a new database:


CREATE DATABASE attendance_system;
Import the tables or create manually (students, attendance, user, etc.).

Update your config.py file with:


DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'yourpassword'
DB_NAME = 'attendance_system'
5️⃣ Configure Email (SMTP)
In your config or mail settings, add:


EMAIL_ADDRESS = 'your-email@gmail.com'
EMAIL_PASSWORD = 'your-app-password'  # Use Gmail App Password
Enable "Less secure apps" or use App Passwords if 2FA is on.

▶️ Run the App


python app.py
Now open your browser and visit:
🔗 http://localhost:5000/

📦 Dependencies
These are in requirements.txt. Main libraries:

Flask

OpenCV (opencv-python)

face_recognition

numpy

mysql-connector-python

flask-mail

Install them all:


pip install -r requirements.txt

📈 Future Improvements
Attendance graphs and analytics

Admin & teacher roles

Mobile responsive UI

Export attendance to CSV/PDF


