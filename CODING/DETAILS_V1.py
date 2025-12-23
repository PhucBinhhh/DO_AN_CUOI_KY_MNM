import time
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CẤU HÌNH ---
INPUT_FILE = "product_links_raw.json"    # File nguồn (kết quả ngày 2)
OUTPUT_FILE = "products_test_50.json"    # File kết quả chạy thử
LIMIT = 50                               # CHỈ LẤY 50 SẢN PHẨM

def parse_price_and_unit(raw_text):
    """
    Input: "18.000 ₫/Gói" hoặc "119.000đ/Chai"
    Output: price (18000), unit ("Gói")
    """
    price = 0
    unit = "Đang cập nhật"
    
    if not raw_text:
        return price, unit

    try:
        # Xóa dấu chấm phân cách ngàn, xóa khoảng trắng thừa
        clean_str = raw_text.replace(".", "").replace(",", "").strip() # Ra: 18000 ₫/Gói
        
        # Trường hợp 1: Có dấu gạch chéo phân tách (VD: /Gói, /Hộp)
        if "/" in clean_str:
            parts = clean_str.split("/")
            price_part = parts[0] # "18000 ₫"
            unit_part = parts[1]  # "Gói"
            
            # Lấy số từ phần giá
            found_digits = re.findall(r'\d+', price_part)
            if found_digits:
                price = int("".join(found_digits))
            
            # Làm sạch phần đơn vị
            unit = unit_part.strip()
            
        # Trường hợp 2: Không có đơn vị, chỉ có giá
        else:
            found_digits = re.findall(r'\d+', clean_str)
            if found_digits:
                price = int("".join(found_digits))
            unit = "Hộp" # Mặc định nếu không ghi gì
            
    except:
        pass # Nếu lỗi thì giữ nguyên mặc định
        
    return price, unit

def clean_text(text):
    if text:
        return text.replace("\n", " ").strip()
    return ""

def get_product_details(driver, link_data):
    url = link_data["url"]
    category = link_data["category"]
    
    # Khởi tạo khung dữ liệu
    product = {
        "Danh mục": category,
        "ID Sản phẩm": "Đang cập nhật",
        "Tên sản phẩm": "",
        "URL": url,
        "Giá": "",
        "Đơn vị tính": "",
        "Mô tả chi tiết": {},
        "Số sao": "0",
        "Số lượng mua/đánh giá": "",
        "Đánh giá của khách hàng": []
    }

    try:
        driver.get(url)
        # Chờ tối đa 5s để thẻ h1 (Tên sản phẩm) xuất hiện
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        except:
            pass
        
        # 1. LẤY TÊN SẢN PHẨM
        try:
            product["Tên sản phẩm"] = driver.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            product["Tên sản phẩm"] = "Unknown"

        # 2. LẤY ID SẢN PHẨM (Ưu tiên lấy từ URL cho chuẩn xác)
        # Link dạng: ...-p12345.html
        match = re.search(r'-p(\d+)\.html', url)
        if match:
            product["ID Sản phẩm"] = "P" + match.group(1)
        else:
            # Nếu URL không có, tìm dòng "Mã sản phẩm" trên giao diện
            try:
                id_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Mã sản phẩm')]")
                product["ID Sản phẩm"] = id_elem.text.split(":")[-1].strip()
            except:
                pass

        # 3. LẤY GIÁ (Tìm theo biểu tượng ₫)
        try:
            # Tìm tất cả phần tử chứa '₫'
            price_elems = driver.find_elements(By.XPATH, "//*[contains(text(), '₫')]")
            valid_prices = []
            for p in price_elems:
                txt = p.text.strip()
                # Lọc rác: Giá phải có số và độ dài ngắn
                if any(c.isdigit() for c in txt) and len(txt) < 20:
                    valid_prices.append(txt)
            
            if valid_prices:
                product["Giá"] = valid_prices[0] # Lấy giá đầu tiên tìm thấy
            else:
                product["Giá"] = "Liên hệ / Hết hàng"
        except:
            product["Giá"] = "Lỗi lấy giá"

        # 4. LẤY ĐƠN VỊ TÍNH
        try:
            # Tìm dòng chứa chữ "Quy cách"
            unit_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Quy cách')]")
            product["Đơn vị tính"] = unit_elem.text.replace("Quy cách", "").replace(":", "").strip()
        except:
            pass

        # 5. LẤY MÔ TẢ CHI TIẾT (Quét bảng thông tin)
        try:
            info_dict = {}
            # Tìm tất cả thẻ tr (hàng trong bảng)
            rows = driver.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 2:
                    key = clean_text(cols[0].text)
                    val = clean_text(cols[1].text)
                    if key and val:
                        info_dict[key] = val
            
            # Nếu không có bảng, tìm các thẻ div thông tin
            if not info_dict:
                divs = driver.find_elements(By.XPATH, "//div[contains(@class, 'attribute-item')] | //div[contains(@class, 'description')]//li")
                for d in divs:
                    txt = d.text
                    if ":" in txt:
                        parts = txt.split(":", 1)
                        info_dict[parts[0].strip()] = parts[1].strip()

            product["Mô tả chi tiết"] = info_dict
        except:
            pass

        # 6. LẤY ĐÁNH GIÁ (Tìm 3 comment đầu tiên)
        try:
            # Cuộn xuống chút để kích hoạt comment
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            
            comments = driver.find_elements(By.XPATH, "//div[contains(@class, 'content') and string-length(text()) > 10]")
            raw_reviews = []
            count = 0
            for cmt in comments:
                txt = cmt.text.strip()
                # Lọc các dòng hệ thống không phải comment
                if "Gửi đánh giá" not in txt and "Trả lời" not in txt:
                    raw_reviews.append(txt)
                    count += 1
                    if count >= 3: break # Chỉ lấy 3 cái demo
            product["Đánh giá của khách hàng"] = raw_reviews
        except:
            pass

        # In ra màn hình để bạn kiểm tra ngay lập tức
        print(f"   ✅ {product['Tên sản phẩm'][:30]}... | ID: {product['ID Sản phẩm']} | Giá: {product['Giá']}")
        return product

    except Exception as e:
        print(f"   ❌ Lỗi link: {url} -> {e}")
        return None

# --- MAIN ---
def main():
    # 1. Đọc file
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            full_list = json.load(f)
    except:
        print(f"❌ Không tìm thấy file {INPUT_FILE}. Hãy chạy code Ngày 2 trước.")
        return

    # 2. Cắt lấy 50 link đầu tiên để test
    test_list = full_list[:LIMIT]
    print(f"🚀 BẮT ĐẦU TEST: Chạy thử trên {len(test_list)} sản phẩm...")

    # 3. Khởi tạo Driver
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    results = []

    # 4. Chạy vòng lặp
    for index, item in enumerate(test_list):
        print(f"[{index+1}/{LIMIT}] ", end="")
        data = get_product_details(driver, item)
        if data:
            results.append(data)
        
        # Cứ 10 cái lưu 1 lần cho chắc
        if (index + 1) % 10 == 0:
             with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)

    driver.quit()

    # 5. Lưu kết quả cuối cùng
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    print("\n" + "="*40)
    print(f"🏁 ĐÃ CHẠY XONG 50 LINK!")
    print(f"💾 Kết quả lưu tại: {OUTPUT_FILE}")
    print("👉 Hãy mở file này lên kiểm tra xem dữ liệu đã đủ ID, Giá chưa nhé.")

if __name__ == "__main__":
    main()