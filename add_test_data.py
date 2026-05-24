import sqlite3

conn = sqlite3.connect('medical_inventory.db')

conn.execute("INSERT INTO sales (medicine_name, quantity_sold, total_price, sold_by, sold_on) VALUES ('Paracetamol', 45, 225.0, 'admin', '2026-03-01')")
conn.execute("INSERT INTO sales (medicine_name, quantity_sold, total_price, sold_by, sold_on) VALUES ('Dolo 650', 30, 180.0, 'staff1', '2026-03-02')")
conn.execute("INSERT INTO sales (medicine_name, quantity_sold, total_price, sold_by, sold_on) VALUES ('Amoxicillin', 20, 400.0, 'admin', '2026-03-03')")
conn.execute("INSERT INTO sales (medicine_name, quantity_sold, total_price, sold_by, sold_on) VALUES ('Crocin', 55, 275.0, 'staff1', '2026-03-04')")
conn.execute("INSERT INTO sales (medicine_name, quantity_sold, total_price, sold_by, sold_on) VALUES ('Ibuprofen', 15, 150.0, 'admin', '2026-03-05')")

conn.commit()
conn.close()
print("Done! Test data added.")