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

    conn.commit()
    conn.close()


init_db()