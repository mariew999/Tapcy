from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import re
import sqlite3
import os

views = Blueprint('views', __name__)

# ============= HELPER FUNCTIONS =============
# TIMEZONE: Philippines UTC+8
def get_local_time():
    utc_now = datetime.utcnow()
    ph_time = utc_now + timedelta(hours=8)
    return ph_time

# DATABASE CONNECTION - handles Render vs local paths
def get_db():
    if os.path.exists('/opt/render/project/src/data'):
        db_path = '/opt/render/project/src/data/tapcy.db'
    else:
        db_path = os.path.join(os.path.dirname(__file__), 'tapcy.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# DATABASE INITIALIZATION - creates all tables
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # PASSENGERS TABLE: stores all passenger accounts
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
    
    # DRIVERS TABLE: stores all driver accounts
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
    
    # BOOKINGS TABLE: stores all ride bookings
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
    
    # NOTIFICATIONS TABLE: alerts for drivers
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

# ACTIVE SESSIONS TRACKING
active_riders = {}  # Currently logged in passengers
active_drivers = {}  # Currently online drivers

# ============= HOME PAGE =============
@views.route("/")
def home():
    # Redirect logged in users to their dashboard
    if 'passenger' in session:
        return redirect(url_for('views.passenger_dashboard'))
    if 'driver' in session:
        return redirect(url_for('views.driver_dashboard'))
    # Show homepage for guests
    return render_template("index.html")

# ============= PASSENGER SECTION =============
# PASSENGER LOGIN - authenticates existing passengers
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
            # Create session and add to active riders
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
            flash(f"🌸 Welcome back {passenger['name']}
