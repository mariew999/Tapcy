{% extends "base.html" %}

{% block content %}
<div class="booking-container">
    <div class="booking-card">
        <div class="booking-header">
            <div class="emoji-large">🚕✨</div>
            <h1>Book Your Ride</h1>
            <p>Hi <strong>{{ passenger.name }}</strong>! Where to today?</p>
        </div>

        <form method="POST" action="{{ url_for('views.book_ride') }}">
            <div class="form-group">
                <label class="form-label">📍 Pick-up Barangay</label>
                <select name="pickup_barangay" class="form-select" required>
                    <option value="">-- Select Pickup Barangay --</option>
                    <option value="Anao">Anao</option>
                    <option value="Angancasilian">Angancasilian</option>
                    <option value="Balasig">Balasig</option>
                    <option value="Cansan">Cansan</option>
                    <option value="Casibarag Sur">Casibarag Sur</option>
                    <option value="Casibarag Norte">Casibarag Norte</option>
                    <option value="Catabayungan">Catabayungan</option>
                    <option value="Centro">Centro</option>
                    <option value="Cubag">Cubag</option>
                    <option value="Garita">Garita</option>
                    <option value="Ngarag">Ngarag</option>
                    <option value="Magassi">Magassi</option>
                    <option value="Luquilu">Luquilu</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">📍 Pickup Specifics (Optional)</label>
                <input type="text" name="pickup_details" class="form-input" placeholder="e.g., Purok 6, near church">
                <small class="input-hint">Helps driver find you faster.</small>
            </div>
            <div class="form-group">
                <label class="form-label">🏁 Drop-off Barangay</label>
                <select name="dropoff_barangay" class="form-select" required>
                    <option value="">-- Select Drop-off Barangay --</option>
                    <option value="Anao">Anao</option>
                    <option value="Angancasilian">Angancasilian</option>
                    <option value="Balasig">Balasig</option>
                    <option value="Cansan">Cansan</option>
                    <option value="Casibarag Sur">Casibarag Sur</option>
                    <option value="Casibarag Norte">Casibarag Norte</option>
                    <option value="Catabayungan">Catabayungan</option>
                    <option value="Centro">Centro</option>
                    <option value="Cubag">Cubag</option>
                    <option value="Garita">Garita</option>
                    <option value="Ngarag">Ngarag</option>
                    <option value="Magassi">Magassi</option>
                    <option value="Luquilu">Luquilu</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">🏁 Drop-off Specifics (Optional)</label>
                <input type="text" name="dropoff_details" class="form-input" placeholder="e.g., Purok 3, near plaza">
                <small class="input-hint">Helps driver know exactly where to drop you.</small>
            </div>
            <div class="form-group">
                <label class="form-label">👥 Number of Passengers</label>
                <select name="passengers" class="form-select" required>
                    <option value="1">1 Passenger</option>
                    <option value="2">2 Passengers</option>
                    <option value="3">3 Passengers</option>
                    <option value="4">4 Passengers</option>
                </select>
            </div>
            <button type="submit" class="submit-btn">✅ Confirm Booking</button>
        </form>
        <div class="back-link"><a href="{{ url_for('views.passenger_dashboard') }}">← Back to Dashboard</a></div>
    </div>
</div>

<style>
    .booking-container { max-width: 600px; margin: 0 auto; padding: 20px; }
    .booking-card { background: white; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); padding: 30px; }
    .booking-header { text-align: center; margin-bottom: 30px; }
    .emoji-large { font-size: 60px; margin-bottom: 10px; }
    .booking-header h1 { color: purple; font-size: 28px; margin-bottom: 8px; }
    .booking-header p { color: #666; font-size: 16px; }
    .form-group { margin-bottom: 20px; }
    .form-label { display: block; font-weight: 600; color: #333; margin-bottom: 8px; font-size: 14px; }
    .form-select, .form-input { width: 100%; padding: 12px 15px; border: 2px solid #e0e0e0; border-radius: 12px; font-size: 16px; }
    .submit-btn { width: 100%; background: purple; color: white; border: none; padding: 14px; font-size: 18px; font-weight: 600; border-radius: 40px; cursor: pointer; }
    .submit-btn:hover { background: #5a1a5a; transform: scale(1.02); }
    .back-link { text-align: center; margin-top: 20px; }
    .back-link a { color: purple; text-decoration: none; font-size: 14px; }
    .input-hint { display: block; font-size: 12px; color: #999; margin-top: 5px; }
</style>
{% endblock %}
