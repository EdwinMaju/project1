from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for both customers and admins"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='customer')  # 'customer' or 'admin'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bookings = db.relationship('Booking', foreign_keys='Booking.user_id', backref='user', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', lazy=True, cascade='all, delete-orphan')
    confirmed_bookings = db.relationship('Booking', foreign_keys='Booking.confirmed_by', backref='admin_confirmer')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.username}>'

class Flight(db.Model):
    """Flight model"""
    __tablename__ = 'flights'
    
    id = db.Column(db.Integer, primary_key=True)
    flight_number = db.Column(db.String(20), unique=True, nullable=False)
    airline = db.Column(db.String(100), nullable=False)
    departure_city = db.Column(db.String(100), nullable=False)
    arrival_city = db.Column(db.String(100), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)   # reference time-of-day
    arrival_time = db.Column(db.DateTime, nullable=False)     # reference time-of-day
    price = db.Column(db.Float, nullable=False)
    available_seats = db.Column(db.Integer, default=200)
    total_seats = db.Column(db.Integer, default=200)
    # Recurring schedule fields
    operating_days = db.Column(db.String(100), default='Mon,Tue,Wed,Thu,Fri,Sat,Sun')  # e.g. "Mon,Wed,Fri"
    schedule_start = db.Column(db.Date)   # first date this schedule is valid
    schedule_end = db.Column(db.Date)     # last date this schedule is valid
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bookings = db.relationship('Booking', backref='flight', lazy=True, cascade='all, delete-orphan')
    
    def runs_on(self, check_date):
        """Check if this flight operates on the given date"""
        if self.schedule_start and check_date < self.schedule_start:
            return False
        if self.schedule_end and check_date > self.schedule_end:
            return False
        day_name = check_date.strftime('%a')  # Mon, Tue, ...
        days = [d.strip() for d in (self.operating_days or '').split(',')]
        return day_name in days
    
    def __repr__(self):
        return f'<Flight {self.flight_number}>'

class Train(db.Model):
    """Train model"""
    __tablename__ = 'trains'
    
    id = db.Column(db.Integer, primary_key=True)
    train_number = db.Column(db.String(20), unique=True, nullable=False)
    train_name = db.Column(db.String(100), nullable=False)
    departure_city = db.Column(db.String(100), nullable=False)
    arrival_city = db.Column(db.String(100), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)   # reference time-of-day
    arrival_time = db.Column(db.DateTime, nullable=False)     # reference time-of-day
    price = db.Column(db.Float, nullable=False)
    available_seats = db.Column(db.Integer, default=500)
    total_seats = db.Column(db.Integer, default=500)
    coach_type = db.Column(db.String(50), default='AC')  # AC, Non-AC, Sleeper
    # Recurring schedule fields
    operating_days = db.Column(db.String(100), default='Mon,Tue,Wed,Thu,Fri,Sat,Sun')
    schedule_start = db.Column(db.Date)
    schedule_end = db.Column(db.Date)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bookings = db.relationship('Booking', backref='train', lazy=True, cascade='all, delete-orphan')
    
    def runs_on(self, check_date):
        """Check if this train operates on the given date"""
        if self.schedule_start and check_date < self.schedule_start:
            return False
        if self.schedule_end and check_date > self.schedule_end:
            return False
        day_name = check_date.strftime('%a')
        days = [d.strip() for d in (self.operating_days or '').split(',')]
        return day_name in days
    
    def __repr__(self):
        return f'<Train {self.train_number}>'

class Hotel(db.Model):
    """Hotel/Accommodation model"""
    __tablename__ = 'hotels'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255))
    description = db.Column(db.Text)
    price_per_night = db.Column(db.Float, nullable=False)
    available_rooms = db.Column(db.Integer, default=50)
    total_rooms = db.Column(db.Integer, default=50)
    rating = db.Column(db.Float, default=4.0)
    amenities = db.Column(db.String(255))  # comma separated
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bookings = db.relationship('Booking', backref='hotel', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Hotel {self.name}>'

class Vehicle(db.Model):
    """Vehicle/Transportation (Car, Bus, etc.) model"""
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_number = db.Column(db.String(50), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)  # Car, Bus, Bike, etc.
    city = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price_per_day = db.Column(db.Float, nullable=False)
    available_units = db.Column(db.Integer, default=20)
    total_units = db.Column(db.Integer, default=20)
    capacity = db.Column(db.Integer)  # Number of passengers
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bookings = db.relationship('Booking', backref='vehicle', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Vehicle {self.vehicle_number}>'

class Booking(db.Model):
    """Booking model - links customer with all bookings"""
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Transportation bookings
    flight_id = db.Column(db.Integer, db.ForeignKey('flights.id'))
    train_id = db.Column(db.Integer, db.ForeignKey('trains.id'))
    
    # Stay and local transport
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'))
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'))
    
    # Booking details
    booking_type = db.Column(db.String(50))  # 'flight', 'train', 'hotel', 'vehicle', 'package'
    booking_status = db.Column(db.String(50), default='pending')  # 'pending', 'confirmed', 'cancelled'
    
    # Dates
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    number_of_passengers = db.Column(db.Integer, default=1)
    number_of_rooms = db.Column(db.Integer, default=1)
    number_of_vehicles = db.Column(db.Integer, default=1)
    number_of_days = db.Column(db.Integer, default=1)
    
    # Cost
    total_cost = db.Column(db.Float, nullable=False)
    commission_amount = db.Column(db.Float, default=0.0)
    
    # Document uploads
    screenshot = db.Column(db.String(255))  # Flight/Train ticket screenshot
    additional_document = db.Column(db.String(255))  # Additional details uploaded
    
    # Admin notes
    admin_notes = db.Column(db.Text)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Admin who confirmed
    confirmed_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payment = db.relationship('Payment', uselist=False, backref='booking', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Booking {self.id} - {self.booking_type}>'

class Payment(db.Model):
    """Payment/QR Code model"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    
    amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(50), default='pending')  # 'pending', 'completed', 'failed'
    payment_method = db.Column(db.String(50), default='qr_code')  # 'qr_code', 'card', 'upi'
    
    # QR Code
    qr_code_path = db.Column(db.String(255))  # Path to generated QR code image
    qr_code_data = db.Column(db.String(500))  # Payment details in QR format
    
    # Payment proof
    payment_screenshot = db.Column(db.String(255))
    transaction_id = db.Column(db.String(100), unique=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Payment {self.id} - {self.payment_status}>'

class HelpDeskMessage(db.Model):
    """Help Desk Message model for customer-admin communication"""
    __tablename__ = 'help_desk_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # 'customer' or 'admin'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to user
    customer = db.relationship('User', foreign_keys=[user_id], backref='help_messages')
    
    def __repr__(self):
        return f'<HelpDeskMessage {self.id} from {self.sender_type}>'
