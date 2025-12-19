import time
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CẤU HÌNH ---
INPUT_FILE = "categories_urls.csv"       # File đầu vào từ Ngày 1
OUTPUT_FILE = "product_links_raw.json"   # File kết quả của Ngày 2

# --- HÀM CUỘN TRANG (Infinite Scroll) ---
def scroll_to_bottom(driver):
    """
    Cuộn trang cho đến khi không còn sản phẩm mới tải ra nữa.
    """
    print("   🖱️ Đang cuộn trang để tải toàn bộ sản phẩm...", end="", flush=True)
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    no_change_count = 0
    while True:
        # Cuộn xuống cuối
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3) # Chờ 3s cho web tải
        
        # Tính chiều cao mới
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            no_change_count += 1
            # Nếu 2 lần liên tiếp không đổi chiều cao -> Chắc chắn đã hết trang
            if no_change_count >= 2:
                print("\n   ✅ Đã cuộn đến đáy trang.")
                break
        else:
            no_change_count = 0
            print(".", end="", flush=True) # In dấu chấm để biết đang chạy
            
        last_height = new_height

# --- HÀM LẤY LINK TỪ 1 DANH MỤC ---
def get_links_from_category(driver, category_name, category_url):
    print(f"\n📂 Đang xử lý danh mục: {category_name}")
    print(f"   🔗 Link: {category_url}")
    
    try:
        driver.get(category_url)
        time.sleep(5) # Chờ load ban đầu

        # 1. Cuộn hết trang
        scroll_to_bottom(driver)
        
        # 2. Quét tất cả thẻ 'a'
        elements = driver.find_elements(By.TAG_NAME, "a")
        
        links = []
        seen_in_cat = set()

        for elem in elements:
            try:
                href = elem.get_attribute('href')
                
                # --- BỘ LỌC LIÊN KẾT (LINK FILTER) ---
                if href and "pharmacity.vn" in href:
                    # Điều kiện tiên quyết: Phải có đuôi .html và KHÔNG phải danh mục
                    if ".html" in href and "/danh-muc/" not in href:
                        
                        # Điều kiện phụ: Loại bỏ các trang tin tức/blog
                        if not any(x in href for x in ["/goc-suc-khoe/", "/tin-tuc/", "/khuyen-mai/"]):
                            
                            # Làm sạch link: Bỏ tham số ?utm_...
                            clean_link = href.split('?')[0]
                            
                            if clean_link not in seen_in_cat:
                                links.append({
                                    "category": category_name,
                                    "url": clean_link
                                })
                                seen_in_cat.add(clean_link)
            except:
                continue
        
        print(f"   -> 🎉 Tìm thấy {len(links)} sản phẩm.")
        return links

    except Exception as e:
        print(f"   ❌ Lỗi danh mục này: {e}")
        return []

# --- CHƯƠNG TRÌNH CHÍNH ---
def main():
    # 1. Đọc file CSV
    try:
        df = pd.read_csv(INPUT_FILE)
        categories = df.to_dict('records')
        print(f"🚀 BẮT ĐẦU NGÀY 2: Tìm thấy {len(categories)} danh mục cần quét.")
    except FileNotFoundError:
        print(f"❌ LỖI: Không thấy file '{INPUT_FILE}'. Hãy chạy code Ngày 1 trước!")
        return

    # 2. Khởi tạo Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    # options.add_argument("--headless") # Bỏ comment nếu muốn chạy ẩn (nhanh hơn xíu)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    all_results = []

    # 3. Chạy vòng lặp
    for index, cat in enumerate(categories):
        name = cat.get("Category Name")
        url = cat.get("URL")
        
        # Bỏ qua dòng trống nếu có
        if not isinstance(url, str) or len(url) < 10: continue
            
        print(f"\n--- [{index+1}/{len(categories)}] ---")
        
        # Gọi hàm cào
        cat_links = get_links_from_category(driver, name, url)
        all_results.extend(cat_links)
        
        # Lưu tạm (Checkpoint) sau mỗi danh mục -> Để lỡ mất mạng thì không mất hết
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)
            
        time.sleep(2) # Nghỉ chút

    driver.quit()

    # 4. Tổng kết
    print("\n" + "="*40)
    print(f"🏁 HOÀN THÀNH NGÀY 2!")
    print(f"📊 Tổng số link thu thập được: {len(all_results)}")
    print(f"💾 Đã lưu vào file: {OUTPUT_FILE}")
    
    if len(all_results) > 1000:
        print("✅ BẠN ĐÃ ĐẠT CHỈ TIÊU > 1000 LINK! Sẵn sàng cho Ngày 3.")
    else:
        print("⚠️ Số lượng hơi ít. Hãy kiểm tra lại xem trang web có chặn cuộn không.")

if __name__ == "__main__":
    main()