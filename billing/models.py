from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
class Provider(db.Model):
    __tablename__ = 'Provider'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    trucks = db.relationship('Truck', backref='provider', lazy=True)
    def __init__(self, name):
        self.name = name
        
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }

class Truck(db.Model):
    __tablename__ = 'Trucks'
    id = db.Column(db.String(10), primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('Provider.id'), nullable=False)
    def to_dict(self):
        return {
            "id": self.id,
            "provider_id": self.provider_id
        }

class Rate(db.Model):
    __tablename__ = 'Rates'
    product_id = db.Column(db.String(50), primary_key=True)
    scope = db.Column(db.String(50), primary_key=True)
    rate = db.Column(db.Integer, nullable=False, default=0)
    def to_dict(self):
        return {
            "product_id": self.product_id,
            "scope": self.scope,
            "rate":self.rate
        }