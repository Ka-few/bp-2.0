from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from flask_restx import Api, Resource, fields, Namespace
from datetime import datetime
from models import db, Customer, Stylist, Service, Booking

from models import db  # import your db instance
from resources.auth import auth_ns
from resources.customer import customer_ns
from resources.stylist import stylist_ns
from resources.service import service_ns
from resources.booking import booking_ns

# ----------------- APP CONFIG ----------------- #
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://user:password@localhost:5432/beautyparlour"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "supersecretkey"  # change in production!

CORS(
    app,
    resources={r"/*": {"origins": [
        "http://localhost:5173"
        
    ]}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

db.init_app(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
api = Api(app, title="Beauty Parlour API", version="1.0", description="Backend for Beauty Parlour App")

# ----------------- HELPERS ----------------- #
def admin_required(fn):
    """Decorator to restrict access to admins only"""
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = Customer.query.get(current_user_id)
        if not user or not user.is_admin:
            return {"error": "Admin access required"}, 403
        return fn(*args, **kwargs)
    return wrapper

# ----------------- NAMESPACES ----------------- #
auth_ns = Namespace("auth", description="Authentication & Users")
services_ns = Namespace("services", description="Service Management")
bookings_ns = Namespace("bookings", description="Booking Management")
stylists_ns = Namespace("stylists", description="Stylist Management")
profiles_ns = Namespace("profiles", description="Customer & Stylist Profiles")

# ----------------- MODELS ----------------- #
register_model = auth_ns.model("Register", {
    "name": fields.String(required=True),
    "phone": fields.String(required=True),
    "password": fields.String(required=True),
    "is_admin": fields.Boolean(default=False),
})

login_model = auth_ns.model("Login", {
    "phone": fields.String(required=True),
    "password": fields.String(required=True),
})

customer_update_model = profiles_ns.model("CustomerUpdate", {
    "name": fields.String(required=False),
    "phone": fields.String(required=False),
})

stylist_update_model = profiles_ns.model("StylistUpdate", {
    "name": fields.String(required=False),
    "bio": fields.String(required=False),
    "service_ids": fields.List(fields.Integer, description="IDs of services offered"),
})

# ----------------- AUTH ----------------- #
@auth_ns.route("/register")
class Register(Resource):
    @auth_ns.expect(register_model)
    def post(self):
        data = request.get_json()
        if Customer.query.filter_by(phone=data["phone"]).first():
            return {"error": "Phone already registered"}, 400

        hashed_pw = bcrypt.generate_password_hash(data["password"]).decode()
        customer = Customer(
            name=data["name"],
            phone=data["phone"],
            password_hash=hashed_pw,
            is_admin=data.get("is_admin", False),
        )
        db.session.add(customer)
        db.session.commit()

        token = create_access_token(identity=str(customer.id))
        return {"customer": customer.to_dict(), "access_token": token}, 201


@auth_ns.route("/login")
class Login(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        data = request.get_json()
        customer = Customer.query.filter_by(phone=data["phone"]).first()
        if not customer or not bcrypt.check_password_hash(customer.password_hash, data["password"]):
            return {"error": "Invalid credentials"}, 401

        token = create_access_token(identity=str(customer.id))
        return {"customer": customer.to_dict(), "access_token": token}, 200


@auth_ns.route("/me")
class Me(Resource):
    @jwt_required()
    def get(self):
        current_customer_id = get_jwt_identity()
        customer = Customer.query.get(current_customer_id)
        if not customer:
            return {"error": "Customer not found"}, 404
        return {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "is_admin": customer.is_admin
        }, 200

# ----------------- SERVICES ----------------- #
@services_ns.route("")
class ServiceList(Resource):
    def get(self):
        services = Service.query.all()
        return [s.to_dict() for s in services], 200

    @jwt_required()
    def post(self):
        data = request.get_json()
        service = Service(
            title=data.get("title"),
            description=data.get("description", ""),
            price=float(data["price"])
        )
        db.session.add(service)
        db.session.commit()
        return service.to_dict(), 201


@services_ns.route("/<int:service_id>")
class ServiceDetail(Resource):
    def get(self, service_id):
        service = Service.query.get_or_404(service_id)
        return service.to_dict(), 200

    @jwt_required()
    def put(self, service_id):
        service = Service.query.get_or_404(service_id)
        data = request.get_json()
        service.title = data.get("title", service.title)
        service.description = data.get("description", service.description)
        service.price = float(data.get("price", service.price))
        db.session.commit()
        return service.to_dict(), 200

    @jwt_required()
    def delete(self, service_id):
        service = Service.query.get_or_404(service_id)
        db.session.delete(service)
        db.session.commit()
        return {}, 204

# ----------------- BOOKINGS ----------------- #
@bookings_ns.route("")
class BookingList(Resource):
    @jwt_required()
    def get(self):
        current_customer_id = get_jwt_identity()
        bookings = Booking.query.filter_by(customer_id=int(current_customer_id)).all()
        return [b.to_dict() for b in bookings], 200

    @jwt_required()
    def post(self):
        current_customer_id = get_jwt_identity()
        data = request.get_json()
        customer = Customer.query.get(current_customer_id)
        stylist = Stylist.query.get(data["stylist_id"])
        service = Service.query.get(data["service_id"])

        if not customer or not stylist or not service:
            return {"error": "Invalid booking data"}, 400
        if service not in stylist.services:
            return {"error": f"Stylist '{stylist.name}' does not offer '{service.title}'"}, 400

        appointment_time = None
        if data.get("appointment_time"):
            try:
                appointment_time = datetime.fromisoformat(data["appointment_time"])
            except ValueError:
                return {"error": "Invalid datetime format"}, 400

        booking = Booking(
            customer_id=customer.id,
            stylist_id=stylist.id,
            service_id=service.id,
            appointment_time=appointment_time
        )
        db.session.add(booking)
        db.session.commit()
        return booking.to_dict(), 201

# ----------------- STYLISTS ----------------- #
@stylists_ns.route("")
class StylistList(Resource):
    @jwt_required()
    def get(self):
        stylists = Stylist.query.all()
        return [s.to_dict(rules=("-services.stylists", "-bookings.stylist")) for s in stylists], 200

    @admin_required
    def post(self):
        data = request.get_json()
        services = Service.query.filter(Service.id.in_(data.get("service_ids", []))).all()
        stylist = Stylist(name=data["name"], bio=data.get("bio"), services=services)
        db.session.add(stylist)
        db.session.commit()
        return stylist.to_dict(), 201


@stylists_ns.route("/<int:stylist_id>")
class StylistDetail(Resource):
    def get(self, stylist_id):
        stylist = Stylist.query.get_or_404(stylist_id)
        return stylist.to_dict(rules=("-services.stylists", "-bookings.stylist")), 200

    @admin_required
    def put(self, stylist_id):
        stylist = Stylist.query.get_or_404(stylist_id)
        data = request.get_json()
        stylist.name = data.get("name", stylist.name)
        stylist.bio = data.get("bio", stylist.bio)
        if "service_ids" in data:
            stylist.services = Service.query.filter(Service.id.in_(data["service_ids"])).all()
        db.session.commit()
        return stylist.to_dict(), 200

    @admin_required
    def delete(self, stylist_id):
        stylist = Stylist.query.get_or_404(stylist_id)
        db.session.delete(stylist)
        db.session.commit()
        return {"message": "Stylist deleted"}, 200

# ----------------- PROFILES ----------------- #
@profiles_ns.route("/customers/<int:customer_id>")
class CustomerProfile(Resource):
    @jwt_required()
    def get(self, customer_id):
        customer = Customer.query.get_or_404(customer_id)
        profile = customer.to_dict()
        profile["appointments"] = [b.to_dict() for b in customer.bookings]
        return profile, 200

    @jwt_required()
    @profiles_ns.expect(customer_update_model)
    def put(self, customer_id):
        current_user_id = get_jwt_identity()
        if current_user_id != customer_id:
            return {"error": "You can only update your own profile"}, 403
        customer = Customer.query.get_or_404(customer_id)
        data = profiles_ns.payload
        customer.name = data.get("name", customer.name)
        customer.phone = data.get("phone", customer.phone)
        db.session.commit()
        return customer.to_dict(), 200


@profiles_ns.route("/stylists/<int:stylist_id>")
class StylistProfile(Resource):
    def get(self, stylist_id):
        stylist = Stylist.query.get_or_404(stylist_id)
        profile = stylist.to_dict(rules=("-services.stylists", "-bookings.stylist"))
        profile["appointments"] = [b.to_dict() for b in stylist.bookings]
        return profile, 200

    @admin_required
    @profiles_ns.expect(stylist_update_model)
    def put(self, stylist_id):
        stylist = Stylist.query.get_or_404(stylist_id)
        data = profiles_ns.payload
        stylist.name = data.get("name", stylist.name)
        stylist.bio = data.get("bio", stylist.bio)
        if "service_ids" in data:
            stylist.services = Service.query.filter(Service.id.in_(data["service_ids"])).all()
        db.session.commit()
        return stylist.to_dict(), 200

# ----------------- REGISTER NAMESPACES ----------------- #
api.add_namespace(auth_ns)
api.add_namespace(customer_ns)
api.add_namespace(stylist_ns)
api.add_namespace(service_ns)
api.add_namespace(booking_ns)

# ----------------- MAIN ----------------- #
if __name__ == "__main__":
    app.run(debug=True)
