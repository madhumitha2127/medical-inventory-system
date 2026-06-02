from flask import Flask, render_template, request, redirect, url_for, session, send_file, abort
from database import get_db
from reportlab.pdfgen import canvas
import io
import os
import secrets
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
# Generate a cryptographically secure secret key if not set in environment
app.secret_key = os.environ.get("SECRET_KEY", "meditrack123_secure_secret_789456")
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB upload limit

import uuid
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    if file and file.filename != "":
        if not allowed_file(file.filename):
            return None, "Invalid file format. Only PNG, JPG, JPEG, and WEBP are allowed."
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        
        # Ensure uploads folder exists securely
        uploads_dir = os.path.join(app.root_path, "static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        image_path = os.path.join("static/uploads", unique_name).replace("\\", "/")
        abs_path = os.path.join(uploads_dir, unique_name)
        file.save(abs_path)
        return image_path, None
    return "", None

# Credentials are now managed dynamically in the SQLite 'users' database table

# Generate a cryptographically secure random session-based CSRF token
def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token)

@app.before_request
def csrf_protect():
    if request.method in ["POST", "PUT", "DELETE"]:
        token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        session_token = session.get("_csrf_token")
        if not session_token or not token or not secrets.compare_digest(session_token, token):
            abort(403, "CSRF token missing or invalid.")

@app.route("/favicon.ico")
def favicon():
    return send_file(os.path.join(app.root_path, "static", "favicon.png"))

@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user_row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user_row and check_password_hash(user_row["password"], password):

            session["user"] = user_row["username"]
            session["role"] = user_row["role"]

            return redirect(url_for("dashboard"))

        else:
            error = "Wrong username or password!"

    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    total_medicines = conn.execute(
        "SELECT COUNT(*) FROM medicines"
    ).fetchone()[0]

    total_revenue = conn.execute(
        "SELECT SUM(total_price) FROM sales"
    ).fetchone()[0] or 0

    total_profit = conn.execute(
        "SELECT SUM(total_price - (quantity_sold * buying_price)) FROM sales"
    ).fetchone()[0] or 0

    total_sold = conn.execute(
        "SELECT SUM(quantity_sold) FROM sales"
    ).fetchone()[0] or 0

    recent_sales = conn.execute(
        "SELECT * FROM sales ORDER BY sold_on DESC LIMIT 5"
    ).fetchall()

    medicines_data = conn.execute("SELECT * FROM medicines").fetchall()
    medicines_list = []
    for r in medicines_data:
        medicines_list.append({
            "name": r["name"],
            "expiry_date": r["expiry_date"],
            "quantity": r["quantity"],
            "price": r["price"]
        })

    conn.close()

    alerts = get_alerts()

    return render_template(
        "dashboard.html",
        user=session["user"],
        role=session["role"],
        alerts=alerts,
        total_medicines=total_medicines,
        total_revenue=round(total_revenue, 2),
        total_profit=round(total_profit, 2),
        total_sold=total_sold,
        recent_sales=recent_sales,
        medicines=medicines_list
    )


@app.route("/billing")
def billing():

    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    medicines = conn.execute(
        "SELECT * FROM medicines WHERE quantity > 0"
    ).fetchall()

    medicines_list = []
    for row in medicines:
        medicines_list.append({
            "id": row["id"],
            "name": row["name"],
            "batch_no": row["batch_no"],
            "dosage_form": row["dosage_form"] or "Tablet",
            "price": row["price"],
            "quantity": row["quantity"],
            "usage": row["dosage"] or "N/A",
            "restrictions": row["restrictions"] or "N/A",
            "image": row["image"] or ""
        })

    conn.close()

    cart = session.get("cart", [])

    cart_total = sum(item["total"] for item in cart)

    return render_template(
        "billing.html",
        medicines=medicines_list,
        cart=cart,
        cart_total=cart_total
    )


