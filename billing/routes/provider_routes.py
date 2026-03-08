from flask import Blueprint, request, jsonify
from models import db, Provider

provider_bp = Blueprint("provider", __name__)

# ____________________________________________________________________
# helper functions
def checkProviderExists(providerName: str):
    return Provider.query.filter(db.func.lower(Provider.name) == providerName.lower()).first()

# ____________________________________________________________________
# routes

# POST /provider
@provider_bp.route("/provider", methods=["POST"])
def new_provider():
    data = request.get_json()
    provider_name = (data.get("name") or "").strip()
    if not provider_name:
        return jsonify({"error": "Provider name is required"}), 400
    
    existing = checkProviderExists(provider_name)
    if existing:
        return jsonify({"error": f"Provider '{provider_name}' already exists"}), 409

    new_provider = Provider(name=provider_name)
    db.session.add(new_provider)
    db.session.commit()
    return jsonify({"id": str(new_provider.id)}), 201


# PUT /provider/<id>
@provider_bp.route("/provider/<int:provider_id>", methods=["PUT"])
def update_provider(provider_id):
    # get data
    data = request.get_json(silent=True) or {}
    new_name = (data.get("name") or "").strip()

    if not new_name:
        return jsonify({"error": "Provider name is required"}), 400

    # get provider by id
    provider = Provider.query.get(provider_id)
    if not provider:
        return jsonify({"error": "Provider not found"}), 404

    # check if existing name
    existing = checkProviderExists(new_name)
    if existing:
        return jsonify({"error": f"Provider '{new_name}' already exists"}), 409

    # change name by ref
    provider.name = new_name
    db.session.commit()

    return jsonify({
        "id": provider.id,
        "name": provider.name
    }), 200
