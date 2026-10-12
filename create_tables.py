from dotenv import load_dotenv
load_dotenv()
from app import app, db

with app.app_context():
    db.create_all()
    print("Tables ready")