@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():

    if "cart" not in session:
        session["cart"] = []

    med_id = request.form["medicine_id"]
    qty = int(request.form["quantity"])

    conn = get_db()

    med = conn.execute(
        "SELECT * FROM medicines WHERE id=?",
        (med_id,)
    ).fetchone()

    if not med:
        conn.close()
        return "❌ Error: Medicine not found!", 404

    # Expiry verification
    from datetime import datetime, date
    try:
        expiry = datetime.strptime(med["expiry_date"], "%Y-%m-%d").date()
        if expiry <= date.today():
            conn.close()
            return f"❌ Error: Cannot sell expired medicine '{med['name']}'!", 400
    except ValueError:
        conn.close()
        return "❌ Error: Invalid expiry date in database!", 400

    if qty > med["quantity"]:

      conn.close()

      return f"""
    ❌ Error:
    Only {med['quantity']} items available in stock!
    """
    if qty <= 0:

      conn.close()

      return "❌ Error: Quantity must be greater than 0!"
    conn.close()

    cart = session["cart"]

    cart.append({
        "id": med["id"],
        "name": med["name"],
        "qty": qty,
        "price": med["price"],
        "total": med["price"] * qty,
        "dosage": med["dosage"] or "N/A",
        "restrictions": med["restrictions"] or "N/A",
        "side_effects": med["side_effects"] or "N/A",
        "expiry_date": med["expiry_date"] or "N/A"
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

    patient_name = request.form.get("patient_name", "Walk-in Patient")
    patient_phone = request.form.get("patient_phone", "N/A")
    try:
        patient_age = int(request.form.get("patient_age", 0))
    except ValueError:
        patient_age = 0
    patient_gender = request.form.get("patient_gender", "Male")
    doctor_name = request.form.get("doctor_name", "Generic Self")
    prescription_id = request.form.get("prescription_id", "N/A")
    payment_method = request.form.get("payment_method", "Cash")
    try:
        discount_rate = float(request.form.get("discount_rate", 0))
    except ValueError:
        discount_rate = 0.0

    conn = get_db()

    # Pre-verify and snapshot buying price to protect transaction integrity
    snapshots = {}
    for item in cart:
        med = conn.execute("SELECT quantity, buying_price FROM medicines WHERE id=?", (item["id"],)).fetchone()
        if not med:
            conn.close()
            return f"❌ Error: Medicine '{item['name']}' no longer exists in database!", 400
        if med["quantity"] < item["qty"]:
            conn.close()
            return f"❌ Error: Not enough stock for '{item['name']}'. Only {med['quantity']} units left!", 400
        snapshots[item["id"]] = med["buying_price"] or round(item["price"] * 0.7, 2)

    # Calculate financial details
    subtotal = sum(item["total"] for item in cart)
    discount_amount = subtotal * (discount_rate / 100.0)
    taxable_subtotal = subtotal - discount_amount
    tax_rate = 12.0 # 6% CGST + 6% SGST
    tax_amount = taxable_subtotal * 0.12
    grand_total = taxable_subtotal + tax_amount

    import random
    invoice_no = f"INV-26-{random.randint(10000, 99999)}"

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO invoices
        (invoice_no, patient_name, patient_age, patient_gender, patient_phone, doctor_name, prescription_id, payment_method, discount_rate, discount_amount, tax_rate, tax_amount, subtotal, grand_total, sold_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice_no,
        patient_name,
        patient_age,
        patient_gender,
        patient_phone,
        doctor_name,
        prescription_id,
        payment_method,
        discount_rate,
        discount_amount,
        tax_rate,
        tax_amount,
        subtotal,
        grand_total,
        session["user"]
    ))
    invoice_id = cursor.lastrowid

    for item in cart:

        conn.execute(
            "UPDATE medicines SET quantity = quantity - ? WHERE id=?",
            (item["qty"], item["id"])
        )

        conn.execute(
            """
            INSERT INTO sales
            (medicine_name, quantity_sold, buying_price, total_price, sold_by, invoice_id)
            VALUES (?,?,?,?,?,?)
            """,
            (
                item["name"],
                item["qty"],
                snapshots[item["id"]],
                item["total"],
                session["user"],
                invoice_id
            )
        )

    conn.commit()
    conn.close()

    import qrcode
    import base64

    qr_text = f"""MEDITRACK RETAIL INVOICE: {invoice_no}
Patient: {patient_name} (Age: {patient_age}, {patient_gender})
Phone: {patient_phone}
Doctor: {doctor_name} | Rx ID: {prescription_id}
Payment: {payment_method}
==================================
"""
    for item in cart:
        google = "https://www.google.com/search?q=" + item["name"].replace(" ", "+") + "+medicine"
        qr_text += f"- Medicine: {item['name']}\n"
        qr_text += f"  Qty: {item['qty']} (Rate: Rs.{item['price']})\n"
        qr_text += f"  Expiry Date: {item.get('expiry_date', 'N/A')}\n"
        qr_text += f"  Dosage: {item.get('dosage', 'N/A')}\n"
        qr_text += f"  Restrictions: {item.get('restrictions', 'N/A')}\n"
        qr_text += f"  Side Effects: {item.get('side_effects', 'N/A')}\n"
        qr_text += f"  Info Link: {google}\n"
        qr_text += "  ----------------\n"
    
    qr_text += f"""==================================
Subtotal: Rs.{round(subtotal, 2)}
Discount ({discount_rate}%): -Rs.{round(discount_amount, 2)}
GST (12% total): +Rs.{round(tax_amount, 2)}
GRAND TOTAL: Rs.{round(grand_total, 2)}
Billed By: {session['user'].upper()}"""

    qr = qrcode.make(qr_text)

    buffer = io.BytesIO()

    qr.save(buffer)

    qr_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode()

    session["last_bill"] = {
        "invoice_id": invoice_id,
        "qr": qr_base64
    }

    session.pop("cart", None)

    return redirect(url_for("invoice"))


@app.route("/invoice")
def invoice():

    bill = session.get("last_bill", {})
    invoice_id = request.args.get("id", type=int)

    if not invoice_id:
        invoice_id = bill.get("invoice_id")

    if not invoice_id:
        return redirect(url_for("billing"))

    conn = get_db()
    invoice = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not invoice:
        conn.close()
        return "❌ Error: Invoice not found!", 404

    sales_items = conn.execute("SELECT * FROM sales WHERE invoice_id=?", (invoice_id,)).fetchall()
    
    data = {
        "id": invoice["id"],
        "invoice_no": invoice["invoice_no"],
        "patient_name": invoice["patient_name"],
        "patient_age": invoice["patient_age"],
        "patient_gender": invoice["patient_gender"],
        "patient_phone": invoice["patient_phone"],
        "doctor_name": invoice["doctor_name"],
        "prescription_id": invoice["prescription_id"],
        "payment_method": invoice["payment_method"],
        "discount_rate": invoice["discount_rate"],
        "discount_amount": invoice["discount_amount"],
        "tax_rate": invoice["tax_rate"],
        "tax_amount": invoice["tax_amount"],
        "subtotal": invoice["subtotal"],
        "total": invoice["grand_total"],
        "seller": invoice["sold_by"],
        "date": invoice["sold_on"],
        "qr": bill.get("qr") if invoice_id == bill.get("invoice_id") else "",
        "cart": []
    }

    for row in sales_items:
        med = conn.execute("SELECT dosage, restrictions, side_effects, expiry_date FROM medicines WHERE name=?", (row["medicine_name"],)).fetchone()
        dosage = med["dosage"] if med else "N/A"
        restrictions = med["restrictions"] if med else "N/A"
        side_effects = med["side_effects"] if med else "N/A"
        expiry_date = med["expiry_date"] if med else "N/A"

        data["cart"].append({
            "name": row["medicine_name"],
            "qty": row["quantity_sold"],
            "price": round(row["total_price"] / row["quantity_sold"], 2) if row["quantity_sold"] > 0 else 0,
            "total": row["total_price"],
            "dosage": dosage,
            "restrictions": restrictions,
            "side_effects": side_effects,
            "expiry_date": expiry_date
        })
    conn.close()

    if not data["qr"]:
        import qrcode
        import base64
        qr_text = f"""MEDITRACK RETAIL INVOICE: {invoice['invoice_no']}
Patient: {invoice['patient_name']} (Age: {invoice['patient_age']}, {invoice['patient_gender']})
Phone: {invoice['patient_phone']}
Doctor: {invoice['doctor_name']} | Rx ID: {invoice['prescription_id']}
Payment: {invoice['payment_method']}
==================================
"""
        for item in data["cart"]:
            google = "https://www.google.com/search?q=" + item["name"].replace(" ", "+") + "+medicine"
            qr_text += f"- Medicine: {item['name']}\n"
            qr_text += f"  Qty: {item['qty']} (Rate: Rs.{item['price']})\n"
            qr_text += f"  Expiry Date: {item.get('expiry_date', 'N/A')}\n"
            qr_text += f"  Dosage: {item.get('dosage', 'N/A')}\n"
            qr_text += f"  Restrictions: {item.get('restrictions', 'N/A')}\n"
            qr_text += f"  Side Effects: {item.get('side_effects', 'N/A')}\n"
            qr_text += f"  Info Link: {google}\n"
            qr_text += "  ----------------\n"
        qr_text += f"""==================================
Subtotal: Rs.{round(invoice['subtotal'], 2)}
Discount ({invoice['discount_rate']}%): -Rs.{round(invoice['discount_amount'], 2)}
GST (12%): +Rs.{round(invoice['tax_amount'], 2)}
GRAND TOTAL: Rs.{round(invoice['grand_total'], 2)}
Billed By: {invoice['sold_by'].upper()}"""

        qr = qrcode.make(qr_text)
        buffer = io.BytesIO()
        qr.save(buffer)
        data["qr"] = base64.b64encode(buffer.getvalue()).decode()

    return render_template("invoice.html", data=data)


@app.route("/download_invoice")
def download_invoice():
    bill = session.get("last_bill", {})
    invoice_id = request.args.get("id", type=int)
    
    if not invoice_id:
        invoice_id = bill.get("invoice_id")
        
    if not invoice_id:
        return redirect(url_for("billing"))

    conn = get_db()
    invoice = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not invoice:
        conn.close()
        return "❌ Error: Invoice not found!", 404
        
    sales_items = conn.execute("SELECT * FROM sales WHERE invoice_id=?", (invoice_id,)).fetchall()
    
    cart = []
    for row in sales_items:
        med = conn.execute("SELECT dosage, restrictions, side_effects, expiry_date FROM medicines WHERE name=?", (row["medicine_name"],)).fetchone()
        dosage = med["dosage"] if med else "N/A"
        restrictions = med["restrictions"] if med else "N/A"
        side_effects = med["side_effects"] if med else "N/A"
        expiry_date = med["expiry_date"] if med else "N/A"
        
        cart.append({
            "name": row["medicine_name"],
            "qty": row["quantity_sold"],
            "price": round(row["total_price"] / row["quantity_sold"], 2) if row["quantity_sold"] > 0 else 0,
            "total": row["total_price"],
            "dosage": dosage,
            "restrictions": restrictions,
            "side_effects": side_effects,
            "expiry_date": expiry_date
        })
    
    conn.close()
    
    import qrcode
    import base64
    from reportlab.lib.utils import ImageReader
    
    qr_text = f"""MEDITRACK RETAIL INVOICE: {invoice['invoice_no']}
Patient: {invoice['patient_name']} (Age: {invoice['patient_age']}, {invoice['patient_gender']})
Phone: {invoice['patient_phone']}
Doctor: {invoice['doctor_name']} | Rx ID: {invoice['prescription_id']}
Payment: {invoice['payment_method']}
==================================
"""
    for item in cart:
        google = "https://www.google.com/search?q=" + item["name"].replace(" ", "+") + "+medicine"
        qr_text += f"- Medicine: {item['name']}\n"
        qr_text += f"  Qty: {item['qty']} (Rate: Rs.{item['price']})\n"
        qr_text += f"  Expiry Date: {item.get('expiry_date', 'N/A')}\n"
        qr_text += f"  Dosage: {item.get('dosage', 'N/A')}\n"
        qr_text += f"  Restrictions: {item.get('restrictions', 'N/A')}\n"
        qr_text += f"  Side Effects: {item.get('side_effects', 'N/A')}\n"
        qr_text += f"  Info Link: {google}\n"
        qr_text += "  ----------------\n"
    qr_text += f"""==================================
Subtotal: Rs.{round(invoice['subtotal'], 2)}
Discount ({invoice['discount_rate']}%): -Rs.{round(invoice['discount_amount'], 2)}
GST (12%): +Rs.{round(invoice['tax_amount'], 2)}
GRAND TOTAL: Rs.{round(invoice['grand_total'], 2)}
Billed By: {invoice['sold_by'].upper()}"""

    qr = qrcode.make(qr_text)
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer)
    qr_buffer.seek(0)
    qr_image = ImageReader(qr_buffer)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    
    # Header block - Dark slate/navy background
    pdf.setFillColorRGB(0.1, 0.1, 0.18)
    pdf.rect(0, 750, 595, 92, fill=True, stroke=False)
    
    # Title
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(40, 790, "MEDITRACK PHARMACY")
    
    # Invoice Label
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(555, 790, "RETAIL INVOICE")
    
    # Reset Fill color to dark gray for texts
    pdf.setFillColorRGB(0.2, 0.2, 0.2)
    
    # Patient Details Block
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, 725, "PATIENT PROFILE")
    pdf.drawString(300, 725, "BILLING DETAILS")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, 710, f"Patient Name: {invoice['patient_name']}")
    pdf.drawString(40, 695, f"Age / Gender: {invoice['patient_age']} Yrs / {invoice['patient_gender']}")
    pdf.drawString(40, 680, f"Phone Number: {invoice['patient_phone']}")
    
    pdf.drawString(300, 710, f"Invoice No: {invoice['invoice_no']}")
    pdf.drawString(300, 695, f"Doctor Name: {invoice['doctor_name'] or 'N/A'}")
    pdf.drawString(300, 680, f"Prescription ID: {invoice['prescription_id'] or 'N/A'}")
    
    pdf.drawString(460, 710, f"Method: {invoice['payment_method']}")
    pdf.drawString(460, 695, f"Billed By: {invoice['sold_by'].upper()}")
    pdf.drawString(460, 680, f"Date: {invoice['sold_on'][:10]}")
    
    # Divider line
    pdf.setStrokeColorRGB(0.85, 0.85, 0.85)
    pdf.setLineWidth(1)
    pdf.line(40, 665, 555, 665)
    
    # Table Header Background
    pdf.setFillColorRGB(0.96, 0.96, 0.98)
    pdf.rect(40, 630, 515, 25, fill=True, stroke=False)
    
    # Table Header text
    pdf.setFillColorRGB(0.3, 0.3, 0.3)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(50, 637, "Medicine Item")
    pdf.drawRightString(350, 637, "Qty")
    pdf.drawRightString(450, 637, "Unit Price")
    pdf.drawRightString(545, 637, "Total")
    
    # Table Content
    y = 605
    pdf.setFont("Helvetica", 9)
    pdf.setFillColorRGB(0.1, 0.1, 0.1)
    
    for item in cart:
        if y < 180:  # Spacing breakout safeguard
            pdf.showPage()
            y = 750
            pdf.setFont("Helvetica", 9)
            
        pdf.drawString(50, y, item["name"])
        pdf.drawRightString(350, y, str(item["qty"]))
        pdf.drawRightString(450, y, f"Rs.{round(item['price'], 2)}")
        pdf.drawRightString(545, y, f"Rs.{round(item['total'], 2)}")
        
        pdf.setStrokeColorRGB(0.93, 0.93, 0.93)
        pdf.setLineWidth(0.5)
        pdf.line(40, y-8, 555, y-8)
        y -= 25
        
    # Totals block
    y -= 10
    pdf.setStrokeColorRGB(0.9, 0.9, 0.9)
    pdf.setLineWidth(1)
    pdf.line(40, y+10, 555, y+10)
    
    pdf.setFillColorRGB(0.3, 0.3, 0.3)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, y - 5, "Subtotal:")
    pdf.drawRightString(545, y - 5, f"Rs. {round(invoice['subtotal'], 2)}")
    
    pdf.drawString(40, y - 20, f"Discount ({invoice['discount_rate']}%):")
    pdf.drawRightString(545, y - 20, f"-Rs. {round(invoice['discount_amount'], 2)}")
    
    pdf.drawString(40, y - 35, "GST Tax (6% CGST + 6% SGST):")
    pdf.drawRightString(545, y - 35, f"+Rs. {round(invoice['tax_amount'], 2)}")
    
    pdf.setStrokeColorRGB(0, 0.78, 0.65) # Teal total line
    pdf.setLineWidth(1.5)
    pdf.line(40, y-45, 555, y-45)
    
    pdf.setFillColorRGB(0, 0.5, 0.4)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y - 60, "GRAND TOTAL:")
    pdf.drawRightString(545, y - 60, f"Rs. {round(invoice['grand_total'], 2)}")
    
    # Draw QR Code on the PDF Receipt
    qr_y = y - 165
    pdf.drawImage(qr_image, 40, qr_y, width=80, height=80)
    
    # QR Explanation text
    pdf.setFillColorRGB(0.1, 0.1, 0.18)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(135, qr_y + 60, "📱 QR Code Medicine Instructions")
    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.drawString(135, qr_y + 45, "This QR code contains detailed dosage recommendations, strict usage")
    pdf.drawString(135, qr_y + 32, "restrictions, and complete digital lookup details for all items.")
    
    # Footer
    pdf.setFillColorRGB(0.6, 0.6, 0.6)
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawCentredString(297, 45, "Thank you for choosing MediTrack Pharmacy! Wish you a healthy recovery.")
    pdf.drawCentredString(297, 30, "This is a computer-generated invoice and requires no physical signature.")
    
    pdf.save()
    buffer.seek(0)
 
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"invoice_{invoice['invoice_no']}.pdf",
        mimetype="application/pdf"
    )

