from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_serializer import SerializerMixin
from datetime import datetime

db = SQLAlchemy()

# Association table for many-to-many relationship between Stylists and Services
stylist_service = db.Table(
    "stylist_service",
    db.Column("stylist_id", db.Integer, db.ForeignKey("stylist.id"), primary_key=True),
    db.Column("service_id", db.Integer, db.ForeignKey("service.id"), primary_key=True)
)

# ----------------- CUSTOMER -----------------
class Customer(db.Model, SerializerMixin):
    __tablename__ = "customer"
    serialize_rules = (
        "-bookings.customer", 
        "-bookings.stylist", 
        "-bookings.service",
        "-payments.customer",
        "-notifications.customer"
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    bookings = db.relationship(
        "Booking",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    payments = db.relationship(
        "Payment",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    notifications = db.relationship(
        "Notification",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

# ----------------- SERVICE -----------------
class Service(db.Model, SerializerMixin):
    __tablename__ = "service"
    serialize_rules = (
        "-stylists.services", 
        "-bookings.service", 
        "-bookings.customer", 
        "-bookings.stylist"
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    price = db.Column(db.Float, nullable=False)

# ----------------- STYLIST -----------------
class Stylist(db.Model, SerializerMixin):
    __tablename__ = "stylist"
    serialize_rules = (
        "-services.stylists", 
        "-bookings.stylist", 
        "-bookings.customer", 
        "-bookings.service",
        "-portfolio.stylist",
        "-reviews.stylist"
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.String(255), nullable=True)

    services = db.relationship(
        "Service",
        secondary=stylist_service,
        backref=db.backref("stylists", lazy="joined")
    )

    bookings = db.relationship(
        "Booking",
        back_populates="stylist",
        cascade="all, delete-orphan"
    )

    portfolio = db.relationship(
        "Portfolio",
        back_populates="stylist",
        cascade="all, delete-orphan"
    )

    reviews = db.relationship(
        "Review",
        back_populates="stylist",
        cascade="all, delete-orphan"
    )

# ----------------- BOOKING -----------------
class Booking(db.Model, SerializerMixin):
    __tablename__ = "booking"
    serialize_rules = (
        "-customer.bookings", 
        "-stylist.bookings", 
        "-service.bookings",
        "-payment.booking",
        "-notifications.booking"
    )

    id = db.Column(db.Integer, primary_key=True)
    appointment_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, confirmed, completed, cancelled

    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    customer = db.relationship("Customer", back_populates="bookings")

    stylist_id = db.Column(db.Integer, db.ForeignKey("stylist.id"), nullable=False)
    stylist = db.relationship("Stylist", back_populates="bookings")

    service_id = db.Column(db.Integer, db.ForeignKey("service.id"), nullable=False)
    service = db.relationship("Service", backref="bookings")

    payment = db.relationship("Payment", back_populates="booking", uselist=False)
    notifications = db.relationship("Notification", back_populates="booking", cascade="all, delete-orphan")

# ----------------- PAYMENT -----------------
class Payment(db.Model, SerializerMixin):
    __tablename__ = "payment"
    serialize_rules = ("-customer.payments", "-booking.payment")

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), nullable=False)  # mpesa, card, paypal, cash
    status = db.Column(db.String(20), default="pending")  # pending, successful, failed, refunded
    transaction_id = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    booking = db.relationship("Booking", back_populates="payment")
    customer = db.relationship("Customer", back_populates="payments")

# ----------------- NOTIFICATION -----------------
class Notification(db.Model, SerializerMixin):
    __tablename__ = "notification"
    serialize_rules = ("-customer.notifications", "-booking.notifications")

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # reminder, offer, system
    status = db.Column(db.String(20), default="unread")  # unread, read, sent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    customer = db.relationship("Customer", back_populates="notifications")

    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=True)
    booking = db.relationship("Booking", back_populates="notifications")

# ----------------- PORTFOLIO -----------------
class Portfolio(db.Model, SerializerMixin):
    __tablename__ = "portfolio"
    serialize_rules = ("-stylist.portfolio",)

    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    stylist_id = db.Column(db.Integer, db.ForeignKey("stylist.id"), nullable=False)
    stylist = db.relationship("Stylist", back_populates="portfolio")

# ----------------- REVIEW -----------------
class Review(db.Model, SerializerMixin):
    __tablename__ = "review"
    serialize_rules = ("-stylist.reviews",)

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    stylist_id = db.Column(db.Integer, db.ForeignKey("stylist.id"), nullable=False)
    stylist = db.relationship("Stylist", back_populates="reviews")

    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
