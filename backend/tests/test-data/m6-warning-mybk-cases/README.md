# M6 myBK warning test cases

Các file `.txt` trong thư mục này mô phỏng nội dung copy từ trang Bảng điểm myBK, có đủ các học kỳ từ `251` trở về `221`.

## Cách dùng

1. Tạo hoặc dùng một tài khoản sinh viên test sạch.
2. Vào `/student/grades`.
3. Chọn `Cập nhật từ myBK`.
4. Mở một file testcase, copy toàn bộ nội dung, paste vào modal import.
5. Để test cảnh báo chính thức M6, đăng nhập admin rồi gọi API batch warning trong Swagger `/docs`:

```text
POST /api/v1/warnings/batch-run?semester=251
```

Lưu ý: import myBK chỉ tạo/cập nhật bảng điểm. Warning chính thức được tạo khi warning engine chạy. Nếu dùng cùng một tài khoản cho nhiều testcase, hãy xóa toàn bộ bảng điểm trước khi paste testcase mới để tránh dữ liệu bị cộng dồn.

## Kỳ vọng nhanh

| File | Mục tiêu test | Kỳ vọng chính |
| --- | --- | --- |
| `tc01_safe_high_gpa_no_warning.txt` | Sinh viên an toàn, GPA cao, không F | Không tạo warning |
| `tc02_level1_low_cumulative.txt` | GPA tích lũy dưới 1.20 | Warning level 1 |
| `tc03_level2_low_cumulative.txt` | GPA tích lũy dưới 1.00 | Warning level 2 |
| `tc04_level3_dismissal_gpa.txt` | GPA tích lũy dưới 0.80 | Warning level 3 |
| `tc05_low_latest_semester_only.txt` | GPA tích lũy ổn nhưng HK 251 rất thấp | Theo quy chế: level 1; hiện batch có thể lộ gap vì chưa truyền `semester_gpa` |
| `tc06_borderline_safe_threshold.txt` | Gần ngưỡng cảnh báo nhưng vẫn an toàn | Không warning vì GPA tích lũy >= 1.20 và GPA học kỳ >= 0.80 |
| `tc07_retake_recovered_highest_wins.txt` | F cũ đã học lại đạt điểm cao | Không giữ F cũ trong GPA hiệu lực |
| `tc08_retake_still_failed_unresolved.txt` | Học lại vẫn F, còn môn chưa đạt | Warning level 2 + study plan phải ưu tiên học lại |
| `tc09_special_letters_rt_mt_dt_ch.txt` | RT/MT/DT/CT/VT/CH/KD/VP/HT | Import được, không tính GPA các điểm đặc biệt |
| `tc10_history_escalation_sequence.txt` | Test leo mức theo lịch sử warning | Chạy batch nhiều kỳ liên tiếp để kiểm tra level 1 -> 2 -> 3 |
| `tc11_current_semester_pending_no_gpa.txt` | HK 251 toàn CH, lịch sử tốt | Không được coi GPA HK là 0 |
| `tc12_transfer_exempt_credit_heavy.txt` | MT/DT/RT xen kẽ nhiều học kỳ | Chỉ môn có GPA thật được tính |
| `tc13_retake_multiple_courses_recovered.txt` | Nhiều môn F cũ đã học lại đạt | Highest-wins phục hồi GPA, không giữ F cũ |
| `tc14_many_unresolved_failed_courses.txt` | Nhiều F chưa xử lý dù GPA không quá thấp | Study plan/AI phải nhận diện nợ môn |
| `tc15_low_gpa_no_failed_courses_watch_zone.txt` | Toàn D/D+, không F | Gần ngưỡng cảnh báo, phù hợp test AI watch zone |
| `tc16_latest_semester_below_08_safe_cumulative.txt` | GPA tích lũy tốt, HK mới nhất < 0.8 | Warning level 1 theo GPA học kỳ |
| `tc17_long_low_history_level2_level3_path.txt` | Lịch sử dài GPA thấp | Test leo mức khi chạy nhiều batch |
| `tc18_partial_effective_data_many_ch_old_terms.txt` | Nhiều học kỳ CH/HT, chỉ vài kỳ có điểm thật | Không cold-start, không tính CH thành F |
| `tc19_withdraw_then_pass_later.txt` | RT/F cũ rồi học lại pass | RT bị bỏ qua, lần pass thắng |
| `tc20_excellent_with_current_pending.txt` | GPA rất cao, HK hiện tại chưa có điểm | Risk/cảnh báo phải thấp |

## Seed 20 user test

Script `backend/scripts/seed_m6_test_users.py` tạo 20 sinh viên test và gán lần lượt 20 file testcase:

```bash
docker compose exec backend python -m scripts.seed_m6_test_users
```

Tài khoản đăng nhập:

```text
test1@hcmut.edu.vn  / 04072004  -> tc01
test2@hcmut.edu.vn  / 04072004  -> tc02
...
test20@hcmut.edu.vn / 04072004  -> tc20
```

Nếu cần tạo lại `tc11` đến `tc20`, chạy:

```bash
python3 backend/scripts/generate_m6_extra_cases.py
```

## Kết quả verify parser

Các file đã được kiểm tra bằng `app.services.mybk_parser.parse_mybk_text`; tất cả đều nhận đủ 9 học kỳ từ `251` đến `221`.

| File | Số môn parse được | GPA HK 251 | GPA tích lũy hiệu lực |
| --- | ---: | ---: | ---: |
| `tc01_safe_high_gpa_no_warning.txt` | 48 | 3.66 | 3.38 |
| `tc02_level1_low_cumulative.txt` | 44 | 1.38 | 1.18 |
| `tc03_level2_low_cumulative.txt` | 37 | 1.08 | 0.86 |
| `tc04_level3_dismissal_gpa.txt` | 35 | 0.38 | 0.48 |
| `tc05_low_latest_semester_only.txt` | 43 | 0.43 | 2.64 |
| `tc06_borderline_safe_threshold.txt` | 23 | 1.00 | 1.26 |
| `tc07_retake_recovered_highest_wins.txt` | 44 | 3.22 | 2.48 |
| `tc08_retake_still_failed_unresolved.txt` | 44 | 0.78 | 0.83 |
| `tc09_special_letters_rt_mt_dt_ch.txt` | 45 | 0.00 | 2.89 |
| `tc10_history_escalation_sequence.txt` | 44 | 1.16 | 1.15 |

`tc09` cố tình có HK 251 gần như toàn điểm đặc biệt. Khi tính cảnh báo theo học kỳ, implementation đúng nên coi học kỳ không có GPA hợp lệ là `None`, không phải tự động xem là GPA 0.

Riêng `tc10`, sau khi import vào một tài khoản sạch, chạy lần lượt:

```text
POST /api/v1/warnings/batch-run?semester=231
POST /api/v1/warnings/batch-run?semester=232
POST /api/v1/warnings/batch-run?semester=233
POST /api/v1/warnings/batch-run?semester=241
```

Kỳ vọng: các lần đầu tạo cảnh báo mức 1, sau đó leo mức 2 do lịch sử liên tiếp, rồi mức 3 do tổng số cảnh báo/lịch sử.
