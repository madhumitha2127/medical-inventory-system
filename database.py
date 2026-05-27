import sqlite3

DB_NAME = "medical_inventory.db"

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
        price REAL,
        expiry_date TEXT,
        dosage TEXT,
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

    conn.commit()
    conn.close()


init_db()