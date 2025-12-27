import time
import json
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CẤU HÌNH --- 
INPUT_FILE = "product_links_raw.json"
OUTPUT_FILE = "products_final_all.json" # File kết quả bạn đang dùng

# ==========================================
# 🧱 PHẦN 1: CÁC HÀM XỬ LÝ 
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

def get_product_image(driver):
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
    price = 0
    unit = "Hộp/Chai"
    try:
        try:
            active_unit_btn = driver.find_element(By.CSS_SELECTOR, "button[class*='border-primary-500'] span")
            unit = active_unit_btn.text.strip()
        except: pass

        raw_price_text = ""
        price_selectors = [
            ".text-primary-500.font-bold", 
            ".text-2xl.font-bold",
            "div[class*='text-primary-500']",
            ".product-price",
            "//div[contains(text(), '₫')]"
        ]
        
        for selector in price_selectors:
            try:
                if selector.startswith("//"):
                    elems = driver.find_elements(By.XPATH, selector)
                else:
                    elems = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for el in elems:
                    txt = el.text.strip()
                    if re.search(r'\d', txt) and any(s in txt.lower() for s in ['₫', 'đ', 'vnđ']) and len(txt) < 50:
                        raw_price_text = txt
                        break
                if raw_price_text: break
            except: continue

        if raw_price_text:
            clean_str = raw_price_text.replace(".", "").replace(",", "")
            matches = re.findall(r'\d+', clean_str)
            if matches:
                longest_num = max(matches, key=len) 
                price = int(longest_num)

            if "/" in raw_price_text and unit == "Hộp/Chai":
                parts = raw_price_text.split("/")
                if len(parts) > 1:
                    unit = parts[1].strip().split()[0]
    except: pass
    return price, unit

def hunt_price_in_comments(driver):
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
    except: pass
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

def scrape_product(driver, link_data):
    url = link_data.get("url") or link_data.get("URL") or link_data.get("link")
    category = link_data.get("category") or link_data.get("Danh mục") or "Unknown"
    
    if not url: return None

    driver.get(url)
    try: WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '₫')]")))
    except: pass

    # Lấy thông tin
    name = "Unknown"
    try: name = driver.find_element(By.TAG_NAME, "h1").text.strip()
    except: pass
    
    pid = get_product_id(driver, url)
    sold = get_sold_count(driver)
    likes = get_like_count(driver)
    desc_data = get_product_description(driver)
    reviews = get_reviews(driver)
    image_url = get_product_image(driver)
    price, unit = get_web_price_and_unit(driver)
    source = "Web"
    
    if price == 0:
        if "Thuốc" in category or "Dược" in category:
            hunted_price = hunt_price_in_comments(driver)
            if hunted_price > 0:
                price = hunted_price
                source = "Comment"
                unit = "Hộp/Chai"
            else: source = "Không tìm thấy"
        else: source = "Không tìm thấy"

    product = {
        "CATEGORY": category,
        "ID": pid,
        "PRODUCT_NAME": name,
        "PRICE": price,
        "PRICE_SOURCE": source,
        "UNIT": unit,
        "IMAGE": image_url,
        "SOLE_COUNT": sold,
        "LIKES": likes,
        "PRODUCT_DESCRIPTION": desc_data["Nội dung đầy đủ"],
        "Chi tiết kỹ thuật": desc_data["Thông số tách"],
        "FAQ & Reviews": reviews,
        "URL": url
    }
    
    price_display = f"{price}đ" if price > 0 else ""
    print(f" {name[:15]}... | {price_display} | Unit: {unit} | {source}")
    return product

# ==========================================
#  PHẦN 4: CHƯƠNG TRÌNH CHÍNH (SMART RESUME)
# ==========================================

def init_driver():
    """Hàm bật trình duyệt"""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--headless") 
    options.add_argument("--log-level=3") 
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def main():
    # 1. Load danh sách link gốc
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f: 
            all_links = json.load(f)
        total_links = len(all_links)
    except: 
        print(f" Lỗi: Không tìm thấy file {INPUT_FILE}")
        return

    # 2. Load dữ liệu ĐÃ LÀM (nếu có)
    results = []
    processed_urls = set() # Dùng set để tìm kiếm cho nhanh
    
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                results = json.load(f)
                # Lưu các URL đã làm vào set
                for p in results:
                    if "URL" in p: processed_urls.add(p["URL"])
            print(f" Đã tìm thấy file cũ: {len(results)} sản phẩm đã xong.")
        except:
            print(" File cũ bị lỗi hoặc rỗng, sẽ chạy lại từ đầu.")
            results = []

    # 3. Lọc ra các link CHƯA LÀM
    links_to_run = []
    for link in all_links:
        url = link.get("url") or link.get("URL")
        if url and url not in processed_urls:
            links_to_run.append(link)
            
    if not links_to_run:
        print(" TẤT CẢ SẢN PHẨM ĐÃ ĐƯỢC CÀO XONG! KHÔNG CẦN CHẠY NỮA.")
        return

    print(f" BẮT ĐẦU CHIẾN DỊCH: Còn {len(links_to_run)}/{total_links} sản phẩm chưa cào.")
    print("---------------------------------------------------")

    driver = init_driver()
    
    # 4. Chạy vòng lặp
    for i, link in enumerate(links_to_run):
        try:
            # Hiển thị tiến độ thực tế
            print(f"[{i+1}/{len(links_to_run)}] ", end="")
            
            # --- CƠ CHẾ AUTO-RESET DRIVER (Mỗi 100 cái reset 1 lần để chống tràn RAM) ---
            if i > 0 and i % 100 == 0:
                print(f"\n  [RAM CLEANER] Khởi động lại trình duyệt...")
                try: driver.quit()
                except: pass
                time.sleep(2)
                driver = init_driver()

            try:
                p = scrape_product(driver, link)
                if p: 
                    results.append(p)
                    processed_urls.add(p["URL"]) # Đánh dấu đã làm
            except Exception as e:
                # --- CƠ CHẾ HỒI SINH KHI CRASH ---
                if "invalid session id" in str(e).lower() or "disconnected" in str(e).lower():
                    print(f"\n  TRÌNH DUYỆT BỊ SẬP! Đang hồi sinh...")
                    try: driver.quit()
                    except: pass
                    time.sleep(3)
                    driver = init_driver()
                    # Thử lại 1 lần nữa
                    print(f" Đang thử lại...")
                    p = scrape_product(driver, link)
                    if p: results.append(p)
                else:
                    print(f" Lỗi: {e}")

        except Exception as e:
            print(f" Lỗi hệ thống: {e}")

        # --- LƯU LIÊN TỤC (QUAN TRỌNG) ---
        # Cứ xong 5 cái là lưu ngay, không chờ lâu
        if (i+1) % 5 == 0:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
                
    driver.quit()
    
    # Lưu lần cuối
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"\n HOÀN TẤT TOÀN BỘ! Dữ liệu tại: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()