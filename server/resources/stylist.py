from flask_restx import Namespace, Resource, fields
from flask import request
from models import db, Stylist, Service

# Create namespace
stylist_ns = Namespace("stylists", description="Stylist related operations")

# ----------------- Models (for Swagger Docs) -----------------
service_model = stylist_ns.model("Service", {
    "id": fields.Integer(readonly=True, description="Service ID"),
    "title": fields.String(required=True, description="Service title"),
    "description": fields.String(description="Service description"),
    "price": fields.Float(description="Service price"),
})

stylist_model = stylist_ns.model("Stylist", {
    "id": fields.Integer(readonly=True, description="Stylist ID"),
    "name": fields.String(required=True, description="Stylist name"),
    "bio": fields.String(description="Short bio"),
    "services": fields.List(fields.Nested(service_model))
})

update_model = stylist_ns.model("StylistUpdate", {
    "name": fields.String(description="Updated name"),
    "bio": fields.String(description="Updated bio"),
})


# ----------------- Routes -----------------
@stylist_ns.route("/")
class StylistList(Resource):
    @stylist_ns.marshal_list_with(stylist_model)
    def get(self):
        """Get all stylists"""
        return Stylist.query.all()

    @stylist_ns.expect(stylist_model)
    @stylist_ns.marshal_with(stylist_model, code=201)
    def post(self):
        """Create a new stylist"""
        data = request.json
        new_stylist = Stylist(
            name=data["name"],
            bio=data.get("bio")
        )
        db.session.add(new_stylist)
        db.session.commit()
        return new_stylist, 201


@stylist_ns.route("/<int:id>")
@stylist_ns.response(404, "Stylist not found")
class StylistDetail(Resource):
    @stylist_ns.marshal_with(stylist_model)
    def get(self, id):
        """Get stylist by ID"""
        stylist = Stylist.query.get_or_404(id)
        return stylist

    @stylist_ns.expect(update_model)
    @stylist_ns.marshal_with(stylist_model)
    def put(self, id):
        """Update stylist details"""
        stylist = Stylist.query.get_or_404(id)
        data = request.json

        if "name" in data:
            stylist.name = data["name"]
        if "bio" in data:
            stylist.bio = data["bio"]

        db.session.commit()
        return stylist

    def delete(self, id):
        """Delete stylist"""
        stylist = Stylist.query.get_or_404(id)
        db.session.delete(stylist)
        db.session.commit()
        return {"message": "Stylist deleted"}, 200


# ----------------- Service Assignment -----------------
@stylist_ns.route("/<int:id>/services")
class StylistServices(Resource):
    @stylist_ns.marshal_list_with(service_model)
    def get(self, id):
        """Get all services for a stylist"""
        stylist = Stylist.query.get_or_404(id)
        return stylist.services

    def post(self, id):
        """Assign a service to a stylist"""
        stylist = Stylist.query.get_or_404(id)
        data = request.json
        service_id = data.get("service_id")

        service = Service.query.get_or_404(service_id)
        stylist.services.append(service)

        db.session.commit()
        return {"message": f"Service {service.title} added to stylist {stylist.name}"}, 200

    def delete(self, id):
        """Remove a service from a stylist"""
        stylist = Stylist.query.get_or_404(id)
        data = request.json
        service_id = data.get("service_id")

        service = Service.query.get_or_404(service_id)
        if service in stylist.services:
            stylist.services.remove(service)
            db.session.commit()
            return {"message": f"Service {service.title} removed from stylist {stylist.name}"}, 200
        return {"message": "Service not assigned to this stylist"}, 400
