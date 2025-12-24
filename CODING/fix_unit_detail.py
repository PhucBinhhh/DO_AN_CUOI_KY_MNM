import json
import os

# Đường dẫn file
FILE_PATH = r"products_final_all.json"

def fix_specific_units():
    # 1. Kiểm tra file
    if not os.path.exists(FILE_PATH):
        print(f"❌ Lỗi: Không tìm thấy file tại {FILE_PATH}")
        return

    print(f"📂 Đang đọc file: {FILE_PATH}...")
    
    try:
        # 2. Đọc dữ liệu
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        count_bom = 0
        count_follitrope = 0
        
        # 3. Duyệt và sửa lỗi
        for p in data:
            unit = p.get("UNIT", "").strip()
            name = p.get("PRODUCT_NAME", "").strip()
            
            # --- Yêu cầu 1: Đổi "Bom" thành "Bơm tiêm" ---
            if unit == "Bom":
                p["UNIT"] = "Bơm tiêm"
                count_bom += 1
            
            # --- Yêu cầu 2: Sửa sản phẩm Follitrope ---
            # So sánh chính xác tên hoặc chứa trong tên
            target_name = "Follitrope Prefilled Syringe 150IU BT 0.3ML"
            if target_name in name:
                # Chỉ sửa nếu Unit hiện tại chưa phải là Hộp
                if p["UNIT"] != "Hộp":
                    print(f"🔧 Đã sửa: {name} | {p['UNIT']} -> Hộp")
                    p["UNIT"] = "Hộp"
                    count_follitrope += 1

        # 4. Lưu lại file
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print("-" * 50)
        print("✅ ĐÃ SỬA XONG!")
        print(f"🔹 Đã đổi 'Bom' -> 'Bơm tiêm': {count_bom} sản phẩm")
        print(f"🔹 Đã sửa Unit cho 'Follitrope...': {count_follitrope} sản phẩm")
        print("-" * 50)

    except Exception as e:
        print(f"❌ Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    fix_specific_units()