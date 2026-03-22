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
    certificate_file = db.Column(db.String(120), nullable=True)
    
    # Email verification status
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    password = db.Column(db.String(60), nullable=False)
    
    # Profile information
    profile_pic = db.Column(db.String(20), nullable=False, default='default.jpg')
    headline = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    
    # REPUTATION: Tracks community support
    vouch_count = db.Column(db.Integer, default=0)
    
    # Skills expertise
    skill_cat = db.Column(db.String(50), nullable=True)
    skill_level = db.Column(db.String(20), nullable=True)
    help_text = db.Column(db.Text, nullable=True)
    skills_learn = db.Column(db.String(200), nullable=True)
    
    # Availability and Logistics
    time_commit = db.Column(db.String(50), nullable=True)
    languages = db.Column(db.String(100), nullable=True)
    method_zoom = db.Column(db.Boolean, default=False)
    method_inperson = db.Column(db.Boolean, default=False)
    
    # Professional and Social links
    linkedin = db.Column(db.String(150), nullable=True)
    instagram = db.Column(db.String(150), nullable=True)

    # RELATIONSHIP: Links to the Request table
    # Allows you to access all of a user's requests via: current_user.requests
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
        return f"User('{self.username}', '{self.email}', 'Vouches: {self.vouch_count}')"

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    offer = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Foreign Key: links the request back to a specific User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Request('{self.title}', '{self.category}', '{self.date_posted}')"