from flask import Flask

views=Flask(__name__)

# health check
@views.route("/health")
def health():
    return "ok",200

