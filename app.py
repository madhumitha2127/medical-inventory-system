from flask import Flask, render_template, request, redirect, url_for, session
from database import get_db
app = Flask(__name__)
app.secret_key = "meditrack123"

users = {
    "admin": {"password": "admin123", "role": "admin"},
    "staff1": {"password": "staff123", "role": "staff"}
}

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username]["password"] == password:
            session["user"] = username
            session["role"] = users[username]["role"]
            return redirect(url_for("dashboard"))
        else:
            error = "Wrong username or password!"
    return render_template("login.html", error=error)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html",
        user=session["user"],
        role=session["role"])
@app.route("/billing")
def billing():
    if "user" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    medicines = conn.execute("SELECT * FROM medicines WHERE quantity > 0").fetchall()
    conn.close()
    return render_template("billing.html", medicines=medicines)

@app.route("/sell", methods=["POST"])
def sell():
    med_id = request.form["medicine_id"]
    qty_sold = int(request.form["quantity"])
    conn = get_db()
    med = conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()
    total = med["price"] * qty_sold
    conn.execute("UPDATE medicines SET quantity = quantity - ? WHERE id=?", (qty_sold, med_id))
    conn.commit()
    conn.close()
    return "Sold! Total: Rs." + str(total)
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
@app.route("/inventory")
def inventory():
    if "user" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    medicines = conn.execute("SELECT * FROM medicines").fetchall()
    conn.close()
    return render_template("inventory.html", medicines=medicines)

@app.route("/add_medicine", methods=["POST"])
def add_medicine():
    name = request.form["name"]
    quantity = request.form["quantity"]
    price = request.form["price"]
    expiry_date = request.form["expiry_date"]
    conn = get_db()
    conn.execute("INSERT INTO medicines (name, quantity, price, expiry_date) VALUES (?,?,?,?)",
                 (name, quantity, price, expiry_date))
    conn.commit()
    conn.close()
    return redirect(url_for("inventory"))
if __name__ == "__main__":
    app.run(debug=True)