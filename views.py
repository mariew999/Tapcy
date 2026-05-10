from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import re
import sqlite3
import os
import requests
from functools import lru_cache

views = Blueprint('views', __name__)

# ============= CONFIGURATION =============
GOOGLE_MAPS_API_KEY = "YOUR_GOOGLE_MAPS_API_KEY"   # <-- Replace with your real key
RATE_PER_KM = 15                                   # ₱ per kilometer (adjust as needed)
DEFAULT_FARE = 50                                  # fallback if API fails

# ============= TIMEZONE =============
def get_local_time():
    utc_now = datetime.utcnow()
    ph_time = utc_now + timedelta(hours=8)
    return ph_time

# ============= DATABASE =============
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS passenger_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_phone TEXT NOT NULL,
            booking_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

active_riders = {}
active_drivers = {}

# ============= GOOGLE MAPS DISTANCE HELPER =============
@lru_cache(maxsize=256)
def get_distance_km(origin, destination):
    """Return distance in kilometers between two addresses using Google Maps API."""
    if not GOOGLE_MAPS_API_KEY or GOOGLE_MAPS_API_KEY == "YOUR_GOOGLE_MAPS_API_KEY":
        # No valid key – fallback to default fare
        return None
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin,
        "destinations": destination,
        "key": GOOGLE_MAPS_API_KEY,
        "units": "metric"
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data["status"] == "OK":
            element = data["rows"][0]["elements"][0]
            if element["status"] == "OK":
                distance_meters = element["distance"]["value"]
                return round(distance_meters / 1000.0, 1)  # km, 1 decimal
    except Exception as e:
        print(f"Distance API error: {e}")
    return None

# ============= HOME =============
@views.route("/")
def home():
    if 'passenger' in session:
        return redirect(url_for('views.passenger_dashboard'))
    if 'driver' in session:
        return redirect(url_for('views.driver_dashboard'))
    return render_template("index.html", active_tab='home')

# ============= PASSENGER =============
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
    passenger_data = db.execute("SELECT * FROM passengers WHERE phone = ?", (session['passenger']['phone'],)).fetchone()
    completed_count = db.execute("SELECT COUNT(*) as count FROM bookings WHERE passenger_phone = ? AND status = 'completed'",
                                 (session['passenger']['phone'],)).fetchone()
    bookings = db.execute("SELECT * FROM bookings WHERE passenger_phone = ? ORDER BY id DESC",
                         (session['passenger']['phone'],)).fetchall()
    available_drivers = db.execute("SELECT * FROM drivers WHERE status = 'available'").fetchall()
    passenger_notifications = db.execute(
        "SELECT * FROM passenger_notifications WHERE passenger_phone = ? AND is_read = 0 ORDER BY id DESC",
        (session['passenger']['phone'],)
    ).fetchall()
    db.close()
    active_riders_list = []
    for phone, rider in active_riders.items():
        active_riders_list.append({'name': rider['name'], 'phone': phone, 'login_time': rider['login_time']})
    passenger_info = {
        'name': session['passenger']['name'],
        'phone': session['passenger']['phone'],
        'email': session['passenger']['email'],
        'total_bookings': completed_count['count'] if completed_count else 0
    }
    return render_template("passenger_dashboard.html",
                           active_tab='passenger',
                           passenger=passenger_info,
                           bookings=bookings,
                           active_riders=active_riders_list,
                           active_riders_count=len(active_riders),
                           available_drivers_count=len(available_drivers),
                           passenger_notifications=passenger_notifications)

@views.route("/book_ride", methods=["GET", "POST"])
def book_ride():
    if 'passenger' not in session:
        flash("Please login first", "error")
        return redirect(url_for('views.passenger_login'))
    
    if request.method == "POST":
        pickup_barangay = request.form.get("pickup_barangay")
        dropoff_barangay = request.form.get("dropoff_barangay")
        pickup_details = request.form.get("pickup_details", "")
        dropoff_details = request.form.get("dropoff_details", "")
        passengers_count = int(request.form.get("passengers"))
        
        # Build full addresses for Google Maps
        origin = f"{pickup_barangay}, Cabagan, Isabela"
        destination = f"{dropoff_barangay}, Cabagan, Isabela"
        
        # Get real distance from API
        distance_km = get_distance_km(origin, destination)
        
        if distance_km is not None:
            base_fare = int(distance_km * RATE_PER_KM)
        else:
            base_fare = DEFAULT_FARE
            flash(f"Using default fare (₱{DEFAULT_FARE}) because distance could not be calculated.", "info")
        
        fare = base_fare * passengers_count
        
        full_pickup = pickup_barangay
        if pickup_details.strip():
            full_pickup = f"{pickup_barangay} - {pickup_details}"
        full_dropoff = dropoff_barangay
        if dropoff_details.strip():
            full_dropoff = f"{dropoff_barangay} - {dropoff_details}"
        
        db = get_db()
        cursor = db.execute('''INSERT INTO bookings (passenger_phone, passenger_name, pickup, dropoff, passengers, fare, status, time, date)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (session['passenger']['phone'], session['passenger']['name'], full_pickup, full_dropoff,
                            passengers_count, fare, 'pending', get_local_time().strftime("%H:%M"),
                            get_local_time().strftime("%Y-%m-%d")))
        booking_id = cursor.lastrowid
        available_drivers = db.execute("SELECT * FROM drivers WHERE status = 'available'").fetchall()
        for driver in available_drivers:
            db.execute('''INSERT INTO notifications (driver_email, booking_id, message, pickup, fare, time)
                          VALUES (?, ?, ?, ?, ?, ?)''',
                      (driver['email'], booking_id, f"New booking from {session['passenger']['name']}",
                       full_pickup, fare, get_local_time().strftime("%H:%M")))
        db.commit()
        db.close()
        
        flash(f"🎀 Booking #{booking_id} created! Fare: ₱{fare} (based on {distance_km} km). {len(available_drivers)} driver(s) notified.", "success")
        return redirect(url_for('views.passenger_dashboard'))
    
    # GET request – just render the form (no fare matrix needed now)
    return render_template("book_ride.html", passenger=session['passenger'], active_tab='passenger')

# ============= (rest of the routes: cancel_booking, passenger_logout, driver_login, driver_register, driver_dashboard, accept, complete, toggle, notify_arrival, mark_read, driver_logout, admin_dashboard) =============
# ⚠️ Keep all those routes exactly as they were in the previous complete `views.py`.
# To save space, I'm not repeating them here – but they must be present.
# You can copy the remaining routes from the previous `views.py` I gave you (the one before the fare matrix).
