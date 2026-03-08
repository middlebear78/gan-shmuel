from flask import Blueprint, request, jsonify
from models import db, Provider, Truck

truck_bp = Blueprint("truck", __name__)


@truck_bp.route("/truck", methods=["POST"])
def new_truck():
    data = request.get_json()
    truck_id=data.get("id")
    provider_id = data.get("provider")
    if not truck_id or not provider_id:
         return jsonify({"error": "Truck id and provider are required"}), 400
    if Provider.query.get(provider_id)==None:
          return jsonify({"error": f"Provider: {provider_id} does not exist" }), 404
    if Truck.query.get(truck_id)!=None:
          return jsonify({"error": f"Truck '{truck_id}' already exists"}), 409
    new_truck = Truck(id=truck_id,provider_id=provider_id)
    db.session.add(new_truck)
    db.session.commit()
    return jsonify({"id": str(new_truck.id)}), 201

@truck_bp.route("/truck/<string:truck_id>", methods=["PUT"])
def update_truck(truck_id):
    data = request.get_json(silent=True) or {}
    provider_id = data.get("provider")
    if not provider_id:
           return jsonify({"error": "provider is required"}), 400
    if Provider.query.get(provider_id) is None:
          return jsonify({"error": f"Provider: {provider_id} does not exist" }), 404
    truck = Truck.query.get(truck_id)
    if truck is None:
     return jsonify({"error": f"Truck: {truck_id} does not exist" }), 404
    truck.provider_id = provider_id
    db.session.commit()
    return jsonify({"id": truck.id, "provider": truck.provider_id}), 200