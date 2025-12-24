# DO_AN_CUOI_KY_MNM

FOLDER test nằm trong code là để test code trước khi chạy trên toàn bộ dữ liệu
Bên trong folder test sẽ có:
    + medicine_prices_hunted.json : code lấy giá trong cmt
    + CODING\test\products_test_50.json : file lấy thử 50 sản phẩm có DETAILS_V2.py, lúc này chưa lấy được giá của hơn 3500 sản phẩm + link hình ảnh
    + CODING\test\t3st.py: dùng để chạy thử nghiệm các code trước khi để vào file hoàn thiện
    + CODING\test\last_demo.py: đây là bản thử nghiệm cuối cùng trước khi đưa vào chạy toàn bộ sản phẩm

-CODING\CATEGORIES.py: dùng để cào các danh mục có sản phẩm trong web Pharmacity 

-CODING\categories_urls.csv: file lưu link các danh mục thuận tiện cho các code sau này

CODING\PRODUCTS.py: code này để lấy link URL các tất cả các sản phẩm ( hơn 1 tiếng 30p ) 

CODING\product_links_raw.json: file json chưa link URL all sản phẩm

CODING\DETAILS.py: code này chỉ cào được giá, tên sản phẩm còn khá nghèo nàn dữ liệu 

CODING\DETAILS_V2.py: code này cào được khoảng 70% yêu cầu, chưa lấy được giá của tất cả sản phẩm, link hình ảnh,.. (gần 4 tiếng )

CODING\products_final_success.json: file json chứa thông tin code DETAILS_V2

CODING\DETAILS_V3.py: Đây là file code cào dữ liệu hoàn chỉnh nhất.

CODING\products_final_all.json: file json chứa dữ liệu từ code DETAILS_V3

CODING\FIX_PRICE_SOURCE.py: code này có nhiệm vụ là xóa "(Theo Admin/ Bot)" đối với các sản phẩm được cào từ comment

CODING\fix_unit_offline.py: code này sửa lại UNIT của các sản phẩm được cào từ comment, lấy UNIT sau giá được săn từ comment không phải để mặc đinh là Hôp/Chai

CODING\fix_unit_detail.py: code này đổi UNIT bom => bom tiem, UNIT của sản phẩm Follitrope Prefilled Syringe 150IU BT 0.3ML => Hộp

CODING\FILTER_ZERO.py: code này để lấy ra các sản phẩm có giá =0

CODING\products_missing_price.json: file json chứa các sản phẩm có giá =0

toMONGODB.py: chuyển từ file json thành database MONGODB để thực hiện truy vấn phân tích 


lúc trước đã lấy được file gồm 6523 sản phẩm. nhưng có hơn 3500 sản phẩm ko có giá, bây giờ đã tách các sản phẩm có giá =0 giá 1 file json khác, bây sẽ chạy hàm tìm giá đã cải tiến lại trên cả 2 file có giá và thiếu giá, vì trong file thiếu giá, có thể hôm trước chạy thì web chưa cập nhất giá vào, mà hôm nay web đã cập nhất giá lại vào các sản phẩm đó 
