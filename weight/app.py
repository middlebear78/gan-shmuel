from flask import Flask, request, jsonify
from database import db
from models import ContainerRegistered, Transactions
import config

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}/{config.DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# --- Utility functions ---

def lbs_to_kg(lbs):
    """Convert pounds to kg, rounded to int (scale precision is ~5kg)."""
    return int(lbs * 0.453592)

def parse_containers(containers_str):
    """Convert comma-delimited containers string to a list."""
    return containers_str.split(",") if containers_str else []

def parse_force(value):
    """ Convert various force inputs to a boolean. """
    return str(value).lower() == "true"

# --- Routes ---

@app.get("/health")
def health():
    return Response("OK", status=200, mimetype="text/plain")

@app.post("/weight")
def post_weight():
    data = request.get_json(silent=True) or request.form.to_dict()

    direction = data.get("direction")
    weight = data.get("weight")

    if not direction or not weight:
        return jsonify({"error": "missing required fields: direction and weight"}), 400

    weight = int(weight)
    truck = data.get("truck", "na")
    containers = parse_containers(data.get("containers", ""))
    unit = data.get("unit", "kg")
    force = parse_force(data.get("force", False))
    produce = data.get("produce", "na")

    if unit == "lbs":
        weight = lbs_to_kg(weight)
    
    return jsonify({"status": "not yet implemented"}), 501

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
