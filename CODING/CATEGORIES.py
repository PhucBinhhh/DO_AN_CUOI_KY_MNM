import time
import pandas as pd
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CẤU HÌNH ---
OUTPUT_FILE = "categories_urls.csv"
TARGET_URL = "https://www.pharmacity.vn/"

# DANH SÁCH CHẶN (BLACKLIST): Những từ khóa này xuất hiện trong link -> BỎ QUA NGAY
BLACKLIST = [
    "goc-suc-khoe",   # Blog sức khỏe
    "bai-viet",       # Bài viết tin tức
    "tin-tuc",        # Tin tức
    "khuyen-mai",     # Trang khuyến mãi (thường tạp nham)
    "he-thong-nha-thuoc",
    "huong-dan",
    "lien-he",
    "tuyen-dung",
    "chinh-sach",
    "gio-hang",
    "account",
    "profile"
]

# DANH SÁCH ƯU TIÊN (WHITELIST): Những từ khóa chắc chắn là danh mục gốc
VALID_ROOTS = [
    "/duoc-pham",
    "/cham-soc-suc-khoe",
    "/cham-soc-ca-nhan",
    "/me-va-be",
    "/cham-soc-sac-dep",
    "/thuc-pham-chuc-nang",
    "/thiet-bi-y-te",
    "/bach-hoa-gia-dinh"
]

def get_categories():
    print(" Đang khởi động trình duyệt...")
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    categories = []
    
    try:
        print(f" Đang truy cập: {TARGET_URL}")
        driver.get(TARGET_URL)
        time.sleep(5) 
        
        # Lấy tất cả thẻ 'a' trên trang
        elements = driver.find_elements(By.TAG_NAME, "a")
        
        seen_urls = set()

        for elem in elements:
            try:
                link = elem.get_attribute('href')
                text = elem.text.strip()
                
                if not link or "pharmacity.vn" not in link:
                    continue

                # --- BỘ LỌC THÔNG MINH (UPDATED) ---
                
                # 1. Kiểm tra Blacklist: Nếu chứa từ khóa cấm -> Bỏ qua
                if any(bad_word in link for bad_word in BLACKLIST):
                    continue
                
                # 2. Kiểm tra Whitelist: Link phải bắt đầu bằng danh mục gốc hợp lệ
                # urlparse(link).path sẽ lấy phần sau .vn (ví dụ: /me-va-be)
                path = urlparse(link).path # Kết quả: /me-va-be hoặc /thuoc
                
                # Logic: Path phải BẮT ĐẦU bằng một trong các từ khóa gốc
                is_valid_category = False
                for root in VALID_ROOTS:
                    if path.startswith(root):
                        is_valid_category = True
                        break
                
                # 3. Lưu kết quả
                if is_valid_category and link not in seen_urls:
                    # Lọc thêm: Tên danh mục không được quá dài (tránh lấy tiêu đề bài viết bị lọt)
                    if text and len(text) < 50:
                        categories.append({
                            "Category Name": text,
                            "URL": link
                        })
                        seen_urls.add(link)
                        print(f" Đã lấy: {text} | Link: {path}")

            except Exception as e:
                continue

    except Exception as e:
        print(f" Lỗi: {e}")
    finally:
        driver.quit()
        
    return categories

if __name__ == "__main__":
    data = get_categories()
    
    if data:
        df = pd.DataFrame(data)
        
        print(f"\n Tìm thấy ban đầu: {len(df)} dòng.")

        # --- BƯỚC LÀM SẠCH QUAN TRỌNG ---
        
        # 1. Cắt bỏ phần đuôi rác (?utm_...) trong URL
        # Logic: Tách chuỗi theo dấu '?' và chỉ lấy phần đầu tiên
        df["URL"] = df["URL"].apply(lambda x: x.split('?')[0])
        
        # 2. Xóa trùng lặp sau khi đã làm sạch URL
        # (Lúc này link có utm và không utm sẽ giống hệt nhau -> bị xóa)
        df = df.drop_duplicates(subset=["URL"])
        
        # 3. Xóa trùng lặp theo Tên danh mục (ưu tiên giữ cái đầu tiên tìm thấy)
        df = df.drop_duplicates(subset=["Category Name"])
        
        # 4. Sắp xếp lại
        df = df.sort_values(by="Category Name")
        
        # Lưu file
        df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        
        print(f" Đã dọn dẹp các link rác (?utm_source).")
        print(f" KẾT QUẢ CUỐI CÙNG: {len(df)} danh mục chuẩn.")
        print("-" * 30)
        print(df) # In toàn bộ ra để ngắm nghía
    else:
        print("\n Không tìm thấy danh mục.")
        
        