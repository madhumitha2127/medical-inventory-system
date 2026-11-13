import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "medical_inventory.db")
def get_db():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    conn.execute("""

    CREATE TABLE IF NOT EXISTS medicines (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT,
        batch_no TEXT,
        quantity INTEGER,
        buying_price REAL,
        price REAL,
        expiry_date TEXT,
        dosage TEXT,
        dosage_form TEXT,
        restrictions TEXT,
        side_effects TEXT,
        supplier TEXT,
        image TEXT

    )

    """)

    conn.execute("""

    CREATE TABLE IF NOT EXISTS sales (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        medicine_name TEXT,
        quantity_sold INTEGER,
        buying_price REAL,
        total_price REAL,
        sold_by TEXT,
        sold_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )

    """)

    conn.execute("""

    CREATE TABLE IF NOT EXISTS suppliers (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT UNIQUE,
        phone TEXT,
        email TEXT,
        address TEXT

    )

    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE,
        patient_name TEXT,
        patient_age INTEGER,
        patient_gender TEXT,
        patient_phone TEXT,
        doctor_name TEXT,
        prescription_id TEXT,
        payment_method TEXT,
        discount_rate REAL,
        discount_amount REAL,
        tax_rate REAL,
        tax_amount REAL,
        subtotal REAL,
        grand_total REAL,
        sold_by TEXT,
        sold_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Seed default credentials if table is empty
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        conn.execute("""
        INSERT INTO users (username, password, role)
        VALUES (
            'admin', 
            'scrypt:32768:8:1$zk703vBNGt8535At$3b6b98132d22021e98eb0fbc7ff0953e68da08d0e3c15f5ceaad546e220b67382aeeb9eeca856c2e6e05bbcf8c3e4674ac7d32ff9ebfe26bfa950b97a7cd9416', 
            'admin'
        )
        """)
        conn.execute("""
        INSERT INTO users (username, password, role)
        VALUES (
            'staff1', 
            'scrypt:32768:8:1$xJq1b0S0fHhAKHn0$f79848e2bdd89b24bb4a58f54a4420411a5e64cd92449882b2a5078ff355fe6d5bdffa5b779a48e7e65d8ba905d5288be525cc99dd8233d653b6dd039e298961', 
            'staff'
        )
        """)

    # Dynamic migrations for existing databases
    # 1. Migrate medicines table
    cursor = conn.execute("PRAGMA table_info(medicines)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "buying_price" not in columns:
        conn.execute("ALTER TABLE medicines ADD COLUMN buying_price REAL")
        conn.execute("UPDATE medicines SET buying_price = ROUND(price * 0.7, 2)")
    if "dosage_form" not in columns:
        conn.execute("ALTER TABLE medicines ADD COLUMN dosage_form TEXT")
        conn.execute("UPDATE medicines SET dosage_form = 'Tablet'")

    # 2. Migrate sales table
    cursor = conn.execute("PRAGMA table_info(sales)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "buying_price" not in columns:
        conn.execute("ALTER TABLE sales ADD COLUMN buying_price REAL")
        conn.execute("""
            UPDATE sales 
            SET buying_price = ROUND((total_price / quantity_sold) * 0.7, 2)
            WHERE quantity_sold > 0
        """)
    if "invoice_id" not in columns:
        conn.execute("ALTER TABLE sales ADD COLUMN invoice_id INTEGER")

    conn.commit()
    conn.close()


init_db()
