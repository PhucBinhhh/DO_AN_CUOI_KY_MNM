import time
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CẤU HÌNH ---
INPUT_FILE = "categories_urls.csv"
OUTPUT_FILE = "product_links_raw.json"

# --- HÀM 1: TẢI SẢN PHẨM (CUỘN + BẤM NÚT "XEM THÊM") ---
def load_more_products(driver):
    print("   🖱️ Đang tải sản phẩm...", end="", flush=True)
    
    no_change_count = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        # 1. Cuộn xuống cuối trang
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # 2. Tìm và bấm nút "Xem thêm" (Nếu có)
        try:
            # Tìm nút bấm có chữ 'Xem thêm' (bất kể là button hay div)
            see_more_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Xem thêm')]")
            
            if see_more_btn.is_displayed():
                # Dùng JS click để chắc chắn ăn
                driver.execute_script("arguments[0].click();", see_more_btn)
                print(" [Bấm nút]", end="", flush=True)
                time.sleep(3) # Chờ tải sau khi bấm
                no_change_count = 0 # Reset đếm lỗi vì đã bấm được nút
                continue # Quay lại đầu vòng lặp
        except:
            pass # Không thấy nút thì thôi, kiểm tra cuộn trang

        # 3. Nếu không có nút, kiểm tra xem chiều cao trang có tăng không (Infinite Scroll)
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            no_change_count += 1
            # Nếu 3 lần liên tiếp không có gì mới -> Hết trang
            if no_change_count >= 3:
                print("\n   ✅ Đã tải hết trang.")
                break
        else:
            no_change_count = 0
            print(".", end="", flush=True)
            
        last_height = new_height

# --- HÀM 2: CÀO LINK TỪ DANH MỤC ---
def get_links_from_category(driver, category_name, category_url):
    print(f"\n📂 Đang xử lý: {category_name}")
    print(f"   🔗 Link: {category_url}")
    
    try:
        driver.get(category_url)
        time.sleep(5) 

        # --- GỌI HÀM TẢI SẢN PHẨM MỚI (Đã sửa tên hàm ở đây) ---
        load_more_products(driver)
        
        # --- BẮT ĐẦU LẤY LINK ---
        elements = driver.find_elements(By.TAG_NAME, "a")
        
        links = []
        seen = set()

        for elem in elements:
            try:
                href = elem.get_attribute('href')
                
                if href and "pharmacity.vn" in href:
                    if ".html" in href and "/danh-muc/" not in href:
                        # Lọc rác
                        if not any(x in href for x in ["/tin-tuc/", "/khuyen-mai/", "/goc-suc-khoe/"]):
                            clean_link = href.split('?')[0]
                            if clean_link not in seen:
                                links.append({
                                    "category": category_name,
                                    "url": clean_link
                                })
                                seen.add(clean_link)
            except:
                continue
        
        print(f"   -> 🎉 Tìm thấy {len(links)} sản phẩm.")
        return links

    except Exception as e:
        print(f"   ❌ Lỗi tại danh mục này: {e}")
        return []

# --- MAIN ---
def main():
    try:
        df = pd.read_csv(INPUT_FILE)
        categories = df.to_dict('records')
    except:
        print(f"❌ Không tìm thấy file {INPUT_FILE}")
        return

    # Mở trình duyệt
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    all_results = []

    for index, cat in enumerate(categories):
        name = cat.get("Category Name")
        url = cat.get("URL")
        
        # Bỏ qua dòng trống
        if not isinstance(url, str) or len(url) < 10: continue
            
        print(f"\n--- [{index+1}/{len(categories)}] ---")
        
        results = get_links_from_category(driver, name, url)
        all_results.extend(results)
        
        # Lưu file liên tục (để lỡ lỗi không mất hết)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)
            
        time.sleep(2)

    driver.quit()
    print("\n" + "="*40)
    print(f"🏁 TỔNG KẾT NGÀY 2: {len(all_results)} LINK SẢN PHẨM.")
    print(f"💾 File kết quả: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()