import time
import json
import re
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CẤU HÌNH --- 
INPUT_FILE = "product_links_raw.json"
OUTPUT_FILE = "products_final_random_50.json"
LIMIT = 50 

# ==========================================
# 🧱 PHẦN 1: CÁC HÀM XỬ LÝ SỐ LIỆU
# ==========================================

def text_to_number(raw_text):
    try:
        clean_text = raw_text.lower().strip()
        clean_text = clean_text.replace("đã bán", "").replace("lượt thích", "").strip()
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
# 🕵️ PHẦN 2: CÁC HÀM CÀO DỮ LIỆU (WORKERS)
# ==========================================

def get_product_image(driver):
    """Lấy link ảnh sản phẩm (img.w-full)"""
    try:
        img_elem = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.w-full"))
        )
        src = img_elem.get_attribute("src")
        if not src:
            src = img_elem.get_attribute("srcset")
            if src: src = src.split(",")[-1].strip().split(" ")[0]
        return src
    except: return "No Image"
def get_web_price_and_unit(driver):
    """
    [CẬP NHẬT MỚI] Chiến thuật đa tầng để bắt giá web
    """
    price = 0
    unit = "Hộp/Chai" # Mặc định
    
    try:
        # --- 1. LẤY UNIT TỪ BUTTON (Ưu tiên cao nhất) ---
        try:
            active_unit_btn = driver.find_element(By.CSS_SELECTOR, "button.border-primary-500 span")
            unit = active_unit_btn.text.strip()
        except: pass

        # --- 2. LẤY GIÁ TIỀN (CHIẾN THUẬT ĐA TẦNG) ---
        raw_price_text = ""
        
        # Cách A: Tìm theo Class đặc trưng (Nhanh nhất)
        # Thêm nhiều class phổ biến mà web hay dùng cho giá
        price_selectors = [
            ".text-primary-500.font-bold", 
            ".text-2xl.font-bold",
            "div[class*='text-primary-500']", # Bất kỳ div nào có màu cam chủ đạo
            ".product-price" # Class chung (nếu có)
        ]
        
        for selector in price_selectors:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elems:
                    # Kiểm tra kỹ: Phải có số và phải có ký hiệu tiền
                    txt = el.text.strip()
                    if re.search(r'\d', txt) and ('₫' in txt or 'đ' in txt.lower()):
                        raw_price_text = txt
                        break
                if raw_price_text: break
            except: continue

        # Cách B: (Dự phòng) Nếu Cách A thua, tìm mọi thẻ chứa ký hiệu '₫'
        if not raw_price_text:
            try:
                # Tìm thẻ chứa '₫' nhưng text không quá dài (tránh lấy nhầm bài văn mô tả)
                potential_prices = driver.find_elements(By.XPATH, "//*[contains(text(), '₫') and string-length(text()) < 30]")
                for p in potential_prices:
                    # Ưu tiên lấy thẻ có chứa số
                    if re.search(r'\d', p.text):
                        raw_price_text = p.text.strip()
                        break # Lấy cái đầu tiên tìm thấy (thường là giá chính)
            except: pass

        # --- 3. XỬ LÝ SỐ LIỆU (REGEX CLEANING) ---
        if raw_price_text:
            # Loại bỏ mọi thứ không phải là số (nhưng giữ lại cấu trúc để tách đơn vị nếu cần)
            # Ví dụ: "1.250.000đ / Hộp"
            
            clean_str = raw_price_text.replace(".", "").replace(",", "")
            
            # Regex tìm nhóm số lớn nhất (giá tiền thường là số to nhất)
            matches = re.findall(r'\d+', clean_str)
            if matches:
                # Lấy số dài nhất hoặc nối lại (đề phòng trường hợp lỗi font)
                # Thường giá tiền là số nguyên liền mạch sau khi bỏ dấu chấm
                longest_num = max(matches, key=len) 
                price = int(longest_num)

            # (Fallback) Nếu bước 1 chưa lấy được Unit thì thử cắt từ chuỗi giá
            if "/" in raw_price_text and unit == "Hộp/Chai":
                parts = raw_price_text.split("/")
                if len(parts) > 1:
                    unit = parts[1].strip().split()[0] # Lấy chữ đầu tiên sau dấu /

    except Exception as e:
        # print(f"Lỗi lấy giá: {e}") 
        pass
        
    return price, unit
def hunt_price_in_comments(driver):
    """Săn giá trong comment Admin"""
    candidates = []
    try:
        try:
            cmt_area = driver.find_element(By.ID, "comment")
            driver.execute_script("arguments[0].scrollIntoView();", cmt_area)
            time.sleep(1.5)
        except: return 0

        comment_blocks = driver.find_elements(By.XPATH, "//div[@id='comment']//div[contains(@class, 'whitespace-break-spaces')]")
        target_text = ""
        
        for cmt in comment_blocks:
            text = cmt.text.strip()
            if any(x in text.lower() for x in ["pharmacity", "chào anh/chị", "chào bạn"]):
                target_text = text.lower()
                break 
        
        if not target_text: return 0

        matches = re.findall(r"([\d\.,]+)\s*(?:đ|₫|vnđ)\s*/", target_text)
        for m in matches:
            clean_num = m.replace(".", "").replace(",", "").strip()
            if clean_num.isdigit():
                val = int(clean_num)
                if val > 100: candidates.append(val)
    except Exception: pass

    if candidates: return max(candidates)
    return 0

