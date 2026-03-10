from flask import Blueprint, request, jsonify
from datetime import datetime
from models import db, Provider, Truck, Rate

# requests is used to call the external weight microservice over HTTP
# os.getenv reads the weight service URL from environment variables
import requests
import os

WEIGHT_API = os.getenv("WEIGHT_SERVER_URL")

bill_bp = Blueprint("bill", __name__)

# ----------------------------------------------------------------------------------
#                  _____ Helper functions _____
# || parse_timestamp || resolve_time_range || get_provider_trucks ||
# ----------------------------------------------------------------------------------
def parse_timestamp(timeStamp_string):
    try:
        return datetime.strptime(timeStamp_string, "%Y%m%d%H%M%S")
    except Exception:
        return None

# "from" default to the 1st of this month, "to" to right now
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

    # return both so the caller can unpack them
    return start, end

def get_provider_trucks(provider_id):
    trucks = Truck.query.filter_by(provider_id=provider_id).all()
    # extract just the id from each Truck object into a flat list
    return [truck.id for truck in trucks]

# calls the weight microservice's GET /weight endpoint to get all completed
# weighing transactions ("out" direction) within the given time window
def fetch_weights(start, end):

    params = {
        # format datetimes back into the "yyyymmddhhmmss" string format
        "from": start.strftime("%Y%m%d%H%M%S"),
        "to": end.strftime("%Y%m%d%H%M%S"),
        "filter": "out",
    }

    # make the HTTP GET call to the weight service
    response = requests.get(f"{WEIGHT_API}/weight", params=params)

    if response.status_code != 200:
        raise Exception("weight service error")

    # parse the JSON array of weight records and return it
    #   "id": t.id,
    #   "direction": t.direction,
    #   "truck": t.truck,
    #   "bruto": t.bruto,
    #   "neto": t.neto / "na",
    #   "produce": t.produce,
    #   "containers": containers
    return response.json()

# ----------------------------------------------------------------------------------
#   the core billing logic
# ----------------------------------------------------------------------------------
def generate_bill(provider, start, end):
    # get all truck IDs for this provider as a set (for fast "in" lookups)
    provider_trucks = set(get_provider_trucks(provider.id))
    # fetch all "out" weight records from the weight service for this time window
    weights = fetch_weights(start, end)

    # dict to accumulate total_kg and session_count per product (e.g. "oranges")
    product_stats = {}
    trucks_seen = set()
    sessions_seen = set()

    # loop through every weight record returned by the weight service
    for weight in weights:
        # if neto is "na", the container tara wasn't known yet so we can't bill
        if weight["neto"] == "na":
            continue

        # the weight service includes "truck" in each record, so we read it
        # directly — this avoids an extra HTTP call to GET /session/<id>
        truck_id = weight.get("truck")                                              #TODO check if truck returns id, or somthing else
        # skip this record if the truck doesn't belong to our provider
        if truck_id not in provider_trucks:
            continue

        trucks_seen.add(truck_id)
        # track the session (weight record) ID for the count
        sessions_seen.add(weight["id"])

        # which product was on this truck (e.g. "oranges", "tomatoes")
        produce = weight["produce"]

        try:
            # neto comes as an int or string — cast it to int for math
            neto = int(weight["neto"])
        except (ValueError, TypeError):
            # if neto is somehow not a valid number, skip this record
            continue

        # if this is the first time we see this product, initialize its stats
        if produce not in product_stats:
            product_stats[produce] = {"total_kg": 0, "session_count": 0}

        # add this transaction's neto weight to the product's running total
        product_stats[produce]["total_kg"] += neto
        # bump the session count for this product
        product_stats[produce]["session_count"] += 1

    # now look up the billing rates — each Rate row maps a product to a price per kg
    # scoped to this provider's ID
    rates_query = Rate.query.filter_by(scope=provider.id).all()
    # turn the list of Rate objects into a dict: {"oranges": 5, "tomatoes": 3, ...}
    rates_map = {r.product_id: r.rate for r in rates_query}

    # build the list of product line items for the response
    result_products = []
    # running total across all products
    grand_total = 0

    # for each product that had weight data, calculate the pay
    for product_id, stats in product_stats.items():
        # look up the rate (price per kg) for this product
        rate = rates_map.get(product_id)
        # if there's no rate configured, we can't bill — raise so the route returns 422
        if rate is None:
            raise ValueError(
                f"No rate configured for product '{product_id}', provider {provider.id}"
            )

        # pay = total kilograms * rate per kg
        pay = stats["total_kg"] * rate

        # add this product's line item to the response
        result_products.append(
            {
                "product": product_id,  # the product name
                "count": str(
                    stats["session_count"]
                ),  # how many sessions carried this product
                "amount": stats["total_kg"],  # total kg for this product
                "rate": rate,  # price per kg
                "pay": pay,  # total pay for this product
            }
        )
        # add this product's pay to the grand total
        grand_total += pay

    # return the full bill as a dict — flask will jsonify it in the route
    return {
        "id": str(provider.id),  # provider ID as a string
        "name": provider.name,  # provider display name
        "from": start.strftime("%Y%m%d%H%M%S"),  # start of billing window
        "to": end.strftime("%Y%m%d%H%M%S"),  # end of billing window
        "truckCount": len(trucks_seen),  # how many unique trucks
        "sessionCount": len(sessions_seen),  # how many weighing sessions
        "products": result_products,  # per-product breakdown
        "total": grand_total,  # total pay across all products
    }


# the actual HTTP endpoint — GET /bill/<provider_id>?from=...&to=...
# returns a JSON billing summary for the given provider in the given time range
@bill_bp.route("/bill/<int:provider_id>", methods=["GET"])
def get_bill(provider_id):
    # look up the provider by primary key in the database
    provider = db.session.get(Provider, provider_id)
    # if no provider with this ID exists, rEturn 404
    if not provider:
        return jsonify({"error": "provider not found"}), 404

    # read optional query params "from" and "to" from the      URL
    from_param = request.args.get("from")
    to_param = request.args.get("to")

    # resolve the time range — fills in defaults if params are missing
    start, end = resolve_time_range(from_param, to_param)

    # sanity check: "from" must be before "to"
    if start > end:
        return jsonify({"error": "invalid time range"}), 400

    try:
        # run the billing logic and return the result as JSON
        bill = generate_bill(provider, start, end)
        return jsonify(bill)
    except ValueError as e:
        # ValueError means a missing rate — return 422 (unprocessable)
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        # any other error (e.g. weight service down) — return 500
        return jsonify({"error": "billing failed", "details": str(e)}), 500
