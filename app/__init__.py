import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate 
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

# Load environment variables (useful for local development)
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Application configuration
# SECRET_KEY is used for session security and CSRF protection
app.config['SECRET_KEY'] = '135790135790'

# Database configuration (SQLite for simplicity)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skills_exchange.db'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/site/wwwroot/skills_exchange.db'

# Email Configuration (used for account verification and password reset)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '2026commskills@gmail.com'
app.config['MAIL_PASSWORD'] = 'bhlh myff hmob dvzc'
app.config['MAIL_DEFAULT_SENDER'] = '2026commskills@gmail.com'

# Initialize extensions
db = SQLAlchemy(app)              # Database ORM
#from app import models  # 👈 IMPORTANT (forces table registration)

#with app.app_context():
#db.create_all()
  
migrate = Migrate(app, db)        # Database migrations
bcrypt = Bcrypt(app)              # Password hashing
csrf = CSRFProtect(app)           # CSRF protection for forms
login_manager = LoginManager(app) # User session management
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
mail = Mail(app)                  # Email service

# Import routes after app initialization to avoid circular imports
from app import routes
