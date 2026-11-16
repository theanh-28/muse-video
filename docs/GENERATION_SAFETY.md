# Generation, credentials and budget safeguards

- Muse2API là gateway cộng đồng không chính thức. Chỉ chạy localhost, không expose public interface.
- Cookie/session có quyền truy cập tài khoản: xem như password. Không log cookie, không commit cookie, không cho agent gửi cookie vào prompt hoặc file dự án.
- Ưu tiên một tài khoản và một request thử nghiệm. Không bật multi-account rotation để né rate limit/usage controls.
- Không giả định 1B referral Additional Tokens được trừ hoặc được chia sẻ qua gateway. Chụp/ghi usage trước và sau một test có kiểm soát.
- Đặt giới hạn concurrency thấp (mặc định 1) cho shot phụ thuộc continuity.
- Có max retries (mặc định 1 cho lỗi generation; không retry vô hạn).
- Khi 401/403/session-expired/provider schema changed: dừng queue và báo; không tự động re-login hay xoay tài khoản để né chặn.
- Trước batch generation, tạo manifest và yêu cầu xác nhận người dùng.
- Giới hạn kích thước file, kiểm tra MIME/container và lưu media ở thư mục riêng.
- Tuân thủ điều khoản sử dụng dịch vụ, quyền sở hữu nội dung đầu vào và quyền sử dụng giọng/nhân vật.
