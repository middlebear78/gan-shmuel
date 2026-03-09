from flask import Blueprint, request, jsonify
import os
from openpyxl import load_workbook
from models import db, Provider, Rate

rates_bp = Blueprint("rates_bp", __name__)

IN_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "in")


def _normalize_scope(scope_raw: str) -> str:
    s = (scope_raw or "").strip()
    if not s:
        raise ValueError("Scope is required")

    if s.upper() == "ALL":
        return "ALL"

    # must be provider id
    if not s.isdigit():
        raise ValueError(f"Scope must be 'ALL' or provider id. Got '{s}'")

    provider_id = int(s)
    if Provider.query.get(provider_id) is None:
        raise ValueError(f"Provider id in Scope does not exist: {provider_id}")

    return str(provider_id)


def _read_rates_excel(filename: str):
    safe_name = os.path.basename(filename)
    path = os.path.join(IN_DIR, safe_name)

    if not os.path.exists(path):
        raise FileNotFoundError(f"file not found in /in: {safe_name}")

    wb = load_workbook(path, data_only=True)
    ws = wb.active

    # read header row
    header = []
    for cell in ws[1]:
        header.append(str(cell.value).strip() if cell.value is not None else "")

    col_idx = {name: i for i, name in enumerate(header)}
    required = ["Product", "Rate", "Scope"]
    for col in required:
        if col not in col_idx:
            raise ValueError(f"missing column '{col}' in excel")

    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        product = r[col_idx["Product"]]
        rate_val = r[col_idx["Rate"]]
        scope = r[col_idx["Scope"]]

        product = str(product).strip() if product is not None else ""
        if not product:
            continue  # skip empty rows

        try:
            rate_int = int(rate_val)
        except Exception:
            raise ValueError(f"invalid Rate for product '{product}'")

        if rate_int < 0:
            raise ValueError(f"Rate must be non-negative for product '{product}'")

        scope_norm = _normalize_scope(str(scope) if scope is not None else "")

        rows.append({"product_id": product, "rate": rate_int, "scope": scope_norm})

    if not rows:
        raise ValueError("No valid rate rows found in excel")

    return rows, safe_name


@rates_bp.route("/rates", methods=["POST"])
def post_rates():
    """
    Spec: file= Will upload new rates from an excel file in "/in" folder.
    Columns: Product, Rate (integer agorot), Scope (ALL or provider id).
    New rates overwrite old ones (by product_id+scope).
    """
    data = request.get_json(silent=True) or {}
    filename = data.get("file") or request.form.get("file")

    if not filename:
        return jsonify({"error": "file is required (name of excel file in /in)"}), 400

    try:
        rows, safe_name = _read_rates_excel(filename)

        inserted = 0
        updated = 0

        for row in rows:
            existing = Rate.query.filter_by(
                product_id=row["product_id"],
                scope=row["scope"]
            ).first()

            if existing:
                if existing.rate != row["rate"]:
                    existing.rate = row["rate"]
                    updated += 1
            else:
                db.session.add(Rate(
                    product_id=row["product_id"],
                    scope=row["scope"],
                    rate=row["rate"]
                ))
                inserted += 1

        db.session.commit()

        return jsonify({
            "status": "OK",
            "file": safe_name,
            "rows": len(rows),
            "inserted": inserted,
            "updated": updated
        }), 200

    except FileNotFoundError as e:
        return jsonify({"error": "file not found", "details": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": "bad input", "details": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "server error", "details": str(e)}), 500