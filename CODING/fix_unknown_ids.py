from pymongo import MongoClient

def delete_garbage():
    client = MongoClient("mongodb://localhost:27017/")
    col = client["pharmacity_db"]["products"]

    # Đếm trước khi xóa
    count_before = col.count_documents({"original_id": "Unknown"})
    
    if count_before == 0:
        print("✅ Database đã sạch! Không có sản phẩm Unknown.")
        return

    print(f"⚠️ Tìm thấy {count_before} sản phẩm lỗi (Không có ID).")
    print("🗑️ Đang tiến hành xóa bỏ...")

    # LỆNH XÓA THẲNG TAY
    result = col.delete_many({"original_id": "Unknown"})

    print("-" * 50)
    print(f"🎉 ĐÃ XÓA THÀNH CÔNG: {result.deleted_count} bản ghi.")
    print("✨ Database của bạn bây giờ đã sạch bóng, sẵn sàng để làm báo cáo!")

if __name__ == "__main__":
    delete_garbage()