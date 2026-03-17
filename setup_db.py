from app import app, db
# We import models here to ensure SQLAlchemy sees the User table
from app.models import User 

def create_db():
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    create_db()