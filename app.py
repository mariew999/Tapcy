from flask import Flask
from views import views
import os
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'hatdogka'

app.permanent_session_lifetime = timedelta(days=30)

app.register_blueprint(views)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
