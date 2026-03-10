from flask import Flask, send_from_directory, request, Response
import os
import requests as http_client

app = Flask(__name__, static_folder="static")

WEIGHT_URL = os.environ.get("WEIGHT_URL", "http://weight-app:5000")
BILLING_URL = os.environ.get("BILLING_URL", "http://billing-app:5000")


def proxy(upstream_url):
    url = f"{upstream_url}?{request.query_string.decode()}" if request.query_string else upstream_url
    resp = http_client.request(
        method=request.method,
        url=url,
        headers={k: v for k, v in request.headers if k.lower() != "host"},
        data=request.get_data(),
        allow_redirects=False,
    )
    return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type"))


@app.route("/api/weight/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_weight(path):
    return proxy(f"{WEIGHT_URL}/{path}")


@app.route("/api/billing/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_billing(path):
    return proxy(f"{BILLING_URL}/{path}")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
