from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


# ---------------- USER MODEL ----------------
class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")

    records = db.relationship("HealthRecord", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ---------------- HEALTH RECORD MODEL ----------------
class HealthRecord(db.Model):
    __tablename__ = "health_record"

    id = db.Column(db.Integer, primary_key=True)

    weight = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, nullable=False)
    bmi = db.Column(db.Float)

    systolic = db.Column(db.Integer, nullable=False)
    diastolic = db.Column(db.Integer, nullable=False)

    sugar = db.Column(db.Float, nullable=False)
    water = db.Column(db.Float, nullable=False)

    date = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # 🔥 AUTO BMI CALCULATION
    def calculate_bmi(self):
        if self.height and self.height > 0:
            self.bmi = round(self.weight / (self.height ** 2), 2)
        else:
            self.bmi = None
