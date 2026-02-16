from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from inventory import load_tablets, add_tablet
from billing import sell_tablet_logic
from billing import get_all_bills

app = Flask(__name__, static_folder="static")

CORS(app)
from billing import sales_analytics_data

@app.route("/sales", methods=["GET"])
def get_sales():
    return jsonify(sales_analytics_data())

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/tablets", methods=["GET"])
def get_tablets():
    return jsonify(load_tablets())

@app.route("/add-tablet", methods=["POST"])
def add_tablet_api():
    data = request.json
    result = add_tablet(
        data["name"],
        data["qty"],
        data["expiry"]
    )
    return jsonify(result)
@app.route("/sell-tablet", methods=["POST"])
def sell_tablet_api():
    data = request.json
    result = sell_tablet_logic(
        data["name"],
        data["qty"],
        data["price"]
    )
    return jsonify(result)
from billing import get_all_bills

@app.route("/bills", methods=["GET"])
def get_bills():
    return jsonify(get_all_bills())

@app.route("/bills", methods=["GET"])
def bills_api():
    return jsonify(get_all_bills())
from billing import get_all_bills

@app.route("/bills", methods=["GET"])
def fetch_bills():
    return jsonify(get_all_bills())
@app.route("/alerts", methods=["GET"])
def get_alerts():

    tablets = load_tablets()

    expired = []
    out_of_stock = []

    for t in tablets:

        if t["status"] == "EXPIRED":
            expired.append(t["name"])

        if int(t["qty"]) == 0:
            out_of_stock.append(t["name"])

    return jsonify({
        "expired": expired,
        "out_of_stock": out_of_stock
    })

if __name__ == "__main__":
    app.run(debug=True)
