from flask import Flask

# ____________________________________________________________
# app routes/views
@app.route("/health")
def health():
    return "ok",200



# ____________________________________________________________
# named as __main__
if __name__=="__main__":
    app.run(debug=True)

