from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    profile_type = db.Column(db.String(7))  # 'user', 'marshal', 'admin'
    national_id = db.Column(db.String(20), unique=True, nullable=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=True)
    first_name = db.Column(db.String(50))
    surname = db.Column(db.String(50))
    email = db.Column(db.String(50), nullable=True)
    gender = db.Column(db.String(6))
    phone = db.Column(db.String(20))
    password = db.Column(db.String(200))
    zone = db.Column(db.String(20), nullable=True)

class ParkingZone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True)
    total_spots = db.Column(db.Integer, default=4)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    zone_id = db.Column(db.Integer, db.ForeignKey('parking_zone.id'))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="booked")
    payment_currency = db.Column(db.String(10), nullable=True)
    payment_time = db.Column(db.DateTime, nullable=True)
    payment_amount = db.Column(db.Float, nullable=True)

class MarshalShift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    marshal_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    zone_id = db.Column(db.Integer, db.ForeignKey('parking_zone.id'))
    shift_date = db.Column(db.Date, default=datetime.now)
    check_in_time = db.Column(db.DateTime)
    location = db.Column(db.String(255), nullable=False)
    approved = db.Column(db.Boolean, default=None)
    declined_reason = db.Column(db.String(255), nullable=True)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    subject = db.Column(db.String(150))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