def get_alerts():

    conn = get_db()

    alerts = []

    from datetime import date, datetime

    today = date.today()

    medicines = conn.execute(
        "SELECT * FROM medicines"
    ).fetchall()

    for med in medicines:

        expiry = datetime.strptime(
            med["expiry_date"],
            "%Y-%m-%d"
        ).date()

        days_left = (expiry - today).days

        if med["quantity"] < 5:

            alerts.append(
                "⚠️ Low Stock: "
                + med["name"]
                + " only "
                + str(med["quantity"])
                + " left!"
            )

        if days_left <= 30 and days_left > 0:

            alerts.append(
                "⏳ Expiring Soon: "
                + med["name"]
                + " in "
                + str(days_left)
                + " days!"
            )

        if days_left <= 0:

            alerts.append(
                "🚫 Expired: "
                + med["name"]
            )

    conn.close()

    return alerts
@app.route("/add_medicine", methods=["POST"])
def add_medicine():

    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "❌ Access Denied: Admin role required!", 403

    name = request.form["name"]
    batch_no = request.form["batch_no"]
    try:
        quantity = int(request.form["quantity"])
        buying_price = float(request.form["buying_price"])
        price = float(request.form["price"])
    except ValueError:
        return "❌ Error: Invalid quantity, buying price, or selling price format!", 400

    if quantity <= 0 or buying_price <= 0 or price <= 0:
        return "❌ Error: Quantity, buying price, and selling price must be positive numbers!", 400

    if price < buying_price:
        return "❌ Error: Selling price cannot be lower than buying price (cost price)!", 400

    expiry_date = request.form["expiry_date"]
    from datetime import datetime, date
    try:
        expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        if expiry <= date.today():
            return "❌ Error: Expiry date must be strictly in the future!", 400
    except ValueError:
        return "❌ Error: Invalid expiry date format!", 400

    dosage = request.form["dosage"]
    dosage_form = request.form.get("dosage_form", "Tablet")
    restrictions = request.form["restrictions"]
    side_effects = request.form["side_effects"]
    supplier = request.form["supplier"]

    image = request.files.get("image")

    image_path = ""

    if image and image.filename != "":

        path, err = save_uploaded_file(image)
        if err:
            return f"❌ Error: {err}", 400
        image_path = path

    conn = get_db()

    existing = conn.execute(
        """
        SELECT * FROM medicines
        WHERE name=? AND batch_no=?
        """,
        (name, batch_no)
    ).fetchone()

    if existing:

        conn.close()

        return "❌ Same batch already exists!"

    conn.execute(
        """
        INSERT INTO medicines
        (
            name,
            batch_no,
            quantity,
            buying_price,
            price,
            expiry_date,
            dosage,
            dosage_form,
            restrictions,
            side_effects,
            supplier,
            image
        )

        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            name,
            batch_no,
            quantity,
            buying_price,
            price,
            expiry_date,
            dosage,
            dosage_form,
            restrictions,
            side_effects,
            supplier,
            image_path
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("inventory"))
@app.route("/inventory")
def inventory():

    if "user" not in session:
        return redirect(url_for("login"))

    search = request.args.get("search", "")

    conn = get_db()

    if search:

        medicines = conn.execute("""
            SELECT * FROM medicines
            WHERE name LIKE ?
        """, ('%' + search + '%',)).fetchall()

    else:

        medicines = conn.execute(
            "SELECT * FROM medicines"
        ).fetchall()

    suppliers = conn.execute("SELECT * FROM suppliers").fetchall()
    conn.close()

    from datetime import datetime, date

    today = date.today()

    medicines_with_status = []

    for med in medicines:

        expiry = datetime.strptime(
            med["expiry_date"],
            "%Y-%m-%d"
        ).date()

        days_left = (expiry - today).days

        status = "ok"

        if days_left < 0:
            status = "expired"

        elif days_left <= 30:
            status = "expiring"

        elif med["quantity"] < 5:
            status = "low"

        medicines_with_status.append({
            "data": med,
            "status": status
        })

    return render_template(
        "inventory.html",
        medicines=medicines_with_status,
        suppliers=suppliers,
        user=session["user"],
        role=session["role"]
    )
@app.route("/analytics")
def analytics():

    if "user" not in session:
        return redirect(url_for("login"))

    import json

    conn = get_db()

    total_revenue = conn.execute(
        "SELECT SUM(total_price) FROM sales"
    ).fetchone()[0] or 0

    total_profit = conn.execute(
        "SELECT SUM(total_price - (quantity_sold * buying_price)) FROM sales"
    ).fetchone()[0] or 0

    total_sold = conn.execute(
        "SELECT SUM(quantity_sold) FROM sales"
    ).fetchone()[0] or 0

    top_medicines = conn.execute("""
        SELECT medicine_name,
               SUM(quantity_sold) as total_qty,
               SUM(total_price) as total_rev
        FROM sales
        GROUP BY medicine_name
        ORDER BY total_qty DESC
        LIMIT 5
    """).fetchall()

    # Query all sales log for comparison dropdown
    all_sales = conn.execute("""
        SELECT medicine_name, quantity_sold, buying_price, total_price, sold_by, strftime('%Y-%m-%d', sold_on) as sold_on
        FROM sales
    """).fetchall()
    
    all_sales_list = []
    for r in all_sales:
        all_sales_list.append({
            "medicine_name": r["medicine_name"],
            "quantity_sold": r["quantity_sold"],
            "buying_price": r["buying_price"] or 0,
            "total_price": r["total_price"],
            "sold_by": r["sold_by"],
            "sold_on": r["sold_on"]
        })

    # Prepare array of revenue shares
    top_revenue_list = [round(r["total_rev"], 2) for r in top_medicines]

    # Daily sales & profit trend
    daily_sales = conn.execute("""
        SELECT strftime('%Y-%m-%d', sold_on) as day, 
               SUM(total_price) as rev,
               SUM(total_price - (quantity_sold * buying_price)) as prof
        FROM sales
        GROUP BY day
        ORDER BY day ASC
        LIMIT 15
    """).fetchall()
    daily_labels = [r["day"] for r in daily_sales]
    daily_values = [round(r["rev"], 2) for r in daily_sales]
    daily_profits = [round(r["prof"], 2) for r in daily_sales]

    conn.close()

    top_labels = [r["medicine_name"] for r in top_medicines]
    top_values = [r["total_qty"] for r in top_medicines]

    return render_template(
        "analytics.html",
        total_revenue=round(total_revenue, 2),
        total_profit=round(total_profit, 2),
        total_sold=total_sold,
        top_labels=json.dumps(top_labels),
        top_values=json.dumps(top_values),
        top_revenue=json.dumps(top_revenue_list),
        all_sales=json.dumps(all_sales_list),
        daily_labels=json.dumps(daily_labels),
        daily_values=json.dumps(daily_values),
        daily_profits=json.dumps(daily_profits),
        top_medicines_count=len(top_labels)
    )
@app.route("/export_inventory")
def export_inventory():

    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    medicines = conn.execute(
        "SELECT * FROM medicines"
    ).fetchall()

    conn.close()

    data = []

    for med in medicines:

        data.append({
            "ID": med["id"],
            "Medicine": med["name"],
            "Batch": med["batch_no"],
            "Quantity": med["quantity"],
            "Price": med["price"],
            "Expiry": med["expiry_date"],
            "Dosage": med["dosage"],
            "Dosage Form": med["dosage_form"],
            "Restrictions": med["restrictions"],
            "Side Effects": med["side_effects"]
        })

    df = pd.DataFrame(data)

    import io
    from flask import Response
    
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=inventory_export.csv"}
    )
@app.route("/medicine_qr/<int:med_id>")
def medicine_qr(med_id):

    if "user" not in session:
        return redirect(url_for("login"))

    import qrcode
    import base64

    conn = get_db()

    med = conn.execute(
        "SELECT * FROM medicines WHERE id=?",
        (med_id,)
    ).fetchone()

    conn.close()

    google = "https://www.google.com/search?q=" + med["name"].replace(" ", "+") + "+medicine"
    qr_text = f"""Medicine: {med['name']}
Batch: {med['batch_no']}
Quantity: {med['quantity']}
Expiry: {med['expiry_date']}
Dosage Form: {med['dosage_form'] or 'N/A'}
Dosage: {med['dosage'] or 'N/A'}
Restrictions: {med['restrictions'] or 'N/A'}
Info: {google}"""

    qr = qrcode.make(qr_text)

    buffer = io.BytesIO()

    qr.save(buffer)

    qr_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode()

    return render_template(
        "medicine_qr.html",
        med=med,
        qr=qr_base64
    )

@app.route("/download_medicine_qr/<int:med_id>")
def download_medicine_qr(med_id):
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    med = conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()
    conn.close()

    if not med:
        return "❌ Error: Medicine not found!", 404

    import qrcode
    import base64
    from reportlab.lib.utils import ImageReader

    # 1. Compile the QR Code text
    google = "https://www.google.com/search?q=" + med["name"].replace(" ", "+") + "+medicine"
    qr_text = f"""Medicine: {med['name']}
Batch: {med['batch_no']}
Quantity: {med['quantity']}
Expiry: {med['expiry_date']}
Dosage Form: {med['dosage_form'] or 'N/A'}
Dosage: {med['dosage'] or 'N/A'}
Restrictions: {med['restrictions'] or 'N/A'}
Info: {google}"""

    qr = qrcode.make(qr_text)
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer)
    qr_buffer.seek(0)
    qr_image = ImageReader(qr_buffer)

    # 2. Draw standard 3.5" x 2" label layout using ReportLab
    # 1 inch = 72 points. 3.5" = 252 points, 2" = 144 points.
    # Scaled 2x for high resolution print layouts: 504 x 288 points.
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(504, 288))

    # Outer border outline
    pdf.setStrokeColorRGB(0, 0.78, 0.65)  # Teal border line
    pdf.setLineWidth(3)
    pdf.rect(10, 10, 484, 268)

    # Header label band
    pdf.setFillColorRGB(0.1, 0.1, 0.18)
    pdf.rect(10, 238, 484, 40, fill=True, stroke=False)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(25, 252, "MEDITRACK PHARMACY LABEL")

    # Draw QR Code Image
    pdf.drawImage(qr_image, 25, 35, width=170, height=170)

    # Text details
    pdf.setFillColorRGB(0.1, 0.1, 0.1)
    pdf.setFont("Helvetica-Bold", 18)
    med_name = med["name"]
    if len(med_name) > 18:
        med_name = med_name[:15] + "..."
    pdf.drawString(215, 195, med_name.upper())

    pdf.setFont("Helvetica", 10)
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.drawString(215, 175, f"Batch: {med['batch_no']}")
    pdf.drawString(215, 160, f"Stock Qty: {med['quantity']} units")
    pdf.drawString(215, 145, f"Expiry Date: {med['expiry_date']}")
    pdf.drawString(215, 130, f"Dosage Form: {med['dosage_form'] or 'Tablet'}")

    # Divider line
    pdf.setStrokeColorRGB(0.9, 0.9, 0.9)
    pdf.setLineWidth(1)
    pdf.line(215, 120, 470, 120)

    # Usage restrictions & dosage summary
    pdf.setFillColorRGB(0.2, 0.2, 0.2)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(215, 102, "Dosage:")
    pdf.setFont("Helvetica", 9)
    dosage = med["dosage"] or "N/A"
    if len(dosage) > 30:
        dosage = dosage[:27] + "..."
    pdf.drawString(275, 102, dosage)

    pdf.setFillColorRGB(0.8, 0.2, 0.2)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(215, 85, "Alerts:")
    pdf.setFont("Helvetica", 9)
    restrictions = med["restrictions"] or "N/A"
    if len(restrictions) > 30:
        restrictions = restrictions[:27] + "..."
    pdf.drawString(275, 85, restrictions)

    # Footer note
    pdf.setFillColorRGB(0.5, 0.5, 0.5)
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(215, 35, "QR code contains medicine profile & instructions.")

    pdf.save()
    buffer.seek(0)

    safe_name = med["name"].lower().replace(" ", "_")
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"qr_label_{safe_name}.pdf",
        mimetype="application/pdf"
    )
@app.route("/sales_history")
def sales_history():
    if "user" not in session:
        return redirect(url_for("login"))

    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    search = request.args.get("search", "")
    seller = request.args.get("seller", "")

    conn = get_db()
    
    query = """
        SELECT sales.*, 
               invoices.patient_name, 
               invoices.patient_phone, 
               invoices.invoice_no,
               invoices.payment_method
        FROM sales 
        LEFT JOIN invoices ON sales.invoice_id = invoices.id
        WHERE 1=1
    """
    params = []
    
    if start_date:
        query += " AND date(sales.sold_on) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(sales.sold_on) <= date(?)"
        params.append(end_date)
    if search:
        query += " AND (sales.medicine_name LIKE ? OR invoices.patient_name LIKE ? OR invoices.invoice_no LIKE ?)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")
        params.append(f"%{search}%")
    if seller:
        query += " AND sales.sold_by = ?"
        params.append(seller)
        
    query += " ORDER BY sales.sold_on DESC"
    sales = conn.execute(query, params).fetchall()

    sellers = conn.execute("SELECT DISTINCT sold_by FROM sales").fetchall()
    conn.close()

    total_qty = sum(item["quantity_sold"] for item in sales)
    total_rev = sum(item["total_price"] for item in sales)

    return render_template(
        "sales_history.html",
        sales=sales,
        sellers=sellers,
        total_qty=total_qty,
        total_rev=round(total_rev, 2),
        start_date=start_date,
        end_date=end_date,
        search=search,
        seller=seller,
        user=session["user"],
        role=session["role"]
    )

@app.route("/edit_medicine/<int:med_id>", methods=["GET", "POST"])
def edit_medicine(med_id):
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "❌ Access Denied: Admin role required!", 403

    conn = get_db()
    med = conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()
    
    if not med:
        conn.close()
        return "❌ Medicine not found!", 404

    if request.method == "POST":
        name = request.form["name"]
        try:
            quantity = int(request.form["quantity"])
            buying_price = float(request.form["buying_price"])
            price = float(request.form["price"])
        except ValueError:
            suppliers = conn.execute("SELECT * FROM suppliers").fetchall()
            conn.close()
            return "❌ Error: Invalid quantity, buying price, or selling price format!", 400

        if quantity < 0 or buying_price <= 0 or price <= 0:
            suppliers = conn.execute("SELECT * FROM suppliers").fetchall()
            conn.close()
            return "❌ Error: Quantity cannot be negative, and buying/selling prices must be positive!", 400

        if price < buying_price:
            suppliers = conn.execute("SELECT * FROM suppliers").fetchall()
            conn.close()
            return "❌ Error: Selling price cannot be lower than buying price (cost price)!", 400

        expiry_date = request.form["expiry_date"]
        from datetime import datetime, date
        try:
            expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            if expiry <= date.today():
                suppliers = conn.execute("SELECT * FROM suppliers").fetchall()
                conn.close()
                return "❌ Error: Expiry date must be strictly in the future!", 400
        except ValueError:
            suppliers = conn.execute("SELECT * FROM suppliers").fetchall()
            conn.close()
            return "❌ Error: Invalid expiry date format!", 400

        dosage = request.form["dosage"]
        dosage_form = request.form.get("dosage_form", "Tablet")
        restrictions = request.form["restrictions"]
        side_effects = request.form["side_effects"]
        supplier = request.form.get("supplier", "")

        # Handle image upload if a new one was provided
        image_file = request.files.get("image")
        image_path = med["image"]  # Keep existing by default
        
        if image_file and image_file.filename != "":
            path, err = save_uploaded_file(image_file)
            if err:
                suppliers = conn.execute("SELECT * FROM suppliers").fetchall()
                conn.close()
                return f"❌ Error: {err}"
            image_path = path

        conn.execute("""
            UPDATE medicines
            SET name=?, quantity=?, buying_price=?, price=?, expiry_date=?, dosage=?, dosage_form=?, restrictions=?, side_effects=?, supplier=?, image=?
            WHERE id=?
        """, (name, quantity, buying_price, price, expiry_date, dosage, dosage_form, restrictions, side_effects, supplier, image_path, med_id))
        
        conn.commit()
        conn.close()
        return redirect(url_for("inventory"))

    suppliers = conn.execute("SELECT * FROM suppliers").fetchall()
    conn.close()
    return render_template("edit_medicine.html", medicine=med, suppliers=suppliers, user=session["user"], role=session["role"])

@app.route("/delete_medicine/<int:med_id>")
def delete_medicine(med_id):
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "❌ Access Denied: Admin role required!", 403

    conn = get_db()
    conn.execute("DELETE FROM medicines WHERE id=?", (med_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("inventory"))

@app.route("/suppliers")
def suppliers():
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "❌ Access Denied: Admin role required!", 403

    edit_id = request.args.get("edit")
    conn = get_db()
    
    edit_supplier = None
    if edit_id:
        edit_supplier = conn.execute("SELECT * FROM suppliers WHERE id=?", (edit_id,)).fetchone()
        
    suppliers_list = conn.execute("SELECT * FROM suppliers").fetchall()
    conn.close()
    
    return render_template(
        "suppliers.html",
        suppliers=suppliers_list,
        edit_supplier=edit_supplier,
        user=session["user"],
        role=session["role"]
    )

@app.route("/add_supplier", methods=["POST"])
def add_supplier():
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "❌ Access Denied: Admin role required!", 403

    name = request.form["name"]
    phone = request.form.get("phone", "")
    email = request.form.get("email", "")
    address = request.form.get("address", "")

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO suppliers (name, phone, email, address)
            VALUES (?, ?, ?, ?)
        """, (name, phone, email, address))
        conn.commit()
    except Exception as e:
        conn.close()
        return f"❌ Error: Supplier name must be unique! ({str(e)})", 400
    
    conn.close()
    return redirect(url_for("suppliers"))

