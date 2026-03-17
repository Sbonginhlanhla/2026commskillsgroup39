from datetime import datetime
from itsdangerous import URLSafeTimedSerializer as Serializer
from app import db, login_manager, app
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # --- NEW: Tracks if the user verified their email (POPIA compliance) ---
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    
    password = db.Column(db.String(60), nullable=False)
    
    # Profile columns
    profile_pic = db.Column(db.String(20), nullable=False, default='default.jpg')
    headline = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    
    # Skills section
    skill_cat = db.Column(db.String(50), nullable=True)
    skill_level = db.Column(db.String(20), nullable=True)
    help_text = db.Column(db.Text, nullable=True)
    skills_learn = db.Column(db.String(200), nullable=True)
    
    # Logistics section
    time_commit = db.Column(db.String(50), nullable=True)
    languages = db.Column(db.String(100), nullable=True)
    method_zoom = db.Column(db.Boolean, default=False)
    method_inperson = db.Column(db.Boolean, default=False)
    
    # Social links
    linkedin = db.Column(db.String(150), nullable=True)
    instagram = db.Column(db.String(150), nullable=True)

    # NEW: This links the User to all the requests they create!
    requests = db.relationship('Request', backref='author', lazy=True)

    def get_reset_token(self):
        s = Serializer(app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=expires_sec)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

# --- HERE IS THE MISSING REQUEST TABLE! ---
class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    offer = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # This stores the ID of the user who made the request
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Request('{self.title}', '{self.category}')"