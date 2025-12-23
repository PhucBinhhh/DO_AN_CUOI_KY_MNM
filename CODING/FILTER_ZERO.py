import json

# --- CẤU HÌNH ---
# File kết quả tổng mà bạn đã chạy xong (chứa cả cái có giá và không giá)
INPUT_FILE = "products_final_success.json" 
# File mới sẽ chứa riêng các sản phẩm bị mất giá
OUTPUT_FILE = "products_missing_price.json"

def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"📊 Đang đọc file tổng: {len(data)} sản phẩm.")
    except:
        print(f"❌ Không tìm thấy file {INPUT_FILE}")
        return

    # Lọc những sản phẩm có Giá = 0
    missing_list = [p for p in data if p.get("Giá") == 0]
    
    print(f"⚠️ Tìm thấy {len(missing_list)} sản phẩm chưa lấy được giá.")
    
    # Lưu ra file riêng
    if missing_list:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(missing_list, f, ensure_ascii=False, indent=4)
        print(f"💾 Đã lưu danh sách cần xử lý vào: {OUTPUT_FILE}")
        print("👉 Giờ hãy chạy file 'HUNTER_FIX.py' để xử lý file này!")
    else:
        print("🎉 Chúc mừng! Không có sản phẩm nào bị lỗi giá cả.")

if __name__ == "__main__":
    main()