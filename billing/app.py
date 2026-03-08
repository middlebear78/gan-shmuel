from flask import Flask, request, jsonify
from models import db, Provider, Truck, Rate
from config import Config, TestConfig

# routes Imports
from routes.provider_routes import provider_bp
from routes.healthCheck_route import health_bp
from routes.rates_route import rates_bp
from routes.truck_routes import truck_bp

CONFIGS = {
    "Config": Config,
    "TestConfig": TestConfig,
}

def create_app(config_name="Config"):
    app = Flask(__name__)
    app.config.from_object(CONFIGS[config_name])
    db.init_app(app)

    # all Blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(provider_bp)
    app.register_blueprint(rates_bp)
    app.register_blueprint(truck_bp)

    return app

# named as __main__
if __name__=="__main__":
    app = create_app()
    app.run(debug=True,host='0.0.0.0', port=5000)


