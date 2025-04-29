import cv2
import os
from flask import Flask,request, render_template, session, redirect, url_for, flash
from datetime import date,datetime, timedelta
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import joblib
from flask_mysqldb import MySQL
import mysql.connector
import MySQLdb
import MySQLdb.cursors
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'xyzsdfg'

app.config['MYSQL_USER'] ='root'
app.config ['MYSQL_PASSWORD'] ='NayaPassword'
app.config['MYSQL_DB'] ='attendance_system'
app.config['MYSQL_HOST'] = '127.0.0.1'



mysql = MySQL(app)

# Define paths dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
FACES_DIR = os.path.join(STATIC_DIR, 'faces')
MODEL_PATH = os.path.join(STATIC_DIR, 'face_recognition_model.pkl')
BACKGROUND_IMAGE = os.path.join(BASE_DIR, 'background.png')
HAARCASCADE_PATH = os.path.join(BASE_DIR, 'haarcascade_frontalface_default.xml')

nimgs = 20
imgBackground = cv2.imread(BACKGROUND_IMAGE)
datetoday = date.today().strftime("%m_%d_%y")
datetoday2 = date.today().strftime("%d-%B-%Y")

face_detector = cv2.CascadeClassifier(HAARCASCADE_PATH)

# Ensure faces directory exists
if not os.path.isdir(FACES_DIR):
    os.makedirs(FACES_DIR)


def totalreg():
    # Fetch total number of students from the students table
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT COUNT(*) FROM students')
    total_students = cursor.fetchone()['COUNT(*)']  # Get the count from the query result
    return total_students

def extract_faces(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_points = face_detector.detectMultiScale(gray, 1.2, 5, minSize=(20, 20))
        return face_points


    except Exception as e:

        print(f"Error extracting faces: {e}")

        return []

def identify_face(facearray):
    model = joblib.load(MODEL_PATH)
    return model.predict(facearray)

def train_model():
    faces = []
    labels = []
    userlist = os.listdir(FACES_DIR)

    for user in userlist:
        user_folder = os.path.join(FACES_DIR, user)
        for imgname in os.listdir(user_folder):

            img_path = os.path.join(user_folder, imgname)
            img = cv2.imread(img_path)
            resized_face = cv2.resize(img, (50, 50))
            faces.append(resized_face.ravel())
            labels.append(user)

    faces = np.array(faces)
    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(faces, labels)
    joblib.dump(knn,MODEL_PATH)

def extract_attendance():
    current_date = date.today().strftime("%Y-%m-%d")
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT name, roll, attendance_time FROM attendance WHERE attendance_date = %s', (current_date,))
    records = cursor.fetchall()

    names = [record['name'] for record in records]
    rolls = [record['roll'] for record in records]
    times = [record['attendance_time'] for record in records]
    return names, rolls, times, len(records)

def send_email( username, current_time_str):
    # Fetch the email from the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT email FROM students WHERE name = %s', (username,))
    user = cursor.fetchone()

    if not user:
        print(f"Email not found for user {username}")
        return

    recipient_email = user['email']

    sender_email = "bhaskarsinghlodhi41@gmail.com"  # Replace with your email
    sender_password = "vfhknjykyxxvgxyu"  # Replace with your app-specific password


    # Email content
    subject = "Attendance Notification"
    body = f"""
    Dear {username},

    Your attendance has been successfully marked at {current_time_str}.

    Best regards,
    Attendance System
    """
    # Create the email message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        # Connect to the SMTP server
        with smtplib.SMTP("smtp.gmail.com", 587) as server:  # Using Gmail SMTP
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)  # Log in to the server
            server.sendmail(sender_email, recipient_email, message.as_string())  # Send the email
            print("Attendance email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")




def add_attendance(name):
    if '_' not in name:
        print(f"Error: Invalid name format '{name}'. Expected format 'name_roll'.")
        return

    name_split = name.split('_')
    if len(name_split) < 2:
        print(f"Error: Name '{name}' does not have a valid roll number after splitting.")
        return

    name = name_split[0]
    roll = name_split[1]
    current_time = datetime.now()
    current_time_only = current_time.time()  # Get only the time part
    current_time_str = current_time.strftime("%H:%M:%S")
    attendance_date = current_time.strftime("%Y-%m-%d")

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM attendance WHERE roll = %s AND attendance_date = %s ORDER BY attendance_time DESC LIMIT 1', (roll, attendance_date))
    existing_entry = cursor.fetchone()

    if existing_entry:
        try:
            # Parse the stored time directly since it's already in TIME format
            last_attendance_time = datetime.strptime(str(existing_entry['attendance_time']), "%H:%M:%S").time()
            # Compare using time difference
            current_datetime = datetime.combine(current_time.date(), current_time_only)
            last_datetime = datetime.combine(current_time.date(), last_attendance_time)

            # Calculate the time difference
            time_difference = current_datetime - last_datetime

            if time_difference < timedelta(minutes=1):
                print("Duplicate attendance detected. Skipping entry.")
                return
        except Exception as e:
            print(f"Error processing existing entry: {e}")
            return

    try:
        # Insert into the database using only the time and date values
        cursor.execute(
            'INSERT INTO attendance (name, roll, attendance_time, attendance_date) VALUES (%s, %s, %s, %s)',
            (name, roll, current_time_only, attendance_date)
        )
        mysql.connection.commit()
        print(f"Attendance added for {name} ({roll}) at {current_time_str}.")
    except Exception as e:
        print(f"Database insert error: {e}")
        return

    try:
        # Send email notification
        send_email(name, current_time_str)
    except Exception as e:
        print(f"Error sending email for {name}: {e}")


