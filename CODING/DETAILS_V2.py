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
OUTPUT_FILE = "products_final_success.json"

# ==========================================
# 🧱 PHẦN 1: CÁC HÀM XỬ LÝ SỐ LIỆU (HELPER)
# ==========================================

def text_to_number(raw_text):
    """
    Chuyển đổi text sang số nguyên.
    Input: "91.8k", "Đã bán 6.8k", "1.2tr"
    Output: 91800, 6800, 1200000
    """
    try:
        # 1. Làm sạch chuỗi
        clean_text = raw_text.lower().strip()
        clean_text = clean_text.replace("đã bán", "").replace("lượt thích", "").strip()
        
        # 2. Xác định hệ số nhân
        multiplier = 1
        if "k" in clean_text:
            multiplier = 1000
            clean_text = clean_text.replace("k", "")
        elif "tr" in clean_text or "m" in clean_text:
            multiplier = 1000000
            clean_text = clean_text.replace("tr", "").replace("m", "")
            
        # 3. Thay dấu phẩy thành chấm (nếu có)
        clean_text = clean_text.replace(",", ".")
        
        # 4. Tách lấy số và nhân
        match = re.search(r"(\d+(\.\d+)?)", clean_text)
        if match:
            number_val = float(match.group(1))
            return int(number_val * multiplier)
    except:
        pass
    return 0

# ==========================================
# 🏭 PHẦN 2: CÁC HÀM CÀO DỮ LIỆU (WORKERS)
# ==========================================

def get_product_id(driver, url):
    """Lấy ID sản phẩm chính xác dựa trên vị trí 'Thương hiệu'"""
    # Cách 1: Ưu tiên URL
    if "-p" in url:
        match = re.search(r'-p(\d+)', url)
        if match: return "P" + match.group(1)
        
    # Cách 2: Tìm thẻ p đứng trước thẻ a chứa chữ 'Thương hiệu'
    try:
        xpath = "//a[contains(text(), 'Thương hiệu')]/preceding-sibling::p"
        id_elem = driver.find_element(By.XPATH, xpath)
        return id_elem.text.strip()
    except:
        pass
        
    # Cách 3: Tìm theo text "Mã sản phẩm"
    try:
        elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Mã sản phẩm')]")
        if ":" in elem.text:
            return elem.text.split(":")[-1].strip()
    except:
        return "Unknown"

def get_price_and_unit(driver):
    """Lấy Giá và Đơn vị tính"""
    price = 0
    unit = "Hộp/Chai"
    try:
        price_elem = driver.find_element(By.XPATH, "//*[contains(text(), '₫')]")
        raw_text = price_elem.text.strip()
        clean = raw_text.replace(".", "").replace(",", "")
        
        if "/" in clean:
            parts = clean.split("/", 1)
            # Lấy số từ phần giá
            p_part = re.findall(r'\d+', parts[0])
            if p_part: price = int("".join(p_part))
            unit = parts[1].strip()
        else:
            p_part = re.findall(r'\d+', clean)
            if p_part: price = int("".join(p_part))
    except: pass
    return price, unit

def get_sold_count(driver):
    """Lấy số lượng đã bán"""
    try:
        elem = driver.find_element(By.XPATH, "//p[contains(text(), 'Đã bán')]")
        return text_to_number(elem.text)
    except:
        return 0

def get_like_count(driver):
    """Lấy lượt yêu thích (Tìm trong div có class space-x-1)"""
    try:
        xpath = "//div[contains(@class, 'space-x-1') and contains(@class, 'text-sm')]/p"
        like_elem = driver.find_element(By.XPATH, xpath)
        return text_to_number(like_elem.text)
    except:
        return 0

