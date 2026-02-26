from flask import Flask, Response

app = Flask(__name__)

@app.get("/health")
def health():
    return Response("OK", status=200, mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
