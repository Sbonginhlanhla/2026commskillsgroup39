from app import app
from flask import Flask
from flask_wtf.csrf import CSRFProtect

if __name__ == '__main__':
    app.run(debug=True)



app = Flask(__name__)

# IMPORTANT: You must have a secret key set for CSRF to work
app.config['SECRET_KEY'] = '571eb9568728d8856a127a51d2f65a12'

# Initialize CSRF protection
csrf = CSRFProtect(app)