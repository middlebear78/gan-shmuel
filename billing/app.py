from flask import Flask

app=Flask(__name__)

# ____________________________________________________________
# app routes/views
@app.route("/health")
def health():
    return "ok",200



# ____________________________________________________________
# named as __main__
if __name__=="__main__":

    app.run(debug=True,host='0.0.0.0', port=5000)


