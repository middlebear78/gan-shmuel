from flask import Flask, request, jsonify
from models import db, Provider, Truck, Rate
from sqlalchemy import text
from config import Config

# routes Imports
from routes.provider_routes import provider_bp
from routes.healthCheck_route import health_bp

app=Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# ____________________________________________________________
# all Blueprints
app.register_blueprint(health_bp)

app.register_blueprint(provider_bp)


# ____________________________________________________________
# named as __main__
if __name__=="__main__":
    app.run(debug=True,host='0.0.0.0', port=5000)