@app.route('/register', methods =['GET', 'POST'])
def register():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form :
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email, ))
        account = cursor.fetchone()
        if account:
            flash('Account already exists !')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash( 'Invalid email address !')
        elif not username or not password or not email:
            flash( 'Please fill out the form !')
        else:
            cursor.execute('INSERT INTO user (username, email, password) VALUES (%s, %s, %s)', (username, email, password))


            mysql.connection.commit()
            flash('You have successfully registered !')

            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/students', methods=['GET'])
def students():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM students')  # Fetch all user records from the `user` table
    students = cursor.fetchall()  # Fetch all rows from the query result
    return render_template('students.html', students=students)

@app.route('/view_records', methods=['GET', 'POST'])
def view_records():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch all dates for the dropdown
    cursor.execute('SELECT DISTINCT attendance_date FROM attendance')
    dates = cursor.fetchall()

    # Initialize records and selected_date
    records = []
    selected_date = None

    if request.method == 'POST':
        selected_date = request.form.get('date', '').strip()

        # Only query if a valid date is selected
        if selected_date:
            cursor.execute(
                'SELECT name, roll, attendance_time, attendance_date FROM attendance WHERE attendance_date = %s',
                (selected_date,))
            records = cursor.fetchall()
        else:
            flash("Please select a valid date.", "error")  # Optional: Add error message for empty date selection
        # Pass the records to the template, with formatted date
    for record in records:
            # Format attendance_time and attendance_date for display
            record['time'] = datetime.strptime(str(record['attendance_time']), '%H:%M:%S').strftime('%I:%M %p')
            record['date'] = datetime.strptime(str(record['attendance_date']), '%Y-%m-%d').strftime('%d-%B-%Y')

    return render_template('view_records.html', records=records, dates=dates, selected_date=selected_date)


@app.route('/home')
def home():
    names, rolls, times, l = extract_attendance()
    scanned_faces = [f'static/scanned_faces/{roll}.jpg' for roll in rolls]
    return render_template('home.html', names=names, rolls=rolls, times=times, l=l,scanned_faces=scanned_faces, totalreg=totalreg(), datetoday2=datetoday2)
@app.route('/logout')
def logout():
    session.clear()  # Clear session data
    return redirect(url_for('login'))  # Redirect to login page

def save_scanned_face(roll_no, face_image):
    # Save the face image with the roll number as the filename
    filepath = f'static/scanned_faces/{roll_no}.jpg'
    face_image.save(filepath)  # Assuming `face_image` is a PIL or OpenCV image object
    return filepath



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s AND password = %s', (email, password,))
        user = cursor.fetchone()
        if user:
            session['logged_in'] = True
            session['name'] = user['username']
            session['email'] = user['email']
            flash('Logged in successfully !')
            return render_template('home.html', totalreg=totalreg(), datetoday2=datetoday2)
        else:
            flash('Please enter correct email / password !')
            return render_template('index.html')
    return render_template('index.html')




def getallusers():
    userlist = os.listdir(FACES_DIR)
    names = []
    rolls = []
    l = len(userlist)

    for i in userlist:
        name, roll = i.split('_')
        names.append(name)
        rolls.append(roll)

    return userlist, names, rolls, l


