from flask import Blueprint, request, jsonify
from datetime import datetime
import requests

from models import db, Provider, Truck, Rate

WEIGHT_API = "http://weight-service:5000"

bill_bp = Blueprint("bill", __name__)


# --------------------------------------------------
# Helper: parse timestamp
# --------------------------------------------------

def parse_timestamp(timeStamp_string):
    try:
        return datetime.strptime(timeStamp_string, "%Y%m%d%H%M%S")
    except Exception:
        return None


# --------------------------------------------------
# Helper: default timestamps
# --------------------------------------------------

def resolve_time_range(from_timeStamp, to_timeStamp):

    now = datetime.now()

    if from_timeStamp:
        start = parse_timestamp(from_timeStamp)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if to_timeStamp:
        end = parse_timestamp(to_timeStamp)
    else:
        end = now

    return start, end


# --------------------------------------------------
# Helper: get provider trucks
# --------------------------------------------------

def get_provider_trucks(provider_id):

    trucks = Truck.query.filter_by(provider_id=provider_id).all()

    return [truck.id for truck in trucks]


# --------------------------------------------------
# Helper: fetch weight and sessions
# --------------------------------------------------

def fetch_weights(start, end):

    params = {
        "from": start.strftime("%Y%m%d%H%M%S"),
        "to": end.strftime("%Y%m%d%H%M%S"),
        "filter": "out"
    }

    response = requests.get(f"{WEIGHT_API}/weight", params=params)

    if response.status_code != 200:
        raise Exception("weight service error")

    return response.json()


def fetch_session(session_id):

    response = requests.get(f"{WEIGHT_API}/session/{session_id}")

    if response.status_code != 200:
        return None

    return response.json()


# --------------------------------------------------
# Helper: main billing logic
# --------------------------------------------------

def generate_bill(provider, start, end):
    provider_trucks = set(get_provider_trucks(provider.id))
    weights = fetch_weights(start, end)

    product_stats = {}
    trucks_seen = set()
    sessions_seen = set()

    for w in weights:
        if w["neto"] == "na":
            continue

        session_id = w["id"]
        session = fetch_session(session_id)

        if not session:
            continue

        truck_id = session.get("truck")
        if truck_id not in provider_trucks:
            continue

        trucks_seen.add(truck_id)
        sessions_seen.add(session_id)

        produce = w["produce"]

        try:
            neto = int(w["neto"])
        except (ValueError, TypeError):
            continue

        if produce not in product_stats:
            product_stats[produce] = {"total_kg": 0, "session_count": 0}

        product_stats[produce]["total_kg"] += neto
        product_stats[produce]["session_count"] += 1

    rates_query = Rate.query.filter_by(scope=provider.id).all()
    rates_map = {r.product_id: r.rate for r in rates_query}

    result_products = []
    grand_total = 0

    for product_id, stats in product_stats.items():
        rate = rates_map.get(product_id)
        if rate is None:
            raise ValueError(f"No rate configured for product '{product_id}', provider {provider.id}")

        pay = stats["total_kg"] * rate

        result_products.append({
            "product": product_id,
            "count": str(stats["session_count"]),
            "amount": stats["total_kg"],
            "rate": rate,
            "pay": pay
        })
        grand_total += pay

    return {
        "id": str(provider.id),
        "name": provider.name,
        "from": start.strftime("%Y%m%d%H%M%S"),
        "to": end.strftime("%Y%m%d%H%M%S"),
        "truckCount": len(trucks_seen),
        "sessionCount": len(sessions_seen),
        "products": result_products,
        "total": grand_total
    }


# --------------------------------------------------
# Route
# --------------------------------------------------

@bill_bp.route("/bill/<int:provider_id>", methods=["GET"])
def get_bill(provider_id):
    provider = db.session.get(Provider, provider_id)
    if not provider:
        return jsonify({"error": "provider not found"}), 404

    from_param = request.args.get("from")
    to_param = request.args.get("to")

    start, end = resolve_time_range(from_param, to_param)

    if start > end:
        return jsonify({"error": "invalid time range"}), 400

    try:
        bill = generate_bill(provider, start, end)
        return jsonify(bill)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({
            "error": "billing failed",
            "details": str(e)
        }), 500