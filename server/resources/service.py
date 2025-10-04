from flask_restx import Namespace, Resource, fields
from flask import request
from models import db, Service, Stylist

# Namespace
service_ns = Namespace("services", description="Service related operations")

# ----------------- Models -----------------
stylist_model = service_ns.model("Stylist", {
    "id": fields.Integer(readonly=True),
    "name": fields.String,
    "bio": fields.String,
})

service_model = service_ns.model("Service", {
    "id": fields.Integer(readonly=True),
    "title": fields.String(required=True, description="Service title"),
    "description": fields.String(description="Service description"),
    "price": fields.Float(required=True, description="Price of the service"),
    "stylists": fields.List(fields.Nested(stylist_model))
})

update_model = service_ns.model("ServiceUpdate", {
    "title": fields.String(description="Updated title"),
    "description": fields.String(description="Updated description"),
    "price": fields.Float(description="Updated price"),
})


# ----------------- Routes -----------------
@service_ns.route("/")
class ServiceList(Resource):
    @service_ns.marshal_list_with(service_model)
    def get(self):
        """Get all services"""
        return Service.query.all()

    @service_ns.expect(service_model)
    @service_ns.marshal_with(service_model, code=201)
    def post(self):
        """Create a new service"""
        data = request.json
        new_service = Service(
            title=data["title"],
            description=data.get("description"),
            price=data["price"]
        )
        db.session.add(new_service)
        db.session.commit()
        return new_service, 201


@service_ns.route("/<int:id>")
@service_ns.response(404, "Service not found")
class ServiceDetail(Resource):
    @service_ns.marshal_with(service_model)
    def get(self, id):
        """Get service by ID"""
        return Service.query.get_or_404(id)

    @service_ns.expect(update_model)
    @service_ns.marshal_with(service_model)
    def put(self, id):
        """Update service details"""
        service = Service.query.get_or_404(id)
        data = request.json

        if "title" in data:
            service.title = data["title"]
        if "description" in data:
            service.description = data["description"]
        if "price" in data:
            service.price = data["price"]

        db.session.commit()
        return service

    def delete(self, id):
        """Delete a service"""
        service = Service.query.get_or_404(id)
        db.session.delete(service)
        db.session.commit()
        return {"message": "Service deleted"}, 200


# ----------------- Stylist Assignment -----------------
@service_ns.route("/<int:id>/stylists")
class ServiceStylists(Resource):
    @service_ns.marshal_list_with(stylist_model)
    def get(self, id):
        """Get all stylists offering this service"""
        service = Service.query.get_or_404(id)
        return service.stylists

    def post(self, id):
        """Assign a stylist to a service"""
        service = Service.query.get_or_404(id)
        data = request.json
        stylist_id = data.get("stylist_id")

        stylist = Stylist.query.get_or_404(stylist_id)
        service.stylists.append(stylist)

        db.session.commit()
        return {"message": f"Stylist {stylist.name} added to service {service.title}"}, 200

    def delete(self, id):
        """Remove a stylist from a service"""
        service = Service.query.get_or_404(id)
        data = request.json
        stylist_id = data.get("stylist_id")

        stylist = Stylist.query.get_or_404(stylist_id)
        if stylist in service.stylists:
            service.stylists.remove(stylist)
            db.session.commit()
            return {"message": f"Stylist {stylist.name} removed from service {service.title}"}, 200
        return {"message": "Stylist not assigned to this service"}, 400