def get_product_description(driver):
    """Lấy mô tả từ id='mo-ta'"""
    details = {}
    full_text = ""
    try:
        desc_box = driver.find_element(By.ID, "mo-ta")
        full_text = desc_box.text.strip()
        
        # Tách bảng thông số nếu có thẻ li chứa dấu :
        rows = desc_box.find_elements(By.TAG_NAME, "li")
        for row in rows:
            txt = row.text
            if ":" in txt:
                parts = txt.split(":", 1)
                details[parts[0].strip()] = parts[1].strip()
    except: pass
    return {"Nội dung đầy đủ": full_text, "Thông số tách": details}

def get_reviews(driver):
    """Lấy bình luận từ id='comment'"""
    reviews = []
    try:
        element = driver.find_element(By.ID, "comment")
        driver.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(1)
        
        comments = element.find_elements(By.XPATH, ".//div[contains(@class, 'whitespace-break-spaces')]")
        for cmt in comments:
            txt = cmt.text.strip()
            if txt and "Pharmacity xin chào" not in txt:
                reviews.append(txt)
                if len(reviews) >= 5: break
    except: pass
    return reviews

# ==========================================
# 🚀 PHẦN 3: HÀM QUẢN LÝ (CONTROLLER)
# ==========================================

def scrape_product(driver, link_data):
    url = link_data["url"]
    driver.get(url)
    
    # Chờ giá tiền hiện ra (Dấu hiệu trang đã load xong)
    try: WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '₫')]")))
    except: pass

    # --- 1. GỌI WORKERS ---
    name = "Unknown"
    try: name = driver.find_element(By.TAG_NAME, "h1").text.strip()
    except: pass
    
    pid = get_product_id(driver, url)
    price, unit = get_price_and_unit(driver)
    sold = get_sold_count(driver)
    likes = get_like_count(driver)
    desc_data = get_product_description(driver)
    reviews = get_reviews(driver)
    
    # --- 2. ĐÓNG GÓI JSON ---
    product = {
        "Danh mục": link_data["category"],
        "Mã sản phẩm (ID)": pid,
        "Tên sản phẩm": name,
        "Giá": price,
        "Đơn vị tính": unit,
        "Đã bán": sold,
        "Lượt yêu thích": likes,
        "Mô tả sản phẩm": desc_data["Nội dung đầy đủ"],
        "Chi tiết kỹ thuật": desc_data["Thông số tách"],
        "Hỏi đáp & Đánh giá": reviews,
        "URL": url
    }
    
    # In ra kiểm tra
    print(f" {name[:20]}... | ID:{pid} | Giá:{price} | Bán:{sold} | :{likes}")
    return product

# ==========================================
# 🏁 PHẦN 4: CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    # 1. Kiểm tra file đầu vào
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f: links = json.load(f)
        total_links = len(links)
        print(f" BẮT ĐẦU CHIẾN DỊCH: Sẽ quét toàn bộ {total_links} sản phẩm.")
    except: 
        print(f" Lỗi: Không tìm thấy file {INPUT_FILE}")
        return

    # 2. Cấu hình Chrome (HEADLESS MODE - Chạy ngầm)
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--headless") # <--- QUAN TRỌNG: Bật cái này để chạy ngầm cho nhanh
    options.add_argument("--log-level=3") # Tắt bớt log rác của Chrome
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    results = []
    
    # 3. Vòng lặp chính (CHẠY HẾT, KHÔNG LIMIT)
    for i, link in enumerate(links):
        try:
            print(f"[{i+1}/{total_links}] ", end="")
            p = scrape_product(driver, link)
            results.append(p)
        except Exception as e:
            print(f" Lỗi link: {link['url']} - {e}")

        # 4. Lưu Checkpoint (An toàn là trên hết)
        # Cứ 10 sản phẩm thì lưu file 1 lần.
        if (i+1) % 10 == 0:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
                
    driver.quit()
    
    # 5. Lưu lần cuối cùng
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"\n XUẤT SẮC! Đã hoàn thành quét {len(results)}/{total_links} sản phẩm.")
    print(f" Dữ liệu đã lưu tại: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()