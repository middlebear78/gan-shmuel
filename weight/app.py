from flask import Flask, Response, request, jsonify
from datetime import datetime
from sqlalchemy import text
import os
import csv
import json


from dotenv import load_dotenv
load_dotenv()
from database import db
from models import ContainerRegistered, Transaction
import config

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}/{config.DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True
}

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

def parse_datetime_param(dt_str):
    """Parse yyyymmddhhmmss string to datetime. Returns None if invalid."""
    try:
        if len(dt_str) != 14:
            return None
        return datetime.strptime(dt_str, "%Y%m%d%H%M%S")
    except (ValueError, TypeError):
        return None
    
def parse_csv(filepath):
    """Parse a CSV file and return a list of (id, weight_in_kg) tuples."""
    records = []

    with open(filepath, "r") as f:
        reader = csv.reader(f)
        header = next(reader)

        if header[0].strip().lower() != "id":
            raise ValueError(f"unexpected first column: '{header[0]}', expected 'id'")

        unit = header[1].strip().lower()

        if unit not in ("kg", "lbs"):
            raise ValueError(f"unsupported unit in header: '{header[1]}'")

        for i, row in enumerate(reader, start=2):
            if len(row) < 2:
                raise ValueError(f"row {i}: expected 2 columns, got {len(row)}")

            container_id = row[0].strip()

            if not container_id:
                raise ValueError(f"row {i}: missing container id")
            
            if not row[1].strip():
                raise ValueError(f"row {i}: missing weight value")

            weight = int(row[1].strip())

            if unit == "lbs":
                weight = lbs_to_kg(weight)

            records.append((container_id, weight))

    return records


def parse_json(filepath):
    """Parse a JSON file and return a list of (id, weight_in_kg) tuples."""
    with open(filepath, "r") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("expected a JSON array")

    records = []
    for i, item in enumerate(data):
        if "id" not in item or "weight" not in item:
            raise ValueError(f"item {i}: missing 'id' or 'weight' field")

        container_id = item["id"]

        if not container_id:
            raise ValueError(f"item {i}: empty 'id' field")
        
        if item["weight"] is None:
            raise ValueError(f"item {i}: missing weight value")

        weight = int(item["weight"])

        unit = item.get("unit", "kg")
        if unit == "lbs":
            weight = lbs_to_kg(weight)

        records.append((container_id, weight))

    return records

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
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "OK"}), 200
    except Exception as e:
        return jsonify({"status": "Failure", "error": str(e)}), 500


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
            datetime=datetime.now().replace(microsecond=0)
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
            datetime=datetime.now().replace(microsecond=0),
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
    

@app.get("/weight")
def get_weight():
    # Defaults: from = today midnight, to = right now
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Read query params
    from_str = request.args.get("from")
    to_str = request.args.get("to")
    filter_str = request.args.get("filter", "in,out,none")

    # Parse dates — use defaults if not provided
    dt_from = parse_datetime_param(from_str) if from_str else today_start
    dt_to = parse_datetime_param(to_str) if to_str else now

    if dt_from is None or dt_to is None:
        return jsonify({"error": "invalid datetime format, expected yyyymmddhhmmss"}), 400

    # Split filter string into a list
    directions = [d.strip() for d in filter_str.split(",")]

    # Query transactions based on datetime range and direction filter
    transactions = Transaction.query.filter(
        Transaction.datetime >= dt_from,
        Transaction.datetime <= dt_to,
        Transaction.direction.in_(directions)
    ).all()

    # Format the response
    result = []
    for t in transactions:
        containers = t.containers.split(",") if t.containers else []
        result.append({
            "id": t.session_id,
            "direction": t.direction,
            "truck": t.truck,
            "bruto": t.bruto,
            "neto": t.neto if t.neto is not None else "na",
            "produce": t.produce,
            "containers": containers
        })

    return jsonify(result), 200

