from flask import Flask
from views import *
import os
from dotenv import load_dotenv

load_dotenv()

app=Flask(__name__)
# ____________________________________________________________
# all routes

# health check
@app.route("/health")
def health():
    return {"status": "UP"},200


# ____________________________________________________________
# named as __main__
if __name__=="__main__":

    app.run(debug=True,host='0.0.0.0', port=5000)


