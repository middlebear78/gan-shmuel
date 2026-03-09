from flask import Blueprint, request, jsonify
from sqlalchemy import text
from models import db, Provider, Truck, Rate

health_bp = Blueprint("health", __name__)

# health check
@health_bp.route("/health", methods=["GET"])
def health():
    try:
        # run lightweight DB check
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "OK",}), 200

    except Exception as e:
        return jsonify({"status": "Failure", "error": str(e)}), 500