@app.post("/batch-weight")
def post_batch_weight():
    data = request.get_json(silent=True) or request.form.to_dict()
    filename = data.get("file")

    if not filename:
        return jsonify({"error": "missing required field: file"}), 400

    filepath = os.path.join("in", filename)

    if not os.path.exists(filepath):
        return jsonify({"error": f"file not found: {filename}"}), 404
    
    # 1. Parse the file
    try:
        if filename.endswith(".csv"):
            records = parse_csv(filepath)
        elif filename.endswith(".json"):
            records = parse_json(filepath)
        else:
            return jsonify({"error": "unsupported file format, expected .csv or .json"}), 400
    except Exception as e:
        return jsonify({"error": f"failed to parse file: {str(e)}"}), 400

    # 2. Upsert each record into containers_registered
    for container_id, weight_kg in records:
        existing = ContainerRegistered.query.filter_by(container_id=container_id).first()

        if existing:
            existing.weight = weight_kg
            existing.unit = "kg"
        else:
            new_container = ContainerRegistered(
                container_id=container_id,
                weight=weight_kg,
                unit="kg"
            )
            db.session.add(new_container)

    db.session.commit()

    return jsonify({"message": f"processed {len(records)} records"}), 200



@app.get("/session/<session_id>")
def get_session(session_id):
    try:
        session_id = int(session_id)
    except ValueError:
        return jsonify({"error": "invalid session id"}), 400

    out_transaction = Transaction.query.filter_by(
        session_id=session_id,
        direction="out"
    ).first()

    if out_transaction:
        return jsonify({
            "id": str(out_transaction.session_id),
            "truck": out_transaction.truck,
            "bruto": out_transaction.bruto,
            "truckTara": out_transaction.truckTara,
            "neto": out_transaction.neto if out_transaction.neto is not None else "na"
        }), 200

    in_transaction = Transaction.query.filter_by(
        session_id=session_id,
        direction="in"
    ).first()

    if in_transaction:
        return jsonify({
            "id": str(in_transaction.session_id),
            "truck": in_transaction.truck,
            "bruto": in_transaction.bruto
        }), 200

    return jsonify({"error": "session not found"}), 404

@app.get('/item/<id>')
def get_item(id):
    now = datetime.now()
    default_t1 = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    from_str = request.args.get("from")
    to_str = request.args.get("to")


    dt_from = parse_datetime_param(from_str) if from_str else default_t1
    dt_to = parse_datetime_param(to_str) if to_str else now

    if dt_from is None or dt_to is None:
        return jsonify({"error": "invalid datetime format, expected yyyymmddhhmmss"}), 400

    item_type = None
    tara_weight = "na"
    
    container = ContainerRegistered.query.filter_by(container_id=id).first()
    if container:
        item_type = "container"
        if container.weight is not None:
            tara_weight = container.weight
            if container.unit == "lbs":
                tara_weight = lbs_to_kg(tara_weight)
        
                
    else:
        truck_exists = Transaction.query.filter_by(truck=id).first()
        if truck_exists:
            item_type = "truck"
            last_out_tx = Transaction.query.filter(
                Transaction.truck == id, 
                Transaction.direction == "out",
                Transaction.truckTara.isnot(None)
            ).order_by(Transaction.datetime.desc()).first()
            
            if last_out_tx:
                tara_weight = last_out_tx.truckTara
                
    if not item_type:
        return jsonify({"error": "Item not found"}), 404

    sessions = set()
    
    if item_type == "truck":
        truck_transactions = Transaction.query.filter(
            Transaction.truck == id,
            Transaction.datetime >= dt_from,
            Transaction.datetime <= dt_to
        ).all()
        
        for t in truck_transactions:
            if t.session_id is not None:
                sessions.add(t.session_id)
        
    elif item_type == "container":
        all_transactions_in_range = Transaction.query.filter(
            Transaction.datetime >= dt_from,
            Transaction.datetime <= dt_to
        ).all()
        
        for t in all_transactions_in_range:
            if t.containers:
                container_list = [c.strip() for c in t.containers.split(",")]
                if id in container_list and t.session_id is not None:
                    sessions.add(t.session_id)

    return jsonify({
        "id": id,
        "tara": tara_weight,
        "sessions": list(sessions)
    }), 200 


@app.get("/unknown")
def get_unknown():
    transactions = Transaction.query.all()

    all_cids = []
    seen = set()

    for transaction in transactions:
        for cid in parse_containers(transaction.containers):
            cid = cid.strip()
            if cid and cid not in seen:
                seen.add(cid)
                all_cids.append(cid)

    if not all_cids:
        return jsonify([]), 200

    known = ContainerRegistered.query.filter(
        ContainerRegistered.container_id.in_(all_cids),
        ContainerRegistered.weight.isnot(None)
    ).all()

    known_ids = {container.container_id for container in known}

    unknown = [cid for cid in all_cids if cid not in known_ids]

    return jsonify(unknown), 200



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
