from flask import Flask, jsonify, request
from inventory import load_tablets

# 1️⃣ Create Flask app FIRST
app = Flask(__name__)

# 2️⃣ Home route
@app.route("/")
def home():
    return jsonify({"message": "Medical Inventory API is running"})

# 3️⃣ View all tablets API
from inventory import add_tablet

@app.route("/add-tablet", methods=["POST"])
def add_tablet_api():
    data = request.json
    name = data["name"]
    qty = data["qty"]
    expiry = data["expiry"]

    add_tablet(name, qty, expiry)
    return jsonify({"message": "Tablet added successfully"})

from billing import sell_tablet_logic

@app.route("/sell-tablet", methods=["POST"])
def sell_tablet_api():
    data = request.json
    result = sell_tablet_logic(
        data["name"],
        data["qty"],
        data["price"]
    )
    return jsonify(result)
from inventory import get_blocked_tablets

@app.route("/blocked-tablets", methods=["GET"])
def blocked_tablets_api():
    return jsonify(get_blocked_tablets())

# 4️⃣ Run server
if __name__ == "__main__":
    app.run(debug=True)