@app.route('/start', methods=['GET'])
def start():
    # Load the attendance model
    if 'face_recognition_model.pkl' not in os.listdir(STATIC_DIR):
        return render_template('home.html', totalreg=totalreg(), datetoday2=datetoday2,
                               mess='There is no trained model in the static folder. Please add a new face to continue.')

    already_detected = set()  # Track detected users during the session
    cap = cv2.VideoCapture(0)
    ret = True
    start_time = datetime.now()  # Record the session start time
    os.makedirs('static/scanned_faces', exist_ok=True)

    scanned_faces = []  # Store file paths of scanned faces

    while ret:
        ret, frame = cap.read()

        if  ret:

             faces = extract_faces(frame)

             for (x, y, w, h) in faces:
                 face = cv2.resize(frame[y:y + h, x:x + w], (50, 50))
                 identified_person = identify_face(face.reshape(1, -1))[0]

                 if identified_person not in already_detected:
                     add_attendance(identified_person)
                     already_detected.add(identified_person)
                     roll = identified_person.split('_')[-1]  # Assuming roll number is part of the identifier
                     filepath = f'static/scanned_faces/{roll}.jpg'
                     cv2.imwrite(filepath, face)
                     scanned_faces.append(filepath)

                # Draw bounding box and label on the frame
                 cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 255), 2)
                 cv2.rectangle(frame, (x, y - 40), (x + w, y), (50, 50, 255), -1)
                 cv2.putText(frame, f'{identified_person}', (x, y - 15), cv2.FONT_HERSHEY_COMPLEX, 0.8, (255, 255, 255), 2)

                # Update the background image
             imgBackground[162:162 + 480, 55:55 + 640] = frame
             cv2.imshow('Attendance', imgBackground)

            # Check if session time exceeds 1 minute
             if (datetime.now() - start_time).seconds >= 60:
                 break

            # Break on pressing the spacebar
             if cv2.waitKey(1) == 32:
                 break

    cap.release()
    cv2.destroyAllWindows()

    # Render attendance results on the home page
    names, rolls, times, l = extract_attendance()



    return render_template('home.html', names=names, rolls=rolls, times=times, l=l,scanned_faces=scanned_faces,
                           totalreg=totalreg(), datetoday2=datetoday2)


@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        # Retrieve form data
        new_username = request.form['name']  # Name
        new_useremail = request.form['new_useremail']  # Email
        new_user_rollno = request.form['new_user_rollno']  # Roll number

        # Check for existing user with same roll number
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM students WHERE rollno = %s', (new_user_rollno,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('User with this Roll Number already exists!')
            return redirect(url_for('add'))
        else:
            # Insert new user details into the database
            cursor.execute('INSERT INTO students (name, email, rollno) VALUES (%s, %s, %s)',(new_username, new_useremail, new_user_rollno))
            mysql.connection.commit()

            # Save user face images locally
            user_image_folder = os.path.join(FACES_DIR, f'{new_username}_{new_user_rollno}')
            if not os.path.isdir(user_image_folder):
                os.makedirs(user_image_folder)

            # Capture face images using webcam
            i, j = 0, 0
            cap = cv2.VideoCapture(0)
             # Number of images to capture

            while True:
                ret, frame = cap.read()
                faces = extract_faces(frame)  # Assuming 'extract_faces' function exists

                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 20), 2)
                    cv2.putText(frame, f'Images Captured: {i}/{nimgs}', (30, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 20), 2, cv2.LINE_AA)
                    if j % 5 == 0:  # Save every 5th frame
                        name = f'{new_username}_{i}.jpg'
                        face_image = frame[y:y + h, x:x + w]
                        cv2.imwrite(os.path.join(user_image_folder, name), frame[y:y+h, x:x+w])
                        i += 1
                    j += 1

                # Exit condition: capture required number of images or press SPACE
                if j == nimgs * 5:  # SPACE key
                    break

                cv2.imshow('Adding New User', frame)
                if cv2.waitKey(1) == 32:
                    break

            cap.release()
            cv2.destroyAllWindows()

            # Train the face recognition model
            train_model()  # Assuming 'train_model' function exists

            flash(f'name {new_username} successfully added!')
            return redirect(url_for('home'))

    return render_template('home.html')  # Render 'home.html' template

@app.route('/delete_student/<roll>', methods=['POST'])
def delete_student(roll):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Delete the student record from the database
    cursor.execute('DELETE FROM students WHERE rollno = %s', (roll,))
    mysql.connection.commit()

    # Remove the student's face images from local storage
    user_image_folder = os.path.join(FACES_DIR, f'{roll}')
    # The student's folder path is based on their roll number
    if os.path.isdir(  user_image_folder):
        for folder in os.listdir(  user_image_folder):
            os.remove(os.path.join(  user_image_folder, folder))  # Delete each image file
        os.rmdir(  user_image_folder)  # Remove the folder

    flash(f'Student with roll number {roll} has been deleted successfully.')
    return redirect(url_for('students'))  # Redirect back to the students page



@app.route('/your_route')
def your_view():
    # Create a cursor to interact with the database
    cursor = mysql.connection.cursor()

    # Query the database to get the total number of students
    cursor.execute("SELECT COUNT(*) FROM students")  # Replace 'students' with your actual table name
    total_students = cursor.fetchone()[0]  # Fetch the result and get the count

    # Pass the count to the template
    return render_template('home.html', totalreg=total_students)

@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')



if __name__ == '__main__':
    app.run(debug=True)