@app.route("/edit_supplier/<int:sup_id>", methods=["POST"])
def edit_supplier(sup_id):
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "❌ Access Denied: Admin role required!", 403

    name = request.form["name"]
    phone = request.form.get("phone", "")
    email = request.form.get("email", "")
    address = request.form.get("address", "")

    conn = get_db()
    try:
        conn.execute("""
            UPDATE suppliers
            SET name=?, phone=?, email=?, address=?
            WHERE id=?
        """, (name, phone, email, address, sup_id))
        conn.commit()
    except Exception as e:
        conn.close()
        return f"❌ Error: Supplier name must be unique! ({str(e)})", 400
        
    conn.close()
    return redirect(url_for("suppliers"))

@app.route("/delete_supplier/<int:sup_id>")
def delete_supplier(sup_id):
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "❌ Access Denied: Admin role required!", 403

    conn = get_db()
    conn.execute("DELETE FROM suppliers WHERE id=?", (sup_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("suppliers"))

@app.route("/developer")
def developer():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("developer.html", user=session["user"], role=session["role"])

@app.route("/staff")
def staff():
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "❌ Access Denied: Admin role required!", 403

    conn = get_db()
    users_list = conn.execute("SELECT id, username, role FROM users ORDER BY id ASC").fetchall()
    conn.close()

    return render_template("staff.html", user=session["user"], role=session["role"], users=users_list)

@app.route("/add_staff", methods=["POST"])
def add_staff():
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "❌ Access Denied: Admin role required!", 403

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "staff").strip()

    if not username or not password:
        return "❌ Error: Username and password are required!", 400

    hashed_pw = generate_password_hash(password, method="scrypt")

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
        """, (username, hashed_pw, role))
        conn.commit()
    except Exception as e:
        conn.close()
        return f"❌ Error: Username '{username}' already exists!", 400

    conn.close()
    return redirect(url_for("staff"))

@app.route("/delete_staff/<int:user_id>")
def delete_staff(user_id):
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "❌ Access Denied: Admin role required!", 403

    conn = get_db()
    
    # Get user to make sure we don't self-delete the logged-in admin
    target_user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not target_user:
        conn.close()
        return "❌ Error: User not found!", 404
        
    if target_user["username"] == session["user"]:
        conn.close()
        return "❌ Error: You cannot delete your own admin account!", 400

    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for("staff"))

@app.route("/remove_from_cart/<int:item_id>")
def remove_from_cart(item_id):
    if "user" not in session:
        return redirect(url_for("login"))
    if "cart" in session:
        cart = session["cart"]
        session["cart"] = [item for item in cart if item["id"] != item_id]
    return redirect(url_for("billing"))

@app.route("/update_cart_qty/<int:item_id>/<string:action>")
def update_cart_qty(item_id, action):
    if "user" not in session:
        return redirect(url_for("login"))
    if "cart" in session:
        cart = session["cart"]
        conn = get_db()
        med = conn.execute("SELECT quantity FROM medicines WHERE id=?", (item_id,)).fetchone()
        max_qty = med["quantity"] if med else 0
        conn.close()
        
        for item in cart:
            if item["id"] == item_id:
                if action == "inc":
                    if item["qty"] < max_qty:
                        item["qty"] += 1
                        item["total"] = item["qty"] * item["price"]
                elif action == "dec":
                    if item["qty"] > 1:
                        item["qty"] -= 1
                        item["total"] = item["qty"] * item["price"]
                break
        session["cart"] = cart
    return redirect(url_for("billing"))

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)