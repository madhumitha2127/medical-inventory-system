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
    alerts = get_alerts()
    return render_template("dashboard.html",
        user=session["user"],
        role=session["role"],
        alerts=alerts)      
@app.route("/billing")
def billing():
    if "user" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    medicines = conn.execute("SELECT * FROM medicines WHERE quantity > 0").fetchall()
    conn.close()
    cart = session.get("cart", [])
    cart_total = sum(item["total"] for item in cart)
    return render_template("billing.html", medicines=medicines, cart=cart, cart_total=cart_total)
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    if "cart" not in session:
        session["cart"] = []
    med_id = request.form["medicine_id"]
    qty = int(request.form["quantity"])
    conn = get_db()
    med = conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()
    conn.close()
    cart = session["cart"]
    cart.append({
        "id": med["id"],
        "name": med["name"],
        "qty": qty,
        "price": med["price"],
        "total": med["price"] * qty,
        "usage": med["usage"] or "N/A",
        "restrictions": med["restrictions"] or "N/A"
    })
    session["cart"] = cart
    return redirect(url_for("billing"))

@app.route("/clear_cart")
def clear_cart():
    session.pop("cart", None)
    return redirect(url_for("billing"))
@app.route("/checkout", methods=["POST"])
def checkout():
    cart = session.get("cart", [])
    if not cart:
        return redirect(url_for("billing"))
    
    conn = get_db()
    for item in cart:
        conn.execute("UPDATE medicines SET quantity = quantity - ? WHERE id=?", 
                     (item["qty"], item["id"]))
        conn.execute("INSERT INTO sales (medicine_name, quantity_sold, total_price, sold_by) VALUES (?,?,?,?)",
                     (item["name"], item["qty"], item["total"], session["user"]))
    conn.commit()
    conn.close()

    import qrcode, base64, io
    cart_total = sum(item["total"] for item in cart)
    
    qr_text = "MEDITRACK BILL\n"
    qr_text += "================\n"
    for item in cart:
        google = "https://www.google.com/search?q=" + item["name"].replace(" ", "+") + "+medicine+usage"
        qr_text += f"{item['name']} x{item['qty']} = Rs.{item['total']}\n"
        qr_text += f"Usage: {item['usage']}\n"
        qr_text += f"Restrictions: {item['restrictions']}\n"
        qr_text += f"Info: {google}\n\n"
    qr_text += f"TOTAL: Rs.{cart_total}"

    qr = qrcode.make(qr_text)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    session["last_bill"] = {
        "cart": cart,
        "total": cart_total,
        "seller": session["user"],
        "qr": qr_base64
    }
    session.pop("cart", None)
    return redirect(url_for("invoice"))
@app.route("/sell", methods=["POST"])
def sell():
    med_id = request.form["medicine_id"]
    qty_sold = int(request.form["quantity"])
    conn = get_db()
    med = conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()
    total = med["price"] * qty_sold

    conn.execute("UPDATE medicines SET quantity = quantity - ? WHERE id=?", (qty_sold, med_id))
    conn.execute("INSERT INTO sales (medicine_name, quantity_sold, total_price, sold_by) VALUES (?,?,?,?)",
                 (med["name"], qty_sold, total, session["user"]))
    conn.commit()
    conn.close()

    import qrcode, base64, io
    google_link = "https://www.google.com/search?q=" + med["name"].replace(" ", "+") + "+medicine+usage"
    qr_data = f"""
BILL RECEIPT
Medicine: {med['name']}
Qty: {qty_sold}
Price: Rs.{med['price']}
Total: Rs.{total}
Usage: {med['usage'] or 'N/A'}
Restrictions: {med['restrictions'] or 'N/A'}
More Info: {google_link}
"""
    qr = qrcode.make(qr_data)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return redirect(url_for("invoice",
        name=med["name"],
        qty=qty_sold,
        price=med["price"],
        total=total,
        seller=session["user"],
        qr=qr_base64
    ))
@app.route("/invoice")
def invoice():
    from datetime import datetime
    bill = session.get("last_bill", {})
    data = {
        "cart": bill.get("cart", []),
        "total": bill.get("total", 0),
        "seller": bill.get("seller", ""),
        "qr": bill.get("qr", ""),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return render_template("invoice.html", data=data)
def get_alerts():
    conn = get_db()
    alerts = []
    from datetime import date, datetime
    today = date.today()
    medicines = conn.execute("SELECT * FROM medicines").fetchall()
    for med in medicines:
        expiry = datetime.strptime(med["expiry_date"], "%Y-%m-%d").date()
        days_left = (expiry - today).days
        if med["quantity"] < 5:
            alerts.append("⚠️ Low Stock: " + med["name"] + " only " + str(med["quantity"]) + " left!")
        if days_left <= 30 and days_left > 0:
            alerts.append("⏳ Expiring Soon: " + med["name"] + " in " + str(days_left) + " days!")
        if days_left <= 0:
            alerts.append("🚫 Expired: " + med["name"])
    conn.close()
    return alerts
@app.route("/analytics")
def analytics():
    if "user" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    total_revenue = conn.execute("SELECT SUM(total_price) FROM sales").fetchone()[0] or 0
    total_sold = conn.execute("SELECT SUM(quantity_sold) FROM sales").fetchone()[0] or 0
    top_medicines = conn.execute("""
        SELECT medicine_name, SUM(quantity_sold) as total_qty
        FROM sales GROUP BY medicine_name ORDER BY total_qty DESC LIMIT 5
    """).fetchall()
    conn.close()
    top_labels = [r["medicine_name"] for r in top_medicines]
    top_values = [r["total_qty"] for r in top_medicines]
    return render_template("analytics.html",
        total_revenue=round(total_revenue, 2),
        total_sold=total_sold,
        top_labels=top_labels,
        top_values=top_values
    )


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
    usage = request.form["usage"]
    restrictions = request.form["restrictions"]
    conn = get_db()
    conn.execute("INSERT INTO medicines (name, quantity, price, expiry_date, usage, restrictions) VALUES (?,?,?,?,?,?)",
                 (name, quantity, price, expiry_date, usage, restrictions))
    conn.commit()
    conn.close()
    return redirect(url_for("inventory"))
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
if __name__ == "__main__":
    app.run(debug=True)