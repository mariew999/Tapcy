from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import re
import sqlite3
import os

views = Blueprint('views', __name__)

# ============= TIMEZONE SETUP (Philippines UTC+8) =============
def get_local_time():
    utc_now = datetime.utcnow()
    ph_time = utc_now + timedelta(hours=8)
    return ph_time

# ============= DATABASE SETUP =============
def get_db():
    if os.path.exists('/opt/render/project/src/data'):
        db_path = '/opt/render/project/src/data/tapcy.db'
    else:
        db_path = os.path.join(os.path.dirname(__file__), 'tapcy.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS passengers (
            phone TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            total_bookings INTEGER DEFAULT 0,
            registered_date TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drivers (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            tricycle TEXT NOT NULL,
            earnings INTEGER DEFAULT 0,
            status TEXT DEFAULT 'offline',
            total_rides INTEGER DEFAULT 0,
            registered_date TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_phone TEXT NOT NULL,
            passenger_name TEXT NOT NULL,
            pickup TEXT NOT NULL,
            dropoff TEXT NOT NULL,
            passengers INTEGER NOT NULL,
            fare INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            driver TEXT,
            time TEXT NOT NULL,
            date TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_email TEXT NOT NULL,
            booking_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            pickup TEXT,
            fare INTEGER,
            read INTEGER DEFAULT 0,
            time TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

active_riders = {}
active_drivers = {}

# ============= HOME PAGE =============
@views.route("/")
def home():
    if 'passenger' in session:
        return redirect(url_for('views.passenger_dashboard'))
    if 'driver' in session:
        return redirect(url_for('views.driver_dashboard'))
    return render_template("index.html", active_tab='home')

# ============= PASSENGER SECTION =============
@views.route("/passenger_login", methods=["GET", "POST"])
def passenger_login():
    if 'passenger' in session:
        return redirect(url_for('views.passenger_dashboard'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        db = get_db()
        passenger = db.execute("SELECT * FROM passengers WHERE email = ? AND password = ?", (email, password)).fetchone()
        db.close()

        if passenger:
            session['passenger'] = {
                'phone': passenger['phone'],
                'name': passenger['name'],
                'email': email,
                'logged_in': True,
                'login_time': get_local_time().strftime("%Y-%m-%d %H:%M")
            }
            active_riders[passenger['phone']] = {
                'name': passenger['name'],
                'email': email,
                'login_time': get_local_time().strftime("%H:%M"),
                'status': 'active'
            }
            flash(f"🌸 Welcome back {passenger['name']}!", "success")
            return redirect(url_for('views.passenger_dashboard'))
        else:
            flash("Invalid email or password", "error")

    return render_template("passenger_login.html", active_tab='passenger')

@views.route("/passenger_register", methods=["POST"])
def passenger_register():
    name = request.form.get("name")
    phone = request.form.get("phone")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if not name or not phone or not email or not password or not confirm_password:
        flash("All fields are required", "error")
        return redirect(url_for('views.passenger_login'))

    if not re.match(r'^\d{11}$', phone):
        flash("Phone number must be exactly 11 digits", "error")
        return redirect(url_for('views.passenger_login'))

    if '@' not in email:
        flash("Email must contain @ symbol", "error")
        return redirect(url_for('views.passenger_login'))

    if len(password) < 8:
        flash("Password must be at least 8 characters", "error")
        return redirect(url_for('views.passenger_login'))

    if password != confirm_password:
        flash("Passwords do not match", "error")
        return redirect(url_for('views.passenger_login'))

    db = get_db()
    
    existing = db.execute("SELECT * FROM passengers WHERE phone = ?", (phone,)).fetchone()
    if existing:
        flash("Phone number already registered", "error")
        db.close()
        return redirect(url_for('views.passenger_login'))
    
    existing = db.execute("SELECT * FROM passengers WHERE email = ?", (email,)).fetchone()
    if existing:
        flash("Email already registered", "error")
        db.close()
        return redirect(url_for('views.passenger_login'))
    
    db.execute('''INSERT INTO passengers (phone, name, email, password, total_bookings, registered_date)
                  VALUES (?, ?, ?, ?, ?, ?)''', 
               (phone, name, email, password, 0, get_local_time().strftime("%Y-%m-%d")))
    db.commit()
    db.close()

    flash("Registration successful! Please login.", "success")
    return redirect(url_for('views.passenger_login'))

@views.route("/passenger_dashboard")
def passenger_dashboard():
    if 'passenger' not in session:
        flash("Please login first", "error")
        return redirect(url_for('views.passenger_login'))

    db = get_db()
    bookings = db.execute("SELECT * FROM bookings WHERE passenger_phone = ? ORDER BY id DESC", 
                         (session['passenger']['phone'],)).fetchall()
    available_drivers = db.execute("SELECT * FROM drivers WHERE status = 'available'").fetchall()
    db.close()

    active_riders_list = []
    for phone, rider in active_riders.items():
        active_riders_list.append({
            'name': rider['name'],
            'phone': phone,
            'login_time': rider['login_time']
        })

    return render_template("passenger_dashboard.html",
                           active_tab='passenger',
                           passenger=session['passenger'],
                           bookings=bookings,
                           active_riders=active_riders_list,
                           active_riders_count=len(active_riders),
                           available_drivers_count=len(available_drivers))

@views.route("/book_ride", methods=["GET", "POST"])
def book_ride():
    if 'passenger' not in session:
        flash("Please login first", "error")
        return redirect(url_for('views.passenger_login'))

    if request.method == "POST":
        pickup = request.form.get("pickup")
        dropoff = request.form.get("dropoff")
        passengers_count = int(request.form.get("passengers"))
        fare = passengers_count * 40

        db = get_db()
        
        cursor = db.execute('''INSERT INTO bookings (passenger_phone, passenger_name, pickup, dropoff, passengers, fare, status, time, date)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (session['passenger']['phone'], session['passenger']['name'], pickup, dropoff, 
                            passengers_count, fare, 'pending', get_local_time().strftime("%H:%M"), 
                            get_local_time().strftime("%Y-%m-%d")))
        booking_id = cursor.lastrowid
        
        db.execute("UPDATE passengers SET total_bookings = total_bookings + 1 WHERE phone = ?", 
                  (session['passenger']['phone'],))
        
        available_drivers = db.execute("SELECT * FROM drivers WHERE status = 'available'").fetchall()
        
        for driver in available_drivers:
            db.execute('''INSERT INTO notifications (driver_email, booking_id, message, pickup, fare, time)
                          VALUES (?, ?, ?, ?, ?, ?)''',
                      (driver['email'], booking_id, f"New booking from {session['passenger']['name']}", 
                       pickup, fare, get_local_time().strftime("%H:%M")))
        
        db.commit()
        db.close()

        flash(f"🎀 Booking #{booking_id} created! Fare: ₱{fare}. {len(available_drivers)} driver(s) notified.", "success")
        return redirect(url_for('views.passenger_dashboard'))

    return render_template("book_ride.html", passenger=session['passenger'], active_tab='passenger')

@views.route("/cancel_booking/<int:booking_id>")
def cancel_booking(booking_id):
    if 'passenger' not in session:
        return redirect(url_for('views.passenger_login'))

    db = get_db()
    db.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ? AND passenger_phone = ?",
              (booking_id, session['passenger']['phone']))
    db.commit()
    db.close()
    
    flash("💔 Booking cancelled", "info")
    return redirect(url_for('views.passenger_dashboard'))

@views.route("/passenger_logout")
def passenger_logout():
    if 'passenger' in session:
        active_riders.pop(session['passenger']['phone'], None)
        flash(f"🌸 Goodbye {session['passenger']['name']}!", "success")
    session.pop('passenger', None)
    return redirect(url_for('views.passenger_login'))

# ============= DRIVER SECTION =============
@views.route("/driver_login", methods=["GET", "POST"])
def driver_login():
    if 'driver' in session:
        return redirect(url_for('views.driver_dashboard'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        db = get_db()
        driver = db.execute("SELECT * FROM drivers WHERE email = ? AND password = ?", (email, password)).fetchone()
        db.close()

        if driver:
            session['driver'] = {'email': driver['email'], 'name': driver['name']}
            active_drivers[email] = {
                'name': driver['name'],
                'login_time': get_local_time().strftime("%H:%M"),
                'status': driver['status']
            }
            flash(f"🚗 Welcome {driver['name']}!", "success")
            return redirect(url_for('views.driver_dashboard'))
        else:
            flash("Invalid email or password", "error")

    return render_template("driver_login.html", active_tab='driver')

@views.route("/driver_register", methods=["POST"])
def driver_register():
    name = request.form.get("name")
    phone = request.form.get("phone")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm = request.form.get("confirm")
    tricycle = request.form.get("tricycle")
    
    # DEBUG: Print to see what's happening
    import re as regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = bool(regex.match(email_pattern, str(email)))
    
    print(f"=== EMAIL DEBUG ===")
    print(f"Email entered: '{email}'")
    print(f"Email length: {len(email) if email else 0}")
    print(f"Regex match result: {is_valid}")
    print(f"==================")
    
    if not name or not phone or not email or not password or not confirm or not tricycle:
        flash("All fields are required", "error")
        return redirect(url_for('views.driver_login'))

    if not re.match(r'^\d{11}$', phone):
        flash("Phone number must be exactly 11 digits", "error")
        return redirect(url_for('views.driver_login'))

    # Email validation
    if not is_valid:
        flash(f"Please enter a valid email address (e.g., name@example.com). You entered: '{email}'", "error")
        return redirect(url_for('views.driver_login'))

    if len(password) < 8:
        flash("Password must be at least 8 characters", "error")
        return redirect(url_for('views.driver_login'))

    if password != confirm:
        flash("Passwords do not match", "error")
        return redirect(url_for('views.driver_login'))

    db = get_db()
    
    existing = db.execute("SELECT * FROM drivers WHERE email = ?", (email,)).fetchone()
    if existing:
        flash("Email already registered", "error")
        db.close()
        return redirect(url_for('views.driver_login'))
    
    db.execute('''INSERT INTO drivers (email, name, phone, password, tricycle, status, registered_date)
                  VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (email, name, phone, password, tricycle, 'offline', get_local_time().strftime("%Y-%m-%d")))
    db.commit()
    db.close()

    flash("Registration successful! Please login.", "success")
    return redirect(url_for('views.driver_login'))
    
@views.route("/driver_dashboard")
def driver_dashboard():
    if 'driver' not in session:
        flash("Please login first", "error")
        return redirect(url_for('views.driver_login'))

    db = get_db()
    
    driver = db.execute("SELECT * FROM drivers WHERE email = ?", (session['driver']['email'],)).fetchone()
    pending_bookings = db.execute("SELECT * FROM bookings WHERE status = 'pending' ORDER BY id DESC").fetchall()
    my_accepted = db.execute("SELECT * FROM bookings WHERE driver = ? AND status = 'accepted'", 
                            (session['driver']['name'],)).fetchall()
    my_completed = db.execute("SELECT * FROM bookings WHERE driver = ? AND status = 'completed'",
                             (session['driver']['name'],)).fetchall()
    notifications = db.execute("SELECT * FROM notifications WHERE driver_email = ? AND read = 0",
                              (session['driver']['email'],)).fetchall()
    
    db.close()

    return render_template("driver_dashboard.html",
                           active_tab='driver',
                           driver=session['driver'],
                           driver_info=driver,
                           pending_bookings=pending_bookings,
                           my_accepted=my_accepted,
                           my_completed=my_completed,
                           notifications=notifications,
                           active_riders_count=len(active_riders),
                           online_drivers_count=len(active_drivers))

@views.route("/accept_booking/<int:booking_id>")
def accept_booking(booking_id):
    if 'driver' not in session:
        return redirect(url_for('views.driver_login'))

    db = get_db()
    db.execute("UPDATE bookings SET status = 'accepted', driver = ? WHERE id = ? AND status = 'pending'",
              (session['driver']['name'], booking_id))
    db.execute("UPDATE drivers SET total_rides = total_rides + 1 WHERE email = ?",
              (session['driver']['email'],))
    db.commit()
    db.close()
    
    flash(f"✅ Booking #{booking_id} accepted! Pick up passenger.", "success")
    return redirect(url_for('views.driver_dashboard'))

@views.route("/complete_ride/<int:booking_id>")
def complete_ride(booking_id):
    if 'driver' not in session:
        return redirect(url_for('views.driver_login'))

    db = get_db()
    booking = db.execute("SELECT fare FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    
    if booking:
        db.execute("UPDATE bookings SET status = 'completed' WHERE id = ?", (booking_id,))
        db.execute("UPDATE drivers SET earnings = earnings + ? WHERE email = ?",
                  (booking['fare'], session['driver']['email']))
        db.commit()
        flash(f"🎉 Ride completed! Earned ₱{booking['fare']}", "success")
    
    db.close()
    return redirect(url_for('views.driver_dashboard'))

@views.route("/toggle_driver_status")
def toggle_driver_status():
    if 'driver' not in session:
        return redirect(url_for('views.driver_login'))

    db = get_db()
    driver = db.execute("SELECT status FROM drivers WHERE email = ?", (session['driver']['email'],)).fetchone()
    
    if driver['status'] == 'available':
        db.execute("UPDATE drivers SET status = 'offline' WHERE email = ?", (session['driver']['email'],))
        active_drivers.pop(session['driver']['email'], None)
        flash("🟡 Status: OFFLINE", "info")
    else:
        db.execute("UPDATE drivers SET status = 'available' WHERE email = ?", (session['driver']['email'],))
        active_drivers[session['driver']['email']] = {
            'name': session['driver']['name'],
            'login_time': get_local_time().strftime("%H:%M"),
            'status': 'online'
        }
        flash("🟢 Status: ONLINE - You will receive bookings", "success")
    
    db.commit()
    db.close()
    return redirect(url_for('views.driver_dashboard'))

@views.route("/driver_logout")
def driver_logout():
    if 'driver' in session:
        active_drivers.pop(session['driver']['email'], None)
        db = get_db()
        db.execute("UPDATE drivers SET status = 'offline' WHERE email = ?", (session['driver']['email'],))
        db.commit()
        db.close()
    session.pop('driver', None)
    flash("🚗 Logged out. Drive safe!", "success")
    return redirect(url_for('views.passenger_login'))

# ============= ADMIN SECTION =============
@views.route("/admin_dashboard")
def admin_dashboard():
    db = get_db()
    
    bookings = db.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()
    passengers = db.execute("SELECT * FROM passengers").fetchall()
    drivers = db.execute("SELECT * FROM drivers").fetchall()
    
    total_passengers = len(passengers)
    total_drivers = len(drivers)
    total_bookings = len(bookings)
    pending = db.execute("SELECT COUNT(*) as count FROM bookings WHERE status = 'pending'").fetchone()
    pending_bookings = pending['count'] if pending else 0
    
    db.close()
    
    return render_template("admin_dashboard.html",
                           active_tab='admin',
                           bookings=[dict(row) for row in bookings],
                           passengers=[dict(row) for row in passengers],
                           drivers=[dict(row) for row in drivers],
                           total_passengers=total_passengers,
                           total_drivers=total_drivers,
                           total_bookings=total_bookings,
                           pending_bookings=pending_bookings,
                           active_riders=active_riders,
                           active_drivers=active_drivers)
