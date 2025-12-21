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
INPUT_FILE = "product_links_raw.json"
OUTPUT_FILE = "products_final_success.json"
LIMIT = 30  # Test 50 sản phẩm

# ==========================================
# 🧱 PHẦN 1: CÁC HÀM XỬ LÝ DỮ LIỆU (WORKERS)
# ==========================================

def get_product_id(driver, url):
    """
    Chiến thuật mới: Tìm ID dựa vào vị trí 'Thương hiệu'
    HTML: <p>P01049</p>...<a ...>Thương hiệu: STADA</a>
    """
    # 1. Ưu tiên lấy từ URL (Nhanh nhất)
    if "-p" in url:
        match = re.search(r'-p(\d+)', url)
        if match: return "P" + match.group(1)
        
    # 2. Lấy từ HTML (Dựa vào sibling của Thương hiệu)
    try:
        # XPath: Tìm thẻ 'a' chứa chữ 'Thương hiệu', sau đó lấy thẻ 'p' đứng ngay trước nó
        xpath = "//a[contains(text(), 'Thương hiệu')]/preceding-sibling::p"
        id_elem = driver.find_element(By.XPATH, xpath)
        return id_elem.text.strip()
    except:
        pass
        
    # 3. Cách cũ (Dự phòng)
    try:
        elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Mã sản phẩm:')]")
        return elem.text.split(":")[-1].strip()
    except:
        return "Unknown"

def get_sold_count(driver):
    """
    Lấy số lượng đã bán và đổi sang số nguyên.
    Ví dụ: "Đã bán 6.8k" -> 6800
           "Đã bán 100" -> 100
    """
    try:
        # 1. Tìm thẻ p chứa chữ "Đã bán"
        elem = driver.find_element(By.XPATH, "//p[contains(text(), 'Đã bán')]")
        raw_text = elem.text.lower().strip() # Chuyển thành chữ thường: "đã bán 6.8k"
        
        # 2. Xóa chữ "đã bán" đi, chỉ giữ lại số và đơn vị
        clean_text = raw_text.replace("đã bán", "").strip() # -> "6.8k"
        
        # 3. Xử lý đơn vị K, TR
        multiplier = 1
        if "k" in clean_text:
            multiplier = 1000
            clean_text = clean_text.replace("k", "")
        elif "tr" in clean_text or "m" in clean_text: # Phòng hờ trường hợp triệu
            multiplier = 1000000
            clean_text = clean_text.replace("tr", "").replace("m", "")
            
        # 4. Chuyển đổi sang số
        # Xóa các ký tự lạ, thay dấu phẩy thành dấu chấm (nếu có)
        clean_text = clean_text.replace(",", ".")
        
        # Dùng Regex để chỉ lấy đúng phần số (ví dụ lấy 6.8 từ chuỗi lạ)
        import re
        match = re.search(r"(\d+(\.\d+)?)", clean_text)
        
        if match:
            number_val = float(match.group(1)) # Chuyển thành số thực: 6.8
            final_val = int(number_val * multiplier) # 6.8 * 1000 = 6800
            return final_val
            
    except:
        pass
        
    return 0 # Trả về 0 nếu không tìm thấy hoặc lỗi

def get_product_description(driver):
    """
    Lấy mô tả từ id="mo-ta" (Chính xác 100%, không sợ footer)
    """
    details = {}
    full_text = ""
    
    try:
        # 1. Lấy toàn bộ text trong id="mo-ta"
        desc_box = driver.find_element(By.ID, "mo-ta")
        full_text = desc_box.text.strip()
        
        # 2. Cố gắng tách bảng (nếu bên trong mo-ta có bảng)
        # Để dữ liệu đẹp hơn dạng key-value
        rows = desc_box.find_elements(By.TAG_NAME, "li")
        for row in rows:
            txt = row.text
            if ":" in txt:
                parts = txt.split(":", 1)
                details[parts[0].strip()] = parts[1].strip()
                
    except:
        pass
    
    # Trả về cả text dài và dict đã tách
    return {"Nội dung đầy đủ": full_text, "Thông số tách": details}

def get_reviews_and_qa(driver):
    """
    Lấy đánh giá từ id="comment"
    """
    reviews = []
    try:
        # Cuộn xuống id="comment"
        element = driver.find_element(By.ID, "comment")
        driver.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(1)
        
        # Tìm các khối nội dung comment (class whitespace-break-spaces)
        # XPath này chọc thẳng vào div chứa text comment
        comments = element.find_elements(By.XPATH, ".//div[contains(@class, 'whitespace-break-spaces')]")
        
        for cmt in comments:
            txt = cmt.text.strip()
            # Lọc bỏ các câu chào tự động của Pharmacity nếu muốn
            if txt and "Pharmacity xin chào" not in txt:
                reviews.append(txt)
                if len(reviews) >= 5: break # Lấy tối đa 5 cái
    except:
        pass
    return reviews

def get_price_and_unit(driver):
    """Lấy giá và đơn vị tính"""
    price = 0
    unit = "Hộp/Chai"
    try:
        price_elem = driver.find_element(By.XPATH, "//*[contains(text(), '₫')]")
        raw_text = price_elem.text.strip()
        clean = raw_text.replace(".", "").replace(",", "")
        
        if "/" in clean:
            parts = clean.split("/", 1)
            p_part = re.findall(r'\d+', parts[0])
            if p_part: price = int("".join(p_part))
            unit = parts[1].strip()
        else:
            p_part = re.findall(r'\d+', clean)
            if p_part: price = int("".join(p_part))
    except: pass
    return price, unit

# ==========================================
# 🏭 PHẦN 2: HÀM QUẢN LÝ (CONTROLLER)
# ==========================================

def scrape_product(driver, link_data):
    url = link_data["url"]
    driver.get(url)
    
    # Chờ trang tải (Chờ giá tiền hiện ra là dấu hiệu trang đã load xong)
    try: WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '₫')]")))
    except: pass

    # --- GỌI CÁC WORKER ---
    name = "Unknown"
    try: name = driver.find_element(By.TAG_NAME, "h1").text.strip()
    except: pass
    
    pid = get_product_id(driver, url)
    price, unit = get_price_and_unit(driver)
    sold = get_sold_count(driver)
    desc_data = get_product_description(driver)
    reviews = get_reviews_and_qa(driver)
    
    # --- ĐÓNG GÓI JSON ---
    product = {
        "Danh mục": link_data["category"],
        "Mã sản phẩm (ID)": pid,
        "Tên sản phẩm": name,
        "Giá": price,
        "Đơn vị tính": unit,
        "Đã bán": sold,
        "Mô tả sản phẩm": desc_data["Nội dung đầy đủ"], # Lấy text dài
        "Chi tiết kỹ thuật": desc_data["Thông số tách"], # Lấy dạng bảng key-value
        "Hỏi đáp & Đánh giá": reviews,
        "URL": url
    }
    
    print(f"✅ {name[:20]}... | ID: {pid} | Giá: {price} | Bán: {sold}")
    return product

# ==========================================
# 🚀 PHẦN 3: MAIN
# ==========================================
def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f: links = json.load(f)
    except: print("Chưa có file input"); return

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    # options.add_argument("--headless") # Bật cái này nếu muốn chạy ẩn cho nhanh
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    
    results = []
    print(f"🚀 BẮT ĐẦU CÀO CHI TIẾT (Logic mới dựa trên HTML)...")
    
    for i, link in enumerate(links[:LIMIT]):
        try:
            p = scrape_product(driver, link)
            results.append(p)
        except Exception as e:
            print(f"❌ Lỗi link: {link['url']} - {e}")

        # Checkpoint lưu file
        if (i+1) % 10 == 0:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
                
    driver.quit()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"\n🏁 XONG! Kiểm tra file: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()