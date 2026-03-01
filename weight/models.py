from database import db

class ContainerRegistered(db.Model):

    __tablename__ = "containers_registered"
    
    container_id = db.Column(db.String(15), primary_key=True)
    weight = db.Column(db.Integer, nullable=True)
    unit = db.Column(db.String(10), nullable=True)

class Transaction(db.Model):

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=True)
    direction = db.Column(db.String(10), nullable=True)
    truck = db.Column(db.String(50), nullable=True)
    containers = db.Column(db.String(10000), nullable=True)
    bruto = db.Column(db.Integer, nullable=True)
    truckTara = db.Column(db.Integer, nullable=True)
    neto = db.Column(db.Integer, nullable=True)
    produce = db.Column(db.String(50), nullable=True)
    session_id = db.Column(db.Integer, nullable=True)
