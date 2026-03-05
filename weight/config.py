import os

DB_HOST = os.environ.get("DB_HOSTNAME", "localhost")
DB_NAME = os.environ.get("DB_NAME", "weight")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")