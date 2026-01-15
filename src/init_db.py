from flask import Flask
from src.models import db
import os

def init_db():
    app = Flask(__name__)
    # Use SQLite for local development/sandbox
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        print("Database initialized successfully at app.db")

if __name__ == '__main__':
    init_db()
