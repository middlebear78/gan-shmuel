# flask Blueprint lets us define routes in a separate file and register them on the app
from flask import Blueprint, request, jsonify

# datetime for parsing and formatting the timestamp strings
from datetime import datetime

# requests is used to call the external weight microservice over HTTP
import requests

# os.getenv reads the weight service URL from environment variables
import os

# import the SQLAlchemy db instance and the three models we need:
# Provider — the company we're billing
# Truck — each truck is linked to a provider
# Rate — price per kg for each product, scoped to a provider
from models import db, Provider, Truck, Rate

# read the weight service base URL from env (e.g. "http://weight:5000")
WEIGHT_API = os.getenv("WEIGHT_SERVER_URL")

# create a blueprint so this route file can be registered on the flask app
bill_bp = Blueprint("bill", __name__)


# takes a string like "20250315143000" and turns it into a python datetime
# returns None if the string is garbage or doesn't match the expected format
def parse_timestamp(timeStamp_string):
    try:
        # strptime parses the string using the exact "yyyymmddhhmmss" format
        return datetime.strptime(timeStamp_string, "%Y%m%d%H%M%S")
    except Exception:
        # if anything goes wrong (wrong length, letters, etc.) just return None
        return None


# determines the start and end datetimes for the billing window
# if the caller didn't provide "from", we default to the 1st of this month at midnight
# if the caller didn't provide "to", we default to right now
def resolve_time_range(from_timeStamp, to_timeStamp):
    # capture the current moment so both defaults are consistent
    now = datetime.now()

    if from_timeStamp:
        # caller gave us a "from" string — try to parse it
        start = parse_timestamp(from_timeStamp)
    else:
        # no "from" provided — default to the first day of the current month at 00:00:00
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if to_timeStamp:
        # caller gave us a "to" string — try to parse it
        end = parse_timestamp(to_timeStamp)
    else:
        # no "to" provided — default to right now
        end = now

    # return both as a tuple so the caller can unpack them
    return start, end


# queries the database for all trucks that belong to the given provider
# returns a plain list of truck ID strings (e.g. ["T-001", "T-002"])
def get_provider_trucks(provider_id):
    # filter_by matches on the foreign key column, .all() returns a list of Truck objects
    trucks = Truck.query.filter_by(provider_id=provider_id).all()
    # extract just the id from each Truck object into a flat list
    return [truck.id for truck in trucks]


# calls the weight microservice's GET /weight endpoint to get all completed
# weighing transactions ("out" direction) within the given time window
# raises an Exception if the weight service returns a non-200 status
def fetch_weights(start, end):
    # build the query params the weight service expects
    params = {
        # format datetimes back into the "yyyymmddhhmmss" string format
        "from": start.strftime("%Y%m%d%H%M%S"),
        "to": end.strftime("%Y%m%d%H%M%S"),
        # we only care about completed weighings (truck weighed out)
        "filter": "out",
    }

    # make the HTTP GET call to the weight service
    response = requests.get(f"{WEIGHT_API}/weight", params=params)

    # if the weight service is down or returns an error, blow up
    # the caller (get_bill) will catch this and return a 500
    if response.status_code != 200:
        raise Exception("weight service error")

    # parse the JSON array of weight records and return it
    return response.json()


# this is the core billing logic — it takes a provider and a time window,
# fetches all weight records, filters to only this provider's trucks,
# groups the neto weights by product, looks up the rate for each product,
# and calculates the total pay
def generate_bill(provider, start, end):
    # get all truck IDs for this provider as a set (for fast "in" lookups)
    provider_trucks = set(get_provider_trucks(provider.id))
    # fetch all "out" weight records from the weight service for this time window
    weights = fetch_weights(start, end)

    # dict to accumulate total_kg and session_count per product (e.g. "oranges")
    product_stats = {}
    # track unique trucks that appeared in at least one transaction
    trucks_seen = set()
    # track unique session IDs that were counted
    sessions_seen = set()

    # loop through every weight record returned by the weight service
    for w in weights:
        # if neto is "na", the container tara wasn't known yet so we can't bill
        if w["neto"] == "na":
            continue

        # the weight service includes "truck" in each record, so we read it
        # directly — this avoids an extra HTTP call to GET /session/<id>
        truck_id = w.get("truck")
        # skip this record if the truck doesn't belong to our provider
        if truck_id not in provider_trucks:
            continue

        # this truck contributed to the bill — remember it
        trucks_seen.add(truck_id)
        # track the session (weight record) ID for the count
        sessions_seen.add(w["id"])

        # which product was on this truck (e.g. "oranges", "tomatoes")
        produce = w["produce"]

        try:
            # neto comes as an int or string — cast it to int for math
            neto = int(w["neto"])
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
