from flask import Flask
from views import views
import os

app = Flask(__name__)
app.secret_key = 'hatdogka'
app.register_blueprint(views)

# This is needed for Render
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
