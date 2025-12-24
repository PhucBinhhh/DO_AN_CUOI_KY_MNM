import json
import os
from pymongo import MongoClient

# --- CẤU HÌNH ---
JSON_FILE = r"products_final_all.json"
MONGO_URI = "mongodb://localhost:27017/" # Đường dẫn kết nối MongoDB mặc định
DB_NAME = "pharmacity_db"                # Tên Database
COLLECTION_NAME = "products"             # Tên Collection (bảng)

def import_data():
    # 1. Kết nối MongoDB
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        print("✅ Đã kết nối thành công tới MongoDB!")
    except Exception as e:
        print(f"❌ Lỗi kết nối MongoDB: {e}")
        return

    # 2. Đọc file JSON
    if not os.path.exists(JSON_FILE):
        print(f"❌ Không tìm thấy file: {JSON_FILE}")
        return

    print(f"📂 Đang đọc dữ liệu từ: {JSON_FILE}...")
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 3. Chuẩn hóa dữ liệu (Mapping Key cũ -> Key mới)
    formatted_data = []
    print("🔄 Đang chuẩn hóa cấu trúc dữ liệu...")

    for item in raw_data:
        # Tạo document mới với cấu trúc đẹp hơn
        doc = {
            "original_id": item.get("ID", ""),
            "name": item.get("PRODUCT_NAME", ""),
            "category": item.get("CATEGORY", ""),
            "price": item.get("PRICE", 0),
            "price_source": item.get("PRICE_SOURCE", ""),
            "unit": item.get("UNIT", ""),
            "image_url": item.get("IMAGE", ""),
            "metrics": {
                "sold": item.get("SOLE_COUNT", 0),
                "likes": item.get("LIKES", 0)
            },
            "description": item.get("PRODUCT_DESCRIPTION", ""),
            # Giữ nguyên object bên trong, chỉ đổi tên key ngoài
            "specs": item.get("Chi tiết kỹ thuật", {}), 
            "reviews": item.get("FAQ & Reviews", []),
            "source_url": item.get("URL", "")
        }
        formatted_data.append(doc)

    # 4. Ghi vào MongoDB
    if formatted_data:
        # Xóa dữ liệu cũ nếu muốn làm sạch trước khi import (Tùy chọn)
        # collection.delete_many({}) 
        # print("🗑️ Đã xóa dữ liệu cũ trong Collection.")

        # Dùng insert_many cho tốc độ cao
        result = collection.insert_many(formatted_data)
        print("-" * 50)
        print(f"🎉 HOÀN TẤT! Đã import {len(result.inserted_ids)} sản phẩm vào MongoDB.")
        print(f"👉 Database: {DB_NAME}")
        print(f"👉 Collection: {COLLECTION_NAME}")
        print("-" * 50)
    else:
        print("⚠️ File JSON rỗng, không có gì để import.")

if __name__ == "__main__":
    import_data()