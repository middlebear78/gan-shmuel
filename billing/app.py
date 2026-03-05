from flask import Flask, request, jsonify
from models import Provider,db,Truck, Rate
from sqlalchemy import text
from config import Config

app=Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# ____________________________________________________________
# all routes

# health check
@app.route("/health")
def health():
    try:
        # run lightweight DB check
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "OK",}), 200

    except Exception as e:
        return jsonify({"status": "Failure", "error": str(e)}), 500

# POST /provider
@app.route("/provider",methods=["POST"])
def new_provider():
    data = request.get_json()
    provider_name = data.get('name')
    if not provider_name:
        return jsonify({"error": "Provider name is required"}), 400
    if Provider.query.filter_by(name=provider_name).first()!=None:
        return jsonify({"message":f"Provider '{provider_name}' is already exist"}),409
    new_provider = Provider(name=provider_name)
    db.session.add(new_provider)
    db.session.commit()
    return jsonify({"id": str(new_provider.id)}), 201

# PUT /provider
@app.put("/provider/<int:provider_id>")
def update_provider(provider_id):

    data = request.get_json(silent=True) or {}
    new_name = (data.get("name") or "").strip()

    if not new_name:
        return jsonify({"error": "name is required"}), 400

    # check provider exists
    provider = Provider.query.get(provider_id)
    if not provider:
        return jsonify({"error": "provider not found"}), 404

    # enforce unique name
    existing = Provider.query.filter(
        Provider.name.ilike(new_name),
        Provider.id != provider_id
    ).first()

    if existing:
        return jsonify({"error": "provider name must be unique"}), 409

    # update
    provider.name = new_name
    db.session.commit()

    return jsonify({
        "id": provider.id,
        "name": provider.name
    }), 200


# ____________________________________________________________
# named as __main__
if __name__=="__main__":
    app.run(debug=True,host='0.0.0.0', port=5000)


