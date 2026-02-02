import os
import qrcode

def generate_qr(bill_text, bill_id):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.join(base_dir, "qr_codes")

    os.makedirs(folder, exist_ok=True)

    path = os.path.join(folder, f"bill_qr_{bill_id}.png")
    img = qrcode.make(bill_text)
    img.save(path)

    print(f"📱 QR Code saved at: {path}")