def get_product_id(driver, url):
    if "-p" in url:
        match = re.search(r'-p(\d+)', url)
        if match: return "P" + match.group(1)
    try:
        xpath = "//a[contains(text(), 'Thương hiệu')]/preceding-sibling::p"
        id_elem = driver.find_element(By.XPATH, xpath)
        return id_elem.text.strip()
    except: return "Unknown"

def get_sold_count(driver):
    try:
        elem = driver.find_element(By.XPATH, "//p[contains(text(), 'Đã bán')]")
        return text_to_number(elem.text)
    except: return 0

def get_like_count(driver):
    try:
        xpath = "//div[contains(@class, 'space-x-1') and contains(@class, 'text-sm')]/p"
        like_elem = driver.find_element(By.XPATH, xpath)
        return text_to_number(like_elem.text)
    except: return 0

def get_product_description(driver):
    details = {}
    full_text = ""
    try:
        desc_box = driver.find_element(By.ID, "mo-ta")
        full_text = desc_box.text.strip()
        rows = desc_box.find_elements(By.TAG_NAME, "li")
        for row in rows:
            txt = row.text
            if ":" in txt:
                parts = txt.split(":", 1)
                details[parts[0].strip()] = parts[1].strip()
    except: pass
    return {"Nội dung đầy đủ": full_text, "Thông số tách": details}

def get_reviews(driver):
    """Lấy bình luận (Bao gồm cả Admin)"""
    reviews = []
    try:
        element = driver.find_element(By.ID, "comment")
        driver.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(0.5)
        comments = element.find_elements(By.XPATH, ".//div[contains(@class, 'whitespace-break-spaces')]")
        for cmt in comments:
            txt = cmt.text.strip()
            if txt: 
                reviews.append(txt)
                if len(reviews) >= 10: break
    except: pass
    return reviews

# ==========================================
# 🚀 PHẦN 3: HÀM QUẢN LÝ (CONTROLLER)
# ==========================================

def scrape_product(driver, link_data):
    url = link_data.get("url") or link_data.get("URL") or link_data.get("link")
    category = link_data.get("category") or link_data.get("Danh mục") or "Unknown"
    
    if not url: return None

    driver.get(url)
    try: WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '₫')]")))
    except: pass

    # 1. LẤY THÔNG TIN CƠ BẢN
    name = "Unknown"
    try: name = driver.find_element(By.TAG_NAME, "h1").text.strip()
    except: pass
    
    pid = get_product_id(driver, url)
    sold = get_sold_count(driver)
    likes = get_like_count(driver)
    desc_data = get_product_description(driver)
    reviews = get_reviews(driver)
    image_url = get_product_image(driver)

    # 2. LOGIC LẤY GIÁ
    # Sử dụng hàm đơn giản get_web_price_and_unit thay vì get_price_details
    price, unit = get_web_price_and_unit(driver)
    source = "Web"
    
    # Nếu Web không có giá -> Săn Comment Admin
    if price == 0:
        if "Thuốc" in category or "Dược" in category:
            hunted_price = hunt_price_in_comments(driver)
            if hunted_price > 0:
                price = hunted_price
                source = "Comment"
                unit = "Hộp/Chai"
            else:
                source = "Không tìm thấy"
        else:
            source = "Không tìm thấy "

    # 3. ĐÓNG GÓI JSON
    product = {
        "CATEGORY": category,
        "ID": pid,
        "PRODUCT_NAME": name,
        "PRICE": price,           # Giá bán
        "PRICE_SOURCE": source,
        "UNIT": unit,             # Đơn vị tính
        "IMAGE": image_url,
        "SOLE_COUNT": sold,
        "LIKES": likes,
        "PRODUCT_DESCRIPTION": desc_data["Nội dung đầy đủ"],
        "Chi tiết kỹ thuật": desc_data["Thông số tách"],
        "FAQ & Reviews": reviews,
        "URL": url
    }
    
    price_display = f"{price}đ" if price > 0 else "❌"
    print(f"✅ {name[:15]}... | {price_display} | Unit: {unit} | {source}")
    return product

# ==========================================
# 🏁 PHẦN 4: CHƯƠNG TRÌNH CHÍNH
# ==========================================

def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f: 
            all_links = json.load(f)
    except: 
        print(f"❌ Lỗi: Không tìm thấy file {INPUT_FILE}")
        return

    # Random 50 sản phẩm
    if len(all_links) > LIMIT:
        print(f"🎲 Đang bốc ngẫu nhiên {LIMIT} sản phẩm...")
        links_to_run = random.sample(all_links, LIMIT)
    else:
        links_to_run = all_links

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--headless") 
    options.add_argument("--log-level=3") 
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    results = []
    
    for i, link in enumerate(links_to_run):
        try:
            print(f"[{i+1}/{len(links_to_run)}] ", end="")
            p = scrape_product(driver, link)
            if p: results.append(p)
        except Exception as e:
            print(f"❌ Lỗi: {e}")

        if (i+1) % 10 == 0:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
                
    driver.quit()
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"\n🎉 HOÀN TẤT! File kết quả: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()