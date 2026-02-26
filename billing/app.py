
from flask import Flask,request,jsonify
app=Flask(__name__)
providers = {}#MOCK
import os

app=Flask(__name__)
# ____________________________________________________________
# all routes

# health check
@app.route("/health")
def health():
     return {"status": "UP"},200

@app.route("/provider",methods=["POST"])
def new_provider():
    data=request.get_json()
    provider_name = data.get("name")
    provider_id = next((key for key, name in providers.items() if name == provider_name), None)
    if not provider_name:
        return jsonify({"error": "Provider name is required"}), 400
    if provider_id!=None:
        return jsonify({"message":f"Provider '{provider_name}' is already exist"}),400
    provider_id=len(providers)+1+10000#starting number is 10000
    providers[provider_id]=provider_name
    return jsonify({"id":provider_id}),201
    
# ____________________________________________________________
# named as __main__
if __name__=="__main__":
    app.run(debug=True,host='0.0.0.0', port=5000)


