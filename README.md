# DO_AN_CUOI_KY_MNM

FOLDER test nằm trong code là để test code trước khi chạy trên toàn bộ dữ liệu
Bên trong folder test sẽ có:
    + medicine_prices_hunted.json : code lấy giá trong cmt
    + CODING\test\products_test_50.json : file lấy thử 50 sản phẩm có DETAILS_V2.py, lúc này chưa lấy được giá của hơn 3500 sản phẩm + link hình ảnh
    + CODING\test\t3st.py: dùng để chạy thử nghiệm các code trước khi để vào file hoàn thiện

CODING\CATEGORIES.py: dùng để cào các danh mục có sản phẩm trong web Pharmacity 
CODING\categories_urls.csv: file lưu link các danh mục thuận tiện cho các code sau này
CODING\PRODUCTS.py: code này để lấy link URL các tất cả các sản phẩm ( hơn 1 tiếng 30p ) 
CODING\product_links_raw.json: file json chưa link URL all sản phẩm
CODING\DETAILS_V2.py: code này cào được khoảng 70% yêu cầu, chưa lấy được giá của tất cả sản phẩm, link hình ảnh,.. (gần 4 tiếng )
CODING\products_final_success.json: file json chứa thông tin code DETAILS_V2
CODING\DETAILS.py: code này chỉ cào được giá, tên sản phẩm còn khá nghèo nàn dữ liệu 
CODING\FILTER_ZERO.py: code này để lấy ra các sản phẩm có giá =0
CODING\products_missing_price.json: file json chứa các sản phẩm có giá =0




lúc trước đã lấy được file gồm 6523 sản phẩm. nhưng có hơn 3500 sản phẩm ko có giá, bây giờ đã tách các sản phẩm có giá =0 giá 1 file json khác, bây sẽ chạy hàm tìm giá đã cải tiến lại trên cả 2 file có giá và thiếu giá, vì trong file thiếu giá, có thể hôm trước chạy thì web chưa cập nhất giá vào, mà hôm nay web đã cập nhất giá lại vào các sản phẩm đó 
