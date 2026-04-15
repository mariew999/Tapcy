from flask import Flask
from views import views
import os

# FLASK APP INITIALIZATION
app = Flask(__name__)
# SECRET KEY - required for sessions and flash messages
app.secret_key = 'hatdogka'
# REGISTER BLUEPRINT - connects all routes from views.py
app.register_blueprint(views)

# RENDER DEPLOYMENT SETUP - required for hosting
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
