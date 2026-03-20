from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import re

views = Blueprint('views', __name__)

# Databases
passengers_db = {}
drivers_db = {}
bookings_db = []
active_riders = {}  # Track currently logged-in riders (auto-saved)
active_drivers = {}  # Track currently logged-in drivers


# ============= HOME =============
@views.route("/")
def home():
    # Check if rider is already logged in (auto-login)
    if 'passenger' in session:
        return redirect(url_for('views.passenger_dashboard'))
    return redirect(url_for('views.kiosk'))


@views.route("/kiosk")
def kiosk():
    # Auto-login check - if already logged in, go to dashboard
    if 'passenger' in session:
        flash("🌸 You are already logged in!", "info")
        return redirect(url_for('views.passenger_dashboard'))
    return render_template("kiosk.html", active_tab='kiosk')


# ============= PASSENGER SECTION =============
@views.route("/passenger_login", methods=["GET", "POST"])
def passenger_login():
    # If already logged in, redirect to dashboard
    if 'passenger' in session:
        return redirect(url_for('views.passenger_dashboard'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        found = False
        for phone, passenger in passengers_db.items():
            if passenger.get('email') == email and passenger.get('password') == password:
                session['passenger'] = {
                    'phone': phone,
                    'name': passenger['name'],
                    'email': email,
                    'logged_in': True,
                    'login_time': datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                # Track active rider
                active_riders[phone] = {
                    'name': passenger['name'],
                    'email': email,
                    'login_time': datetime.now().strftime("%H:%M"),
                    'status': 'active'
                }
                flash(f"🌸 Welcome back {passenger['name']}! You are now logged in.", "success")
                found = True
                return redirect(url_for('views.passenger_dashboard'))

        if not found:
            flash("Invalid email or password", "error")

    return render_template("passenger_login.html", active_tab='kiosk')


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

    if phone in passengers_db:
        flash("Phone number already registered", "error")
        return redirect(url_for('views.passenger_login'))

    for p in passengers_db.values():
        if p.get('email') == email:
            flash("Email already registered", "error")
            return redirect(url_for('views.passenger_login'))

    passengers_db[phone] = {
        'name': name,
        'phone': phone,
        'email': email,
        'password': password,
        'total_bookings': 0,
        'registered_date': datetime.now().strftime("%Y-%m-%d")
    }

    flash("Registration successful! Please login.", "success")
    return redirect(url_for('views.passenger_login'))


@views.route("/passenger_dashboard")
def passenger_dashboard():
    if 'passenger' not in session:
        flash("Please login first", "error")
        return redirect(url_for('views.passenger_login'))

    my_bookings = []
    for b in bookings_db:
        if b.get('passenger_phone') == session['passenger']['phone']:
            my_bookings.append(b)

    # Get all active riders (auto-saved logged in riders)
    active_riders_list = []
    for phone, rider in active_riders.items():
        active_riders_list.append({
            'name': rider['name'],
            'phone': phone,
            'login_time': rider['login_time']
        })

    # Get available drivers
    available_drivers = [d for d in drivers_db.values() if d.get('status') == 'available']

    return render_template("passenger_dashboard.html",
                           active_tab='kiosk',
                           passenger=session['passenger'],
                           bookings=my_bookings,
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

        booking = {
            'id': len(bookings_db) + 1,
            'passenger_name': session['passenger']['name'],
            'passenger_phone': session['passenger']['phone'],
            'pickup': pickup,
            'dropoff': dropoff,
            'passengers': passengers_count,
            'fare': fare,
            'status': 'pending',
            'driver': None,
            'time': datetime.now().strftime("%H:%M"),
            'date': datetime.now().strftime("%Y-%m-%d")
        }
        bookings_db.append(booking)

        # Update passenger total bookings
        passengers_db[session['passenger']['phone']]['total_bookings'] += 1

        # Count available drivers
        available_drivers = [d for d in drivers_db.values() if d.get('status') == 'available']

        # Send notification to all available drivers (auto-notify)
        for email, driver in drivers_db.items():
            if driver.get('status') == 'available':
                if 'notifications' not in driver:
                    driver['notifications'] = []
                driver['notifications'].append({
                    'id': len(driver.get('notifications', [])) + 1,
                    'booking_id': booking['id'],
                    'message': f"New booking from {session['passenger']['name']}",
                    'pickup': pickup,
                    'fare': fare,
                    'read': False,
                    'time': datetime.now().strftime("%H:%M")
                })

        flash(f"🎀 Booking #{booking['id']} created! Fare: ₱{fare}. {len(available_drivers)} driver(s) notified.",
              "success")
        return redirect(url_for('views.passenger_dashboard'))

    return render_template("book_ride.html",
                           active_tab='kiosk',
                           passenger=session['passenger'])


@views.route("/cancel_booking/<int:booking_id>")
def cancel_booking(booking_id):
    if 'passenger' not in session:
        return redirect(url_for('views.passenger_login'))

    for b in bookings_db:
        if b['id'] == booking_id:
            b['status'] = 'cancelled'
            flash("💔 Booking cancelled", "info")
            break

    return redirect(url_for('views.passenger_dashboard'))


@views.route("/passenger_logout")
def passenger_logout():
    if 'passenger' in session:
        # Remove from active riders
        active_riders.pop(session['passenger']['phone'], None)
        flash(f"🌸 Goodbye {session['passenger']['name']}! You have been logged out.", "success")
    session.pop('passenger', None)
    return redirect(url_for('views.kiosk'))


# ============= DRIVER SECTION =============
@views.route("/driver_portal")
def driver_portal():
    # Auto-login check for driver
    if 'driver' in session:
        return redirect(url_for('views.driver_dashboard'))
    return render_template("driver_portal.html", active_tab='driver')


@views.route("/driver_login", methods=["GET", "POST"])
def driver_login():
    if 'driver' in session:
        return redirect(url_for('views.driver_dashboard'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email in drivers_db and drivers_db[email]['password'] == password:
            session['driver'] = {'email': email, 'name': drivers_db[email]['name']}
            # Track active driver
            active_drivers[email] = {
                'name': drivers_db[email]['name'],
                'login_time': datetime.now().strftime("%H:%M"),
                'status': drivers_db[email].get('status', 'online')
            }
            flash(f"🚗 Welcome {drivers_db[email]['name']}! You are now online.", "success")
            return redirect(url_for('views.driver_dashboard'))
        else:
            flash("Invalid email or password", "error")

    return render_template("driver_login.html", active_tab='driver')


@views.route("/driver_register", methods=["GET", "POST"])
def driver_register():
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        tricycle = request.form.get("tricycle")

        if not name or not phone or not email or not password or not confirm or not tricycle:
            flash("All fields are required", "error")
            return render_template("driver_register.html", active_tab='driver')

        if not re.match(r'^\d{11}$', phone):
            flash("Phone number must be exactly 11 digits", "error")
            return render_template("driver_register.html", active_tab='driver')

        if '@' not in email:
            flash("Email must contain @ symbol", "error")
            return render_template("driver_register.html", active_tab='driver')

        if email in drivers_db:
            flash("Email already registered", "error")
            return render_template("driver_register.html", active_tab='driver')

        if len(password) < 8:
            flash("Password must be at least 8 characters", "error")
            return render_template("driver_register.html", active_tab='driver')

        if password != confirm:
            flash("Passwords do not match", "error")
            return render_template("driver_register.html", active_tab='driver')

        drivers_db[email] = {
            'name': name,
            'phone': phone,
            'email': email,
            'password': password,
            'tricycle': tricycle,
            'earnings': 0,
            'status': 'offline',
            'total_rides': 0,
            'registered_date': datetime.now().strftime("%Y-%m-%d"),
            'notifications': []
        }

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('views.driver_login'))

    return render_template("driver_register.html", active_tab='driver')


@views.route("/driver_dashboard")
def driver_dashboard():
    if 'driver' not in session:
        flash("Please login first", "error")
        return redirect(url_for('views.driver_login'))

    pending_bookings = [b for b in bookings_db if b['status'] == 'pending']
    my_accepted = [b for b in bookings_db if b.get('driver') == session['driver']['name'] and b['status'] == 'accepted']
    my_completed = [b for b in bookings_db if
                    b.get('driver') == session['driver']['name'] and b['status'] == 'completed']

    driver = drivers_db.get(session['driver']['email'], {})

    # Get active riders count
    active_riders_count = len(active_riders)
    online_drivers_count = len(active_drivers)

    return render_template("driver_dashboard.html",
                           active_tab='driver',
                           driver=session['driver'],
                           driver_info=driver,
                           pending_bookings=pending_bookings,
                           my_accepted=my_accepted,
                           my_completed=my_completed,
                           active_riders_count=active_riders_count,
                           online_drivers_count=online_drivers_count)


@views.route("/accept_booking/<int:booking_id>")
def accept_booking(booking_id):
    if 'driver' not in session:
        return redirect(url_for('views.driver_login'))

    for b in bookings_db:
        if b['id'] == booking_id and b['status'] == 'pending':
            b['status'] = 'accepted'
            b['driver'] = session['driver']['name']
            drivers_db[session['driver']['email']]['total_rides'] += 1
            flash(f"✅ Booking #{booking_id} accepted! Pick up passenger.", "success")
            break

    return redirect(url_for('views.driver_dashboard'))


@views.route("/complete_ride/<int:booking_id>")
def complete_ride(booking_id):
    if 'driver' not in session:
        return redirect(url_for('views.driver_login'))

    for b in bookings_db:
        if b['id'] == booking_id and b.get('driver') == session['driver']['name']:
            b['status'] = 'completed'
            drivers_db[session['driver']['email']]['earnings'] += b['fare']
            flash(f"🎉 Ride completed! Earned ₱{b['fare']}", "success")
            break

    return redirect(url_for('views.driver_dashboard'))


@views.route("/toggle_driver_status")
def toggle_driver_status():
    if 'driver' not in session:
        return redirect(url_for('views.driver_login'))

    driver = drivers_db[session['driver']['email']]
    if driver['status'] == 'available':
        driver['status'] = 'offline'
        active_drivers.pop(session['driver']['email'], None)
        flash("🟡 Status: OFFLINE", "info")
    else:
        driver['status'] = 'available'
        active_drivers[session['driver']['email']] = {
            'name': driver['name'],
            'login_time': datetime.now().strftime("%H:%M"),
            'status': 'online'
        }
        flash("🟢 Status: ONLINE - You will receive bookings", "success")

    return redirect(url_for('views.driver_dashboard'))


@views.route("/driver_logout")
def driver_logout():
    if 'driver' in session:
        active_drivers.pop(session['driver']['email'], None)
        if session['driver']['email'] in drivers_db:
            drivers_db[session['driver']['email']]['status'] = 'offline'
    session.pop('driver', None)
    flash("🚗 Logged out. Drive safe!", "success")
    return redirect(url_for('views.kiosk'))


# ============= ADMIN SECTION =============
@views.route("/admin_dashboard")
def admin_dashboard():
    return render_template("admin_dashboard.html",
                           active_tab='admin',
                           bookings=bookings_db,
                           passengers=passengers_db,
                           drivers=drivers_db,
                           active_riders=active_riders,
                           active_drivers=active_drivers)