from flask import Flask
from views import *

app=Flask(__name__)

# ____________________________________________________________
# named as __main__
if __name__=="__main__":
    app.run(debug=True)