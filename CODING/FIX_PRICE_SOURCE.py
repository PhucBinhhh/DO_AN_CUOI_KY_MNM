import json
import os

# Đường dẫn đến file JSON
FILE_PATH = r"products_final_all.json"

def clean_price_source():
    # 1. Kiểm tra file
    if not os.path.exists(FILE_PATH):
        print(f" Lỗi: Không tìm thấy file tại {FILE_PATH}")
        return

    print(f" Đang đọc file: {FILE_PATH}...")
    
    try:
        # 2. Đọc dữ liệu cũ
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        count_modified = 0
        
        # 3. Duyệt và sửa đổi
        for product in data:
            source = product.get("PRICE_SOURCE", "")
            
            # Kiểm tra nếu nguồn giá chứa từ khóa "Comment" hoặc "Admin"
            if "Comment" in source or "Admin" in source:
                # Đổi thành chữ "Comment" ngắn gọn
                product["PRICE_SOURCE"] = "Comment"
                
                # Hoặc nếu bạn muốn xóa hẳn phần trong ngoặc nhưng giữ nguyên ý nghĩa:
                # product["PRICE_SOURCE"] = source.split("(")[0].strip()
                
                count_modified += 1

            # (Tùy chọn) Sửa luôn phần UNIT nếu muốn (bỏ chữ "Theo Admin")
            unit = product.get("UNIT", "")
            if "Theo Admin" in unit:
                product["UNIT"] = unit.replace("(Theo Admin)", "").strip()

        # 4. Lưu lại file đã sửa
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print("-" * 40)
        print(f" ĐÃ XONG! Đã sửa đổi {count_modified} sản phẩm.")
        print(f" File đã được lưu đè lên: {FILE_PATH}")
        print("-" * 40)

    except Exception as e:
        print(f" Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    clean_price_source()