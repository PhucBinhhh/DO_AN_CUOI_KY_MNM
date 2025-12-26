from pymongo import MongoClient

# --- CẤU HÌNH ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "pharmacity_db"
COLLECTION_NAME = "products"

def remove_duplicates():
    client = MongoClient(MONGO_URI)
    col = client[DB_NAME][COLLECTION_NAME]

    print("🕵️‍♂️ Đang quét các sản phẩm bị trùng lặp...")

    # 1. Tìm các original_id xuất hiện nhiều hơn 1 lần
    # (Loại trừ thằng 'Unknown' ra vì sẽ xử lý riêng)
    pipeline = [
        {"$match": {"original_id": {"$ne": "Unknown"}}}, 
        {"$group": {
            "_id": "$original_id", 
            "count": {"$sum": 1}, 
            "ids": {"$push": "$_id"} # Lưu danh sách _id của các bản ghi trùng
        }},
        {"$match": {"count": {"$gt": 1}}} # Chỉ lấy nhóm có số lượng > 1
    ]

    duplicates = list(col.aggregate(pipeline))
    
    if not duplicates:
        print("✅ Dữ liệu sạch! Không có sản phẩm nào bị trùng ID.")
        return

    print(f"⚠️ Phát hiện {len(duplicates)} mã sản phẩm bị trùng. Đang xử lý...")
    
    total_deleted = 0

    # 2. Duyệt qua từng nhóm trùng và xóa bớt
    for item in duplicates:
        original_id = item["_id"]
        doc_ids = item["ids"]
        
        # Giữ lại phần tử đầu tiên (index 0), xóa từ phần tử thứ 2 trở đi
        ids_to_remove = doc_ids[1:] 
        
        # Thực hiện lệnh xóa
        result = col.delete_many({"_id": {"$in": ids_to_remove}})
        deleted_count = result.deleted_count
        total_deleted += deleted_count
        
        print(f"   - Mã {original_id}: Giữ 1, đã xóa {deleted_count} bản thừa.")

    print("-" * 50)
    print(f"🎉 ĐÃ XONG! Tổng cộng đã xóa {total_deleted} bản ghi thừa.")

if __name__ == "__main__":
    remove_duplicates()