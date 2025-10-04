from flask_restx import Namespace, Resource, fields
from flask import request
from models import db, Customer
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

# Create namespace
customer_ns = Namespace("customers", description="Customer related operations")

# ----------------- Models (for Swagger Docs) -----------------
customer_model = customer_ns.model("Customer", {
    "id": fields.Integer(readonly=True, description="Customer ID"),
    "name": fields.String(required=True, description="Customer name"),
    "phone": fields.String(required=True, description="Phone number"),
    "password": fields.String(required=True, description="Password (plain text on create)")
})

update_model = customer_ns.model("CustomerUpdate", {
    "name": fields.String(description="Updated name"),
    "phone": fields.String(description="Updated phone"),
    "password": fields.String(description="Updated password")
})


# ----------------- Routes -----------------
@customer_ns.route("/")
class CustomerList(Resource):
    @customer_ns.marshal_list_with(customer_model)
    def get(self):
        """Get all customers"""
        return Customer.query.all()

    @customer_ns.expect(customer_model)
    @customer_ns.marshal_with(customer_model, code=201)
    def post(self):
        """Create a new customer"""
        data = request.json
        hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")

        new_customer = Customer(
            name=data["name"],
            phone=data["phone"],
            password_hash=hashed_password
        )
        db.session.add(new_customer)
        db.session.commit()
        return new_customer, 201


@customer_ns.route("/<int:id>")
@customer_ns.response(404, "Customer not found")
class CustomerDetail(Resource):
    @customer_ns.marshal_with(customer_model)
    def get(self, id):
        """Get customer by ID"""
        customer = Customer.query.get_or_404(id)
        return customer

    @customer_ns.expect(update_model)
    @customer_ns.marshal_with(customer_model)
    def put(self, id):
        """Update a customer"""
        customer = Customer.query.get_or_404(id)
        data = request.json

        if "name" in data:
            customer.name = data["name"]
        if "phone" in data:
            customer.phone = data["phone"]
        if "password" in data:
            customer.password_hash = bcrypt.generate_password_hash(data["password"]).decode("utf-8")

        db.session.commit()
        return customer

    def delete(self, id):
        """Delete a customer"""
        customer = Customer.query.get_or_404(id)
        db.session.delete(customer)
        db.session.commit()
        return {"message": "Customer deleted"}, 200
