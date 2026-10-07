---
name: refund-policy
description: Xác định chính sách hoàn tiền áp dụng cho một đơn hàng theo ngày mua và kết luận khách có được hoàn tiền không, phí bao nhiêu. Dùng khi người dùng hỏi về hoàn tiền, trả hàng, refund hoặc chính sách hoàn tiền của một đơn hàng.
---

# Refund policy

Hướng dẫn chọn đúng phiên bản chính sách hoàn tiền và kết luận cho một yêu cầu hoàn tiền.

## Các bước

1. Kiểm tra đủ 3 thông tin trong hội thoại:
   - **Ngày mua**.
   - **Ngày yêu cầu hoàn tiền** (người dùng nói "hôm nay" mà không ghi ngày cụ thể thì hỏi lại ngày).
   - **Tình trạng kích hoạt** sản phẩm (đã kích hoạt hay chưa).

   Thiếu bất kỳ thông tin nào: hỏi lại đúng các thông tin còn thiếu rồi dừng. Không giả định, không kết luận tạm.
2. Tìm file chính sách bằng `list_files`, bắt đầu từ `data/policies`. Nếu thư mục đó không tồn tại, gọi `list_files` với `data` để tìm thư mục chứa chính sách. Không đoán tên file và không dựa vào tên file đã thấy ở hội thoại trước, vì tên file có thể thay đổi.
3. Đọc từng file chính sách bằng `read_file`. Xác định phạm vi áp dụng theo **nội dung** file (ví dụ "áp dụng cho đơn mua trước 01/10/2026"), không theo tên file.
4. Chọn đúng một chính sách có phạm vi chứa ngày mua. Mốc "từ ngày X" bao gồm ngày X; "trước ngày X" không bao gồm ngày X. Nếu không có hoặc có nhiều hơn một chính sách khớp, báo rõ cho người dùng và dừng.
5. Tính số ngày đã qua = ngày yêu cầu − ngày mua (đếm theo lịch, ví dụ 28/09 → 06/10 là 8 ngày).
6. Kết luận theo chính sách đã chọn:
   - Sản phẩm đã kích hoạt → không đủ điều kiện.
   - Số ngày đã qua lớn hơn thời hạn → không đủ điều kiện. Bằng thời hạn vẫn đủ điều kiện.
   - Đủ điều kiện → nêu phí hoàn tiền đúng như chính sách ghi.
7. Đọc `references/answer-template.md` trong thư mục skill này, tức `skills/refund-policy/references/answer-template.md`, và trả lời theo đúng template. Ghi đường dẫn file chính sách đã dùng theo kết quả `list_files`/`read_file`.
