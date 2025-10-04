from flask_restx import Namespace, Resource, fields
from flask import request
from models import db, Customer
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

bcrypt = Bcrypt()

# Namespace
auth_ns = Namespace("auth", description="Authentication endpoints")

# ----------------- Models -----------------
register_model = auth_ns.model("Register", {
    "name": fields.String(required=True, description="Full name"),
    "phone": fields.String(required=True, description="Phone number"),
    "password": fields.String(required=True, description="Password"),
    "is_admin": fields.Boolean(description="Admin user?", default=False)
})

login_model = auth_ns.model("Login", {
    "phone": fields.String(required=True, description="Phone number"),
    "password": fields.String(required=True, description="Password"),
})

me_model = auth_ns.model("Me", {
    "id": fields.Integer,
    "name": fields.String,
    "phone": fields.String,
    "is_admin": fields.Boolean
})

# ----------------- Endpoints -----------------
@auth_ns.route("/register")
class Register(Resource):
    @auth_ns.expect(register_model)
    def post(self):
        """Register a new user"""
        data = request.json

        if Customer.query.filter_by(phone=data["phone"]).first():
            return {"error": "Phone already registered"}, 400

        hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")

        new_customer = Customer(
            name=data["name"],
            phone=data["phone"],
            password_hash=hashed_pw,
            is_admin=data.get("is_admin", False)
        )
        db.session.add(new_customer)
        db.session.commit()

        token = create_access_token(identity=new_customer.id)

        return {
            "customer": {
                "id": new_customer.id,
                "name": new_customer.name,
                "phone": new_customer.phone,
                "is_admin": new_customer.is_admin
            },
            "access_token": token
        }, 201


@auth_ns.route("/login")
class Login(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        """Login and get a JWT"""
        data = request.json
        customer = Customer.query.filter_by(phone=data["phone"]).first()

        if not customer or not bcrypt.check_password_hash(customer.password_hash, data["password"]):
            return {"error": "Invalid credentials"}, 401

        token = create_access_token(identity=customer.id)

        return {
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
                "is_admin": customer.is_admin
            },
            "access_token": token
        }, 200


@auth_ns.route("/me")
class Me(Resource):
    @jwt_required()
    @auth_ns.marshal_with(me_model)
    def get(self):
        """Get the currently logged-in user"""
        user_id = get_jwt_identity()
        customer = Customer.query.get_or_404(user_id)
        return customer
