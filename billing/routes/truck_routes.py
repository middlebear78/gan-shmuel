from flask import Blueprint, request, jsonify
from models import db, Provider, Truck

truck_bp = Blueprint("truck", __name__)


@truck_bp.route("/truck", methods=["POST"])
def new_truck():
    data = request.get_json()
    truck_id=data.get("id")
    provider_id = data.get("provider")
    if not truck_id or not provider_id:
         return jsonify({"error": f"Truck id and provider are required"}), 400
    if Provider.query.get(provider_id)==None:
          return jsonify({"error": f"Provider: {provider_id} does not exist" }), 404
    if Truck.query.get(truck_id)!=None:
          return jsonify({"error": f"Truck '{truck_id}' already exists"}), 409
    new_truck = Truck(id=truck_id,provider_id=provider_id)
    db.session.add(new_truck)
    db.session.commit()
    return jsonify({"id": str(new_truck.id)}), 201