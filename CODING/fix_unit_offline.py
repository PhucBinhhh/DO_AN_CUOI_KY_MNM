import json
import re
import os

# --- CẤU HÌNH ---
FILE_PATH = r"products_final_all.json"

def get_unit_from_reviews(reviews_list, target_price):
    """
    Tìm trong đống review xem đơn vị tính ứng với giá target_price là gì.
    Ví dụ: target_price = 216000
    Text: "... 216.000 đ/Hộp ..."
    -> Trả về: "Hộp"
    """
    if not reviews_list: return None
    
    # Gộp tất cả review thành 1 chuỗi lớn để dễ tìm
    full_text = " ".join(reviews_list).lower()
    
    # Regex tìm: [Số tiền] [đ/₫] / [Đơn vị]
    # Group 1: Số tiền
    # Group 2: Đơn vị
    pattern = r"([\d\.,]+)\s*(?:đ|₫|vnđ)\s*/\s*([^\s.,;)]+)"
    
    matches = re.findall(pattern, full_text)
    
    for m in matches:
        raw_price_str = m[0]
        raw_unit = m[1]
        
        # Chuyển text giá thành số nguyên để so sánh
        try:
            price_val = int(raw_price_str.replace(".", "").replace(",", "").strip())
        except: continue
        
        # Nếu giá trong text khớp với giá đang lưu trong JSON
        if price_val == target_price:
            # Chuẩn hóa tên đơn vị (viết hoa chữ đầu)
            return raw_unit.title()
            
    return None

def main():
    if not os.path.exists(FILE_PATH):
        print("❌ Không tìm thấy file JSON.")
        return

    print(f" Đang đọc file: {FILE_PATH}...")
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    count_fixed = 0
    
    print(" Đang quét comment để sửa lại Unit...")
    
    for p in data:
        current_unit = p.get("UNIT", "")
        price = p.get("PRICE", 0)
        source = p.get("PRICE_SOURCE", "")
        reviews = p.get("FAQ & Reviews", [])
        
        # Điều kiện sửa:
        # 1. Nguồn là Comment HOẶC Unit đang là mặc định "Hộp/Chai"
        # 2. Phải có giá > 0 thì mới đối chiếu được
        # 3. Phải có dữ liệu Review
        if (price > 0 and reviews) and ("Comment" in source or current_unit == "Hộp/Chai" or "Admin" in current_unit):
            
            found_unit = get_unit_from_reviews(reviews, price)
            
            if found_unit:
                # Nếu tìm được unit chuẩn và nó khác unit cũ
                if found_unit != current_unit:
                    # print(f" {p['PRODUCT_NAME'][:20]}...: {price}đ | {current_unit} -> {found_unit}")
                    p["UNIT"] = found_unit
                    
                    # Nếu Unit cũ có chữ "Admin", ta cũng nên sửa lại nguồn giá cho gọn
                    if "Admin" in source:
                        p["PRICE_SOURCE"] = "Comment"
                        
                    count_fixed += 1
            else:
                # Trường hợp không tìm thấy trong comment (hiếm), 
                # nếu unit cũ dính chữ "Theo Admin", ta dọn dẹp về "Hộp/Chai" cho sạch
                if "Theo Admin" in current_unit:
                    p["UNIT"] = "Hộp/Chai"

    # Lưu lại file
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("-" * 40)
    print(f" HOÀN TẤT! Đã sửa đơn vị tính cho {count_fixed} sản phẩm.")
    print(f" Dữ liệu đã được cập nhật vào file: {FILE_PATH}")
    print("-" * 40)

if __name__ == "__main__":
    main()