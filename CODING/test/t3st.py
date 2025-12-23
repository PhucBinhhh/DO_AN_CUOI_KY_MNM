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
OUTPUT_FILE = "medicine_prices_hunted.json"
LIMIT = 50  # Lấy 50 sản phẩm thuốc

# ==========================================
# 🧱 PHẦN 1: CÁC HÀM XỬ LÝ SỐ LIỆU
# ==========================================

def text_to_number(raw_text):
    """Chuyển đổi 9.8k -> 9800, 1.2tr -> 1200000"""
    try:
        clean_text = raw_text.lower().replace("đã bán", "").replace("lượt thích", "").strip()
        multiplier = 1
        if "k" in clean_text:
            multiplier = 1000
            clean_text = clean_text.replace("k", "")
        elif "tr" in clean_text or "m" in clean_text:
            multiplier = 1000000
            clean_text = clean_text.replace("tr", "").replace("m", "")
        clean_text = clean_text.replace(",", ".")
        match = re.search(r"(\d+(\.\d+)?)", clean_text)
        if match:
            return int(float(match.group(1)) * multiplier)
    except: pass
    return 0

# ==========================================
# 🕵️ PHẦN 2: ĐỘI ĐẶC NHIỆM SĂN GIÁ (LOGIC MỚI)
# ==========================================

def hunt_price_in_comments(driver):
    """
    Tìm giá trong comment với chiến thuật:
    Chỉ lấy số đứng trước cụm 'đ/' hoặc '₫/' (Ví dụ: 27.000 ₫/Tuýp)
    Và lấy số LỚN NHẤT tìm được.
    """
    candidates = []
    try:
        # 1. Cuộn xuống phần comment
        try:
            cmt_area = driver.find_element(By.ID, "comment")
            driver.execute_script("arguments[0].scrollIntoView();", cmt_area)
            time.sleep(1.5) 
            full_text = cmt_area.text.lower()
        except:
            return 0 

        # 2. REGEX MỚI: Bắt buộc phải có dấu gạch chéo '/' sau đơn vị tiền
        # Giải thích Regex:
        # ([\d\.,]+) : Nhóm 1 - Bắt các con số (chấp nhận chấm, phẩy)
        # \s* : Chấp nhận khoảng trắng thừa
        # (?:đ|₫|vnđ): Tìm chữ đ, ₫ hoặc vnđ
        # \s* : Khoảng trắng
        # /          : BẮT BUỘC phải có dấu gạch chéo (để khớp với đ/Hộp, đ/Viên)
        matches = re.findall(r"([\d\.,]+)\s*(?:đ|₫|vnđ)\s*/", full_text)
        
        for m in matches:
            # Làm sạch số: "27.000" -> 27000
            clean_num = m.replace(".", "").replace(",", "").strip()
            if clean_num.isdigit():
                val = int(clean_num)
                # Lọc nhiễu: Giá thuốc phải > 100 đồng
                if val > 100: 
                    candidates.append(val)

    except Exception as e:
        print(f"   ⚠️ Lỗi săn giá: {e}")

    # 3. Logic chọn giá: Lấy giá CAO NHẤT
    # Ví dụ tìm được: [2700, 27000] (giá tép và giá hộp) -> Lấy 27000
    if candidates:
        return max(candidates)
    
    return 0

# ==========================================
# 🏭 PHẦN 3: CÁC HÀM CÀO CƠ BẢN
# ==========================================

def get_product_id(driver, url):
    if "-p" in url:
        m = re.search(r'-p(\d+)', url)
        if m: return "P" + m.group(1)
    try:
        xpath = "//a[contains(text(), 'Thương hiệu')]/preceding-sibling::p"
        return driver.find_element(By.XPATH, xpath).text.strip()
    except: return "Unknown"

def get_sold_count(driver):
    try:
        return text_to_number(driver.find_element(By.XPATH, "//p[contains(text(), 'Đã bán')]").text)
    except: return 0

def get_reviews(driver):
    reviews = []
    try:
        cmts = driver.find_elements(By.XPATH, "//div[@id='comment']//div[contains(@class, 'whitespace-break-spaces')]")
        for c in cmts:
            t = c.text.strip()
            if t and "Pharmacity xin chào" not in t:
                reviews.append(t)
                if len(reviews) >= 3: break
    except: pass
    return reviews

# ==========================================
# 🚀 PHẦN 4: HÀM QUẢN LÝ (CONTROLLER)
# ==========================================

def scrape_medicine(driver, link_data):
    url = link_data["url"]
    category = link_data["category"]
    
    # Chỉ làm việc với danh mục Thuốc
    if "Thuốc" not in category and "Dược" not in category:
        return None 

    driver.get(url)
    try: WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    except: pass

    # 1. Thử lấy giá Web
    price = 0
    unit = "Hộp/Chai"
    source = "Web"
    
    try:
        price_elem = driver.find_element(By.XPATH, "//*[contains(text(), '₫')]")
        raw_price = price_elem.text.strip()
        clean = raw_price.replace(".", "").replace(",", "")
        p_match = re.search(r'(\d+)', clean)
        if p_match: price = int(p_match.group(1))
    except: 
        price = 0

    # 2. Nếu không có giá Web -> Dùng chiến thuật săn "đ/"
    if price == 0:
        print("   🔍 Đang tìm giá trong comment (chiến thuật 'đ/')...")
        hunted_price = hunt_price_in_comments(driver)
        
        if hunted_price > 0:
            price = hunted_price
            source = "Comment (Săn được)"
            unit = "Hộp/Chai (Theo comment)"
        else:
            source = "Không tìm thấy"

    # Lấy thông tin khác
    name = "Unknown"
    try: name = driver.find_element(By.TAG_NAME, "h1").text.strip()
    except: pass
    
    product = {
        "Danh mục": category,
        "ID": get_product_id(driver, url),
        "Tên": name,
        "GIÁ CUỐI CÙNG": price,
        "Nguồn giá": source,
        "Đơn vị": unit,
        "Đã bán": get_sold_count(driver),
        "Review mẫu": get_reviews(driver),
        "URL": url
    }
    
    print(f"✅ {name[:20]}... | Giá: {price} ({source})")
    return product

# ==========================================
# 🏁 MAIN
# ==========================================
def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f: links = json.load(f)
    except: print("Chưa có file input"); return

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--headless") 
    options.add_argument("--log-level=3")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    results = []
    medicine_count = 0
    
    print(f"🚀 BẮT ĐẦU: Săn giá 50 sản phẩm thuốc...")
    
    for link in links:
        if medicine_count >= LIMIT:
            break
            
        try:
            p = scrape_medicine(driver, link)
            if p:
                results.append(p)
                medicine_count += 1
                
        except Exception as e:
            print(f"❌ Lỗi: {e}")

    driver.quit()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"\n🏁 XONG! Kiểm tra file: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()