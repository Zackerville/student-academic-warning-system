# 📋 Danh Sách Chức Năng Hệ Thống
## Hệ Thống AI Cảnh Báo Học Tập — ĐH Bách Khoa TPHCM

---

## Phân loại mức ưu tiên

| Mức | Ý nghĩa |
|-----|---------|
| 🔴 **P0** | Bắt buộc — không có thì hệ thống không hoạt động |
| 🟡 **P1** | Quan trọng — nên có để hệ thống hoàn chỉnh |
| 🟢 **P2** | Nên có — tăng giá trị và trải nghiệm |
| ⚪ **P3** | Nếu kịp — điểm cộng cho đồ án |

---

## I. CHỨC NĂNG CHUNG (Cả 2 vai trò)

### A. Xác thực & Phân quyền

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| A1 | **Đăng nhập** | Đăng nhập bằng email/MSSV + mật khẩu. Hệ thống trả JWT token | 🔴 P0 |
| A2 | **Đăng ký tài khoản** | SV tự đăng ký bằng MSSV + email trường. Admin tạo bởi super admin | 🔴 P0 |
| A3 | **Đăng xuất** | Xóa token, kết thúc phiên | 🔴 P0 |
| A4 | **Quên mật khẩu** | Gửi link reset mật khẩu qua email | 🟢 P2 |
| A5 | **Phân quyền RBAC** | Tự động phân biệt giao diện Student vs Admin dựa trên role | 🔴 P0 |

---

## II. CHỨC NĂNG PHÍA SINH VIÊN

### B. Dashboard Sinh Viên

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| B1 | **Tổng quan cá nhân** | Hiển thị: ảnh, tên, MSSV, khoa, ngành, khóa, số tín chỉ tích lũy, GPA tích lũy hiện tại | 🔴 P0 |
| B2 | **Biểu đồ GPA theo học kỳ** | Line chart thể hiện GPA từng HK, kèm đường trung bình. Dễ thấy xu hướng tăng/giảm | 🔴 P0 |
| B3 | **Risk Score hiện tại** | Hiển thị dạng gauge/meter (0-100%) cho biết mức độ nguy cơ học tập do AI đánh giá | 🔴 P0 |
| B4 | **Trạng thái cảnh báo** | Badge hiển thị mức cảnh báo hiện tại: Bình thường / Cảnh báo Mức 1 / Mức 2 / Nguy cơ buộc thôi học | 🔴 P0 |
| B5 | **Thông báo mới nhất** | Hiển thị 3-5 thông báo gần nhất (cảnh báo, nhắc nhở deadline, sự kiện) | 🟡 P1 |
| B6 | **Sự kiện sắp tới** | Danh sách 3-5 sự kiện/deadline gần nhất (thi, nộp bài, sinh hoạt công dân) | 🟡 P1 |

---

### C. Quản Lý Học Tập

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| C1 | **Xem bảng điểm** | Bảng điểm chi tiết theo từng học kỳ: môn, số TC, điểm GK, CK, tổng kết, điểm chữ | 🔴 P0 |
| C2 | **Nhập/cập nhật điểm** | SV tự nhập điểm các môn đang học (điểm GK, CK khi có). Hệ thống tự tính GPA dự kiến | 🔴 P0 |
| C3 | **Đăng ký môn học hiện tại** | SV khai báo danh sách môn đang học trong HK hiện tại (tên môn, số TC) | 🔴 P0 |
| C4 | **Xem GPA tích lũy & dự kiến** | Hiển thị GPA tích lũy hiện tại + GPA dự kiến (nếu đã nhập điểm GK) | 🟡 P1 |
| C5 | **Lịch sử đăng ký môn** | Xem toàn bộ lịch sử môn đã học qua các HK, trạng thái (đạt/rớt/đang học) | 🟢 P2 |

---

### D. AI — Dự Báo & Cảnh Báo

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| D1 | **Xem kết quả dự đoán** | Hiển thị risk_score + risk_level (Thấp/Trung bình/Cao/Rất cao) do AI tính toán | 🔴 P0 |
| D2 | **Xem yếu tố nguy cơ** | Giải thích TẠI SAO risk score cao: "GPA giảm 3 HK liên tiếp", "Rớt 2 môn HK trước",... (Feature importance từ XGBoost) | 🔴 P0 |
| D3 | **Dự đoán kết quả từng môn** | AI dự đoán khả năng pass/fail cho từng môn đang học dựa trên điểm GK + lịch sử | 🟡 P1 |
| D4 | **Xem lịch sử cảnh báo** | Danh sách tất cả cảnh báo đã nhận: ngày, mức độ, lý do, trạng thái (đã xử lý / chưa) | 🔴 P0 |
| D5 | **Chi tiết cảnh báo** | Xem chi tiết 1 cảnh báo: lý do cụ thể, GPA tại thời điểm, khuyến nghị từ hệ thống | 🟡 P1 |

---

### E. AI — Chatbot Tư Vấn

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| E1 | **Chat hỏi đáp quy chế** | SV nhập câu hỏi → AI trả lời dựa trên tài liệu quy chế (RAG). VD: "GPA bao nhiêu bị cảnh báo?" | 🔴 P0 |
| E2 | **Chat tư vấn cá nhân** | AI tư vấn dựa trên DATA CỦA SV đó: "Với GPA hiện tại 1.8, bạn cần cải thiện ít nhất 2 môn..." | 🟡 P1 |
| E3 | **Lịch sử chat** | Xem lại các cuộc hội thoại trước | 🟢 P2 |
| E4 | **Gợi ý câu hỏi** | Hiển thị sẵn các câu hỏi phổ biến để SV click nhanh | 🟢 P2 |

---

### F. Kế Hoạch Học Tập

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| F1 | **Xem kế hoạch gợi ý** | Hệ thống gợi ý chiến lược cho HK tới: nên đăng ký bao nhiêu TC, môn nào nên học lại/cải thiện | 🟡 P1 |
| F2 | **Gợi ý môn học** | Dựa trên lịch sử + pattern SV tương tự: "SV có profile giống bạn thường pass môn X khi học cùng môn Y" | 🟢 P2 |
| F3 | **Gợi ý giảm tải** | Nếu SV đang nguy cơ cao → gợi ý giảm số TC đăng ký, tập trung vào môn quan trọng | 🟢 P2 |

---

### G. Thông Báo & Sự Kiện (SV)

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| G1 | **Xem danh sách thông báo** | Tất cả thông báo: cảnh báo học tập, nhắc deadline, sự kiện, từ admin | 🟡 P1 |
| G2 | **Đánh dấu đã đọc** | Click vào thông báo → đánh dấu đã đọc | 🟡 P1 |
| G3 | **Xem lịch sự kiện** | Calendar view hiển thị: lịch thi, hạn nộp bài, sinh hoạt công dân, đánh giá môn học | 🟡 P1 |
| G4 | **Nhận nhắc nhở tự động** | Push/In-app notification trước deadline 3 ngày và 1 ngày | 🟡 P1 |
| G5 | **Nhận thông báo qua email** | Cảnh báo mức cao (Mức 2+) tự động gửi email | 🟢 P2 |

---

## III. CHỨC NĂNG PHÍA ADMIN (Văn Phòng Đào Tạo)

### H. Dashboard Admin

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| H1 | **Tổng quan hệ thống** | Các con số chính: tổng SV, số SV bị cảnh báo (theo mức), số SV nguy cơ cao, tỷ lệ cảnh báo | 🔴 P0 |
| H2 | **Biểu đồ phân bố risk** | Pie/Bar chart phân bố SV theo mức nguy cơ (Thấp/TB/Cao/Rất cao) | 🔴 P0 |
| H3 | **Biểu đồ cảnh báo theo HK** | Line chart số lượng SV bị cảnh báo qua từng HK → thấy xu hướng | 🟡 P1 |
| H4 | **Top SV nguy cơ cao nhất** | Danh sách 10-20 SV có risk score cao nhất, cần can thiệp ngay | 🔴 P0 |
| H5 | **Thống kê theo khoa/ngành** | So sánh tỷ lệ cảnh báo giữa các khoa, ngành, khóa | 🟡 P1 |

---

### I. Quản Lý Sinh Viên

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| I1 | **Danh sách sinh viên** | Bảng tất cả SV: MSSV, tên, khoa, GPA, mức cảnh báo, risk score. Có phân trang | 🔴 P0 |
| I2 | **Tìm kiếm sinh viên** | Tìm theo MSSV, tên, khoa, ngành | 🔴 P0 |
| I3 | **Lọc sinh viên** | Lọc theo: mức cảnh báo, mức risk, khoa, ngành, khóa, khoảng GPA | 🔴 P0 |
| I4 | **Xem chi tiết 1 SV** | Trang chi tiết: profile, bảng điểm toàn bộ HK, biểu đồ GPA, lịch sử cảnh báo, risk factors, predictions | 🔴 P0 |
| I5 | **Xuất danh sách** | Export danh sách SV cảnh báo ra Excel/CSV | 🟢 P2 |

---

### J. Import Dữ Liệu

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| J1 | **Import danh sách SV** | Upload Excel/CSV chứa: MSSV, tên, khoa, ngành, khóa → tạo tài khoản tự động | 🔴 P0 |
| J2 | **Import bảng điểm** | Upload Excel bảng điểm theo HK: MSSV, mã môn, tên môn, số TC, điểm GK, CK, tổng kết | 🔴 P0 |
| J3 | **Xem lịch sử import** | Danh sách các lần import: ngày, file, số records, trạng thái (thành công/lỗi) | 🟡 P1 |
| J4 | **Xem lỗi import** | Nếu import có lỗi (MSSV trùng, thiếu cột,...) → hiển thị chi tiết để sửa | 🟡 P1 |
| J5 | **Template mẫu** | Download file Excel/CSV mẫu để import đúng format | 🟡 P1 |

---

### K. Quản Lý Cảnh Báo

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| K1 | **Chạy batch prediction** | Nút trigger chạy AI prediction cho tất cả SV (hoặc tự động theo lịch) | 🔴 P0 |
| K2 | **Xem danh sách cảnh báo** | Tất cả cảnh báo đã phát: SV nào, mức nào, ngày nào, lý do, trạng thái | 🔴 P0 |
| K3 | **Duyệt cảnh báo** | Admin xem xét cảnh báo AI → Duyệt gửi / Bỏ qua / Chỉnh sửa trước khi gửi cho SV | 🟡 P1 |
| K4 | **Gửi cảnh báo thủ công** | Admin tự tạo cảnh báo cho 1 SV hoặc nhóm SV cụ thể | 🟡 P1 |
| K5 | **Cấu hình ngưỡng cảnh báo** | Tùy chỉnh: GPA bao nhiêu thì cảnh báo mức 1/2/3, risk score bao nhiêu thì cảnh báo | 🟢 P2 |
| K6 | **Báo cáo cảnh báo** | Xuất báo cáo tổng hợp cảnh báo theo HK (PDF/Excel) | 🟢 P2 |

---

### L. Quản Lý Quy Chế (RAG Documents)

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| L1 | **Upload tài liệu quy chế** | Upload PDF/Word/TXT → hệ thống tự chunk + embed + lưu vector | 🔴 P0 |
| L2 | **Danh sách tài liệu** | Xem tất cả tài liệu đã upload: tên, ngày, số chunks, trạng thái (active/inactive) | 🔴 P0 |
| L3 | **Bật/tắt tài liệu** | Vô hiệu hóa quy chế cũ mà không xóa (khi có quy chế mới thay thế) | 🟡 P1 |
| L4 | **Xóa tài liệu** | Xóa hoàn toàn tài liệu + vectors liên quan | 🟡 P1 |
| L5 | **Thay thế tài liệu** | Upload phiên bản mới → tự động thay thế phiên bản cũ | 🟢 P2 |

---

### M. Quản Lý Sự Kiện & Deadline

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| M1 | **Tạo sự kiện** | Tạo: tiêu đề, mô tả, loại (thi/nộp bài/sinh hoạt/đánh giá), thời gian, đối tượng, bắt buộc hay không | 🟡 P1 |
| M2 | **Danh sách sự kiện** | Xem/sửa/xóa tất cả sự kiện đã tạo | 🟡 P1 |
| M3 | **Gửi thông báo sự kiện** | Khi tạo sự kiện → tự động gửi thông báo cho SV liên quan | 🟡 P1 |
| M4 | **Cấu hình nhắc nhở** | Tùy chỉnh nhắc trước bao nhiêu ngày cho từng loại sự kiện | 🟢 P2 |

---

### N. Thống Kê & Báo Cáo

| # | Chức năng | Mô tả chi tiết | Ưu tiên |
|---|-----------|----------------|---------|
| N1 | **Thống kê GPA toàn trường** | Phân bố GPA theo khoa, ngành, khóa (histogram) | 🟡 P1 |
| N2 | **Thống kê cảnh báo** | Số SV bị cảnh báo theo thời gian, theo khoa, so sánh giữa các HK | 🟡 P1 |
| N3 | **Hiệu quả hệ thống** | Bao nhiêu SV được cảnh báo sớm → cải thiện GPA thành công (nếu có data) | 🟢 P2 |
| N4 | **Xuất báo cáo PDF** | Xuất báo cáo tổng hợp dạng PDF để nộp cho ban giám hiệu | ⚪ P3 |

---

## Tổng Hợp

| Nhóm | Số chức năng | P0 | P1 | P2 | P3 |
|------|-------------|----|----|----|----|
| **A. Xác thực** | 5 | 3 | 0 | 1 | 0 |
| **B. Dashboard SV** | 6 | 4 | 2 | 0 | 0 |
| **C. Quản lý học tập** | 5 | 3 | 1 | 1 | 0 |
| **D. AI Dự báo** | 5 | 3 | 2 | 0 | 0 |
| **E. Chatbot** | 4 | 1 | 1 | 2 | 0 |
| **F. Kế hoạch học tập** | 3 | 0 | 1 | 2 | 0 |
| **G. Thông báo SV** | 5 | 0 | 4 | 1 | 0 |
| **H. Dashboard Admin** | 5 | 3 | 2 | 0 | 0 |
| **I. Quản lý SV** | 5 | 4 | 0 | 1 | 0 |
| **J. Import dữ liệu** | 5 | 2 | 3 | 0 | 0 |
| **K. Quản lý cảnh báo** | 6 | 2 | 2 | 2 | 0 |
| **L. Quản lý quy chế** | 5 | 2 | 2 | 1 | 0 |
| **M. Sự kiện & Deadline** | 4 | 0 | 3 | 1 | 0 |
| **N. Thống kê** | 4 | 0 | 2 | 1 | 1 |
| **TỔNG** | **67** | **27** | **25** | **13** | **1** |

> [!TIP]
> **Chiến lược triển khai:**
> - **Sprint 1**: Hoàn thành tất cả **27 chức năng P0** → hệ thống chạy được cơ bản
> - **Sprint 2**: Thêm **25 chức năng P1** → hệ thống hoàn chỉnh
> - **Sprint 3**: Thêm **P2 + P3** nếu còn thời gian → hệ thống chuyên nghiệp
