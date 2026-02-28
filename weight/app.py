from flask import Flask, Response, request, jsonify
from datetime import datetime
from database import db
from models import ContainerRegistered, Transaction
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

# --- Business logic helpers ---

def calculate_neto(bruto, truck_tara, container_ids):
    """Calculate neto weight. Returns int or 'na' if any container tara unknown."""
    container_taras = []

    for cid in container_ids:
        container = ContainerRegistered.query.filter_by(container_id=cid.strip()).first()
        if container and container.weight is not None:
            tara = container.weight
            if container.unit == "lbs":
                tara = lbs_to_kg(tara)
            container_taras.append(tara)
        else:
            container_taras.append(None)

    if None in container_taras:
        return "na"
    return bruto - truck_tara - sum(container_taras)

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
    
    # --- IN or NONE: create a new session ---
    if direction in ("in", "none"):
        # Check for existing open session for this truck
        if truck != "na":
            existing = Transaction.query.filter_by(
                truck=truck, direction="in", truckTara=None
            ).first()

            if existing:
                if direction == "none":
                    # "none" after "in" is always an error
                    return jsonify({"error": "truck has an open 'in' session, cannot use direction 'none'"}), 400
                elif not force:
                    # "in" after "in" without force is an error
                    return jsonify({"error": "truck already weighed in, use force=true to overwrite"}), 400
                else:
                    # "in" after "in" with force — delete the old session
                    db.session.delete(existing)
                    db.session.commit()

        new_transaction = Transaction(
            direction=direction,
            truck=truck,
            containers=",".join(containers),
            bruto=weight,
            produce=produce,
            datetime=datetime.now()
        )

        db.session.add(new_transaction)
        db.session.commit()

        new_transaction.session_id = new_transaction.id
        db.session.commit()

        return jsonify({
            "id": str(new_transaction.session_id),
            "truck": truck,
            "bruto": weight
        }), 200
    
    # --- OUT: close an existing session ---
    elif direction == "out":
        # 1. Find the open "in" session for this truck
        open_session = Transaction.query.filter_by(
            truck=truck, direction="in", truckTara=None
            ).first()
        
        if not open_session:
            return jsonify({"error": "no open 'in' session for this truck"}), 400
        
        # 2. Check for existing "out" in this session
        existing_out = Transaction.query.filter_by(
            session_id=open_session.session_id, direction="out"
        ).first()

        if existing_out:
            if not force:
                return jsonify({"error": "truck already weighed out, use force=true to overwrite"}), 400
            else:
                db.session.delete(existing_out)
                db.session.commit()
        
        # 3. truckTara is the weight from the scale right now
        truck_tara = weight

        # 4. Look up each container's tara weight & calculate neto
        container_ids = open_session.containers.split(",") if open_session.containers else []
        neto = calculate_neto(open_session.bruto, truck_tara, container_ids)
        
        # 5. Create the "out" transaction
        out_transaction = Transaction(
            direction="out",
            truck=truck,
            containers=open_session.containers,
            bruto=open_session.bruto,
            truckTara=truck_tara,
            neto=neto if neto != "na" else None,
            produce=open_session.produce,
            datetime=datetime.now(),
            session_id=open_session.session_id
        )

        db.session.add(out_transaction)
        db.session.commit()

        return jsonify({
            "id": str(open_session.session_id),
            "truck": truck,
            "bruto": open_session.bruto,
            "truckTara": truck_tara,
            "neto": neto
        }), 200
    
    else:
        return jsonify({"error": "invalid direction"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
