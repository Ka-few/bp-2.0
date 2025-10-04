from flask_restx import Namespace, Resource, fields
from flask import request
from datetime import datetime
from models import db, Booking, Customer, Stylist, Service

# Namespace
booking_ns = Namespace("bookings", description="Booking related operations")

# ----------------- Models -----------------
customer_model = booking_ns.model("Customer", {
    "id": fields.Integer(readonly=True),
    "name": fields.String,
    "phone": fields.String,
})

stylist_model = booking_ns.model("Stylist", {
    "id": fields.Integer(readonly=True),
    "name": fields.String,
    "bio": fields.String,
})

service_model = booking_ns.model("Service", {
    "id": fields.Integer(readonly=True),
    "title": fields.String,
    "price": fields.Float,
})

booking_model = booking_ns.model("Booking", {
    "id": fields.Integer(readonly=True),
    "appointment_time": fields.DateTime(description="Appointment datetime"),
    "customer": fields.Nested(customer_model),
    "stylist": fields.Nested(stylist_model),
    "service": fields.Nested(service_model),
})

create_model = booking_ns.model("BookingCreate", {
    "customer_id": fields.Integer(required=True, description="Customer ID"),
    "stylist_id": fields.Integer(required=True, description="Stylist ID"),
    "service_id": fields.Integer(required=True, description="Service ID"),
    "appointment_time": fields.String(required=True, description="ISO datetime string"),
})

update_model = booking_ns.model("BookingUpdate", {
    "stylist_id": fields.Integer(description="Update stylist"),
    "service_id": fields.Integer(description="Update service"),
    "appointment_time": fields.String(description="Updated appointment time (ISO)"),
})

# ----------------- Routes -----------------
@booking_ns.route("/")
class BookingList(Resource):
    @booking_ns.marshal_list_with(booking_model)
    def get(self):
        """Get all bookings"""
        return Booking.query.all()

    @booking_ns.expect(create_model)
    @booking_ns.marshal_with(booking_model, code=201)
    def post(self):
        """Create a new booking"""
        data = request.json

        customer = Customer.query.get_or_404(data["customer_id"])
        stylist = Stylist.query.get_or_404(data["stylist_id"])
        service = Service.query.get_or_404(data["service_id"])

        # Ensure stylist offers this service
        if service not in stylist.services:
            return {"error": f"Stylist '{stylist.name}' does not offer '{service.title}'"}, 400

        # Parse appointment time
        try:
            appointment_time = datetime.fromisoformat(data["appointment_time"])
        except ValueError:
            return {"error": "Invalid datetime format. Use ISO format."}, 400

        new_booking = Booking(
            customer_id=customer.id,
            stylist_id=stylist.id,
            service_id=service.id,
            appointment_time=appointment_time
        )

        db.session.add(new_booking)
        db.session.commit()
        return new_booking, 201


@booking_ns.route("/<int:id>")
@booking_ns.response(404, "Booking not found")
class BookingDetail(Resource):
    @booking_ns.marshal_with(booking_model)
    def get(self, id):
        """Get booking by ID"""
        return Booking.query.get_or_404(id)

    @booking_ns.expect(update_model)
    @booking_ns.marshal_with(booking_model)
    def put(self, id):
        """Update booking details"""
        booking = Booking.query.get_or_404(id)
        data = request.json

        if "stylist_id" in data:
            stylist = Stylist.query.get_or_404(data["stylist_id"])
            if booking.service not in stylist.services:
                return {"error": f"Stylist '{stylist.name}' does not offer '{booking.service.title}'"}, 400
            booking.stylist = stylist

        if "service_id" in data:
            service = Service.query.get_or_404(data["service_id"])
            if booking.stylist and service not in booking.stylist.services:
                return {"error": f"Stylist '{booking.stylist.name}' does not offer '{service.title}'"}, 400
            booking.service = service

        if "appointment_time" in data:
            try:
                booking.appointment_time = datetime.fromisoformat(data["appointment_time"])
            except ValueError:
                return {"error": "Invalid datetime format. Use ISO format."}, 400

        db.session.commit()
        return booking

    def delete(self, id):
        """Delete a booking"""
        booking = Booking.query.get_or_404(id)
        db.session.delete(booking)
        db.session.commit()
        return {"message": "Booking deleted"}, 200
