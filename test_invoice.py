import os

base_dir = os.path.dirname(os.path.abspath(__file__))
folder = os.path.join(base_dir, "invoices")
os.makedirs(folder, exist_ok=True)

file_path = os.path.join(folder, "test.txt")
with open(file_path, "w") as f:
    f.write("TEST OK")

print("CREATED:", file_path)
