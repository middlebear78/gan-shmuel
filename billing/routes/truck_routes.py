from flask import Blueprint, request, jsonify
from models import db, Provider, Truck
from datetime import datetime
import requests
from dotenv import load_dotenv
import os

truck_bp = Blueprint("truck", __name__)

WEIGHT_SERVER_URL=os.getenv("WEIGHT_SERVER_URL")

@truck_bp.route("/truck", methods=["POST"])
def new_truck():
    data = request.get_json(silent=True) or {}
    truck_id=data.get("id")
    provider_id = data.get("provider")
    if not truck_id or not provider_id:
         return jsonify({"error": "Truck id and provider are required"}), 400
    if db.session.get(Provider, provider_id) is None:
          return jsonify({"error": f"Provider: {provider_id} does not exist" }), 404
    if db.session.get(Truck, truck_id) is not None:
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
    if db.session.get(Provider, provider_id) is None:
        return jsonify({"error": f"Provider: {provider_id} does not exist" }), 404
    truck = db.session.get(Truck, truck_id)
    if truck is None:
        return jsonify({"error": f"Truck: {truck_id} does not exist" }), 404
    truck.provider_id = provider_id
    db.session.commit()
    return jsonify({"id": truck.id, "provider": truck.provider_id}), 200

@truck_bp.route("/truck/<string:truck_id>", methods=["GET"])
def data_about_truck(truck_id):
    t1,t2=get_time_range()
    truck = db.session.get(Truck, truck_id)
    if truck is None:
        return jsonify({"error": f"Truck: {truck_id} does not exist" }), 404
    tara = "na"
    sessions = []

    try:
        weight_api_url = f"{WEIGHT_SERVER_URL}/item/{truck_id}?from={t1}&to={t2}"
        response = requests.get(weight_api_url)        
        if response.status_code == 200:
            weight_data = response.json()
            tara = weight_data.get("tara", "na")
            sessions = weight_data.get("sessions", [])
            
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not connect to Weight server: {e}")
    return jsonify({
            "id": truck.id,
            "tara": tara,
            "sessions":sessions}), 200


#######################

def get_time_range():
    now = datetime.now()
    default_t1_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    default_t1 = default_t1_dt.strftime('%Y%m%d%H%M%S')
    default_t2 = now.strftime('%Y%m%d%H%M%S')

    def validate_or_default(value, default):
            if not value:
                return default
            try:
                datetime.strptime(value, '%Y%m%d%H%M%S')
                return value
            except ValueError:
               
                return default
    t1 = validate_or_default(request.args.get('from'), default_t1)
    t2 = validate_or_default(request.args.get('to'), default_t2)
    return t1,t2
