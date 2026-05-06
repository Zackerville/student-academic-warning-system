---
marp: true
theme: default
paginate: true
header: 'AI Warning System — HCMUT'
footer: 'Đồ án chuyên ngành · 2026'
size: 16:9
style: |
  section {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif;
    background: #ffffff;
    color: #1a1d29;
    padding: 48px 56px;
  }
  section img {
    max-width: 100%;
    max-height: 440px;
    display: block;
    margin: 12px auto;
    object-fit: contain;
  }
  section.title {
    background: linear-gradient(135deg, #003e80 0%, #0052a3 100%);
    color: #fff;
    text-align: center;
    justify-content: center;
  }
  section.title h1 {
    color: #fff;
    font-size: 64px;
    margin: 0;
    border: none;
  }
  section.title h2 {
    color: rgba(255,255,255,0.8);
    font-weight: 400;
    border: none;
  }
  section.title p { color: rgba(255,255,255,0.6); }
  section.section {
    background: #003e80;
    color: #fff;
    text-align: center;
    justify-content: center;
  }
  section.section h1 { color: #fff; border: none; font-size: 56px; }
  section.section p { color: rgba(255,255,255,0.7); }
  h1 {
    color: #003e80;
    border-bottom: 3px solid #003e80;
    padding-bottom: 8px;
    font-size: 32px;
  }
  h2 { color: #0052a3; font-size: 24px; }
  strong { color: #003e80; }
  code {
    background: #f1f5f9;
    color: #0052a3;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
  }
  pre {
    background: #1e293b;
    color: #e2e8f0;
    padding: 16px;
    border-radius: 8px;
    font-size: 16px;
    line-height: 1.5;
  }
  pre code { background: transparent; color: inherit; }
  blockquote {
    border-left: 4px solid #003e80;
    padding-left: 16px;
    color: #475569;
    font-style: italic;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 18px;
  }
  th {
    background: #003e80;
    color: #fff;
    padding: 8px 12px;
    text-align: left;
  }
  td { padding: 8px 12px; border-bottom: 1px solid #e2e8f0; }
  tr:nth-child(even) { background: #f8fafc; }
  ul, ol { line-height: 1.6; }
  .columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }
  .metric {
    display: inline-block;
    background: #003e80;
    color: #fff;
    padding: 4px 12px;
    border-radius: 999px;
    font-weight: 600;
    font-size: 16px;
  }
  .metric-good { background: #16a34a; }
  .metric-warn { background: #f97316; }
  .metric-bad { background: #dc2626; }
---

<!-- _class: title -->

# AI Warning System

## Hệ thống cảnh báo học vụ thông minh cho sinh viên

**Trường Đại học Bách Khoa TP.HCM**
Khoa Khoa học và Kỹ thuật Máy tính

SVTH: *(Tên sinh viên)* · MSSV: *(MSSV)*
GVHD: *(Tên GVHD)*

Đồ án chuyên ngành — Học kỳ 2 / 2025-2026

---

# Mục lục

<div class="columns">

**Phần 1: Tổng quan**
1. Bối cảnh & vấn đề
2. Mục tiêu đồ án
3. Phạm vi triển khai
4. Tech stack

**Phần 2: Thiết kế**
5. Kiến trúc hệ thống
6. Layered architecture
7. Database schema
8. Quy chế HCMUT

**Phần 3: AI**
9. XGBoost prediction
10. SHAP explainability
11. RAG chatbot
12. Hybrid retrieval

</div>

<div class="columns">

**Phần 4: Sản phẩm**
13. Module sinh viên
14. Module admin
15. Email + Notification
16. Demo flow

**Phần 5: Đánh giá**
17. Bảo mật
18. Số liệu thống kê
19. Hạn chế
20. Hướng phát triển

</div>

---

<!-- _class: section -->

# Phần 1
## Tổng quan

---

# Bối cảnh

**Trường Đại học Bách Khoa TP.HCM** — quy mô lớn:
- ~30,000 sinh viên đang theo học
- ~15 khoa, hàng trăm chương trình đào tạo
- Quy chế cảnh báo học vụ phức tạp (3 mức + buộc thôi học)

**Quy trình hiện tại:**
- Phòng đào tạo tổng kết điểm cuối kỳ → ban hành quyết định cảnh báo
- Sinh viên **chỉ biết khi đã bị cảnh báo chính thức** (cuối kỳ)
- Không có cơ chế cảnh báo sớm dựa trên dữ liệu giữa kỳ

> Khi sinh viên nhận quyết định cảnh báo, cơ hội cải thiện đã rất hạn chế.

---

# Vấn đề cụ thể

| # | Vấn đề | Hậu quả |
|---|---|---|
| 1 | Cảnh báo **muộn** (cuối học kỳ) | SV không kịp điều chỉnh kế hoạch học |
| 2 | Cảnh báo **rule-based đơn giản** chỉ dựa GPA tích lũy | Bỏ sót SV có pattern nguy cơ rõ rệt nhưng GPA chưa rớt ngưỡng |
| 3 | SV **không hiểu rõ quy chế** + công thức cảnh báo | Mỗi học kỳ phòng đào tạo nhận hàng trăm câu hỏi giống nhau |
| 4 | **Học lại / cải thiện** xử lý sai → GPA tích lũy hiển thị sai | SV nhầm tưởng vẫn an toàn |
| 5 | Phòng đào tạo phải nhập điểm Excel + gửi email thủ công | Tốn thời gian, dễ sót |

---

# Mục tiêu đồ án

**Xây dựng hệ thống web full-stack** giải quyết 5 vấn đề trên:

1. **Cảnh báo sớm bằng AI** — XGBoost dự đoán risk score giữa kỳ, không đợi điểm cuối kỳ
2. **Áp dụng đúng quy chế HCMUT** — bao gồm rule "highest GPA wins" cho học lại / cải thiện
3. **Chatbot RAG** trả lời quy chế tự động bằng tiếng Việt, có trích dẫn tài liệu gốc
4. **Tự động hóa** — admin import Excel, hệ thống tự predict + tạo cảnh báo + gửi email
5. **Giải thích được (XAI)** — mỗi prediction có top yếu tố ảnh hưởng nhờ SHAP

**Đối tượng người dùng:**
- *Sinh viên* — theo dõi, xem cảnh báo, tư vấn AI
- *Admin (Phòng đào tạo)* — vận hành toàn hệ thống

---

# Phạm vi triển khai

| Milestone | Nội dung | Trạng thái |
|---|---|---|
| **M1** | Foundation (DB models, Alembic, Docker) | ✅ Done |
| **M2** | Auth (JWT) + Next.js setup | ✅ Done |
| **M3** | Student profile + Grades + myBK paste | ✅ Done |
| **M4** | AI Prediction — XGBoost + SHAP | ✅ Done |
| **M5** | AI Chatbot — RAG hybrid retrieval | ✅ Done |
| **M6** | Warnings + Study Plan + Events + Email | ✅ Done |
| **M7** | Admin Portal — 8 trang | ✅ Done |
| M8 | Integration & Polish | Tuần 12-13 |
| M9 | Wow features (optional) | Tuần 14 |

> 7/9 milestone hoàn tất, đủ để demo end-to-end cho GVHD.

---

# Tech Stack

<div class="columns">

**Backend**
- FastAPI 0.111 (async)
- Python 3.11
- SQLAlchemy 2 (async)
- Alembic (migrations)
- APScheduler (jobs)
- Pydantic v2

**AI / ML**
- XGBoost 2.1
- SHAP 0.46 (explainability)
- Optuna (hyperparam tuning)
- LangChain
- Google Gemini 2.5 Flash
- pgvector (768-dim embeddings)

</div>

<div class="columns">

**Frontend**
- Next.js 14 (App Router)
- React 18 + TypeScript
- Tailwind CSS + shadcn/ui
- Zustand (state)
- recharts (charts)

**Infrastructure**
- PostgreSQL 16 + pgvector
- Redis 7 (cache)
- Docker Compose
- Gmail SMTP (email)

</div>

---

<!-- _class: section -->

# Phần 2
## Thiết kế hệ thống

---

# Kiến trúc tổng quan

![Mermaid diagram 1](https://mermaid.ink/svg/Zmxvd2NoYXJ0IExSCiAgICBTVlvwn5GkIFNpbmggdmnDqm5dIC0tPiBGRQogICAgQURb8J-RqOKAjfCfkrwgQWRtaW5dIC0tPiBGRQogICAgRkVbTmV4dC5qcyAxNDxici8-QXBwIFJvdXRlciArIFRhaWx3aW5kXSAtLT58SlNPTiAvIFNTRXwgQkUKICAgIEJFW0Zhc3RBUEkgYXN5bmM8YnIvPkpXVCArIFJCQUNdCiAgICBCRSAtLT4gREJbKFBvc3RncmVTUUwgMTY8YnIvPisgcGd2ZWN0b3IpXQogICAgQkUgLS0-IFJDWyhSZWRpcyA3PGJyLz5jYWNoZSldCiAgICBCRSAtLT4gU0NIW0FQU2NoZWR1bGVyPGJyLz5kYWlseSAwMjowMF0KICAgIEJFIC0tPiBBSTFbWEdCb29zdDxici8-UHJlZGljdGlvbl0KICAgIEJFIC0tPiBBSTJbUkFHIENoYXRib3Q8YnIvPkxhbmdDaGFpbiArIEdlbWluaV0KICAgIEFJMiAtLT4gREIKICAgIEJFIC0tPiBTTVRQW0dtYWlsIFNNVFA8YnIvPkppbmphMiB0ZW1wbGF0ZXNdCgogICAgc3R5bGUgRkUgZmlsbDojZGJlYWZlLHN0cm9rZTojMDA1MmEzCiAgICBzdHlsZSBCRSBmaWxsOiNlMGU3ZmYsc3Ryb2tlOiMwMDNlODAKICAgIHN0eWxlIERCIGZpbGw6I2ZlZjNjNyxzdHJva2U6I2Q5NzcwNgogICAgc3R5bGUgQUkxIGZpbGw6I2RjZmNlNyxzdHJva2U6IzE2YTM0YQogICAgc3R5bGUgQUkyIGZpbGw6I2RjZmNlNyxzdHJva2U6IzE2YTM0YQ)

---

# Layered Architecture (rule cứng)

![Mermaid diagram 2](https://mermaid.ink/svg/Zmxvd2NoYXJ0IFRECiAgICBBW2FwcC9hcGkvdjEvKjxici8-SFRUUCBsYXllciDigJQgcm91dGUgaGFuZGxlcnNdCiAgICBTW2FwcC9zZXJ2aWNlcy8qPGJyLz5CdXNpbmVzcyBsb2dpYyDigJQgZ3BhX2NhbGN1bGF0b3IsIHdhcm5pbmdfZW5naW5lLCBpbXBvcnRfc2VydmljZSwgLi4uXQogICAgTVthcHAvbW9kZWxzLyo8YnIvPlNRTEFsY2hlbXkgT1JNIOKAlCAxMCBi4bqjbmddCiAgICBBSVthcHAvYWkvKjxici8-TUwgLyBSQUcg4oCUIFhHQm9vc3QsIExhbmdDaGFpbl0KCiAgICBBIC0tPnxkZXBlbmRzIG9ufCBTCiAgICBTIC0tPnxkZXBlbmRzIG9ufCBNCiAgICBBSSAtLT58ZGVwZW5kcyBvbnwgUwogICAgQUkgLS0-fGRlcGVuZHMgb258IE0KICAgIEEgLS4tPnzinYwgS0jDlE5HIMSRxrDhu6NjfCBBSQoKICAgIHN0eWxlIEEgZmlsbDojZGJlYWZlLHN0cm9rZTojMDA1MmEzCiAgICBzdHlsZSBTIGZpbGw6I2UwZTdmZixzdHJva2U6IzAwM2U4MAogICAgc3R5bGUgTSBmaWxsOiNmZWYzYzcsc3Ryb2tlOiNkOTc3MDYKICAgIHN0eWxlIEFJIGZpbGw6I2RjZmNlNyxzdHJva2U6IzE2YTM0YQ)

> **Rule cứng:** AI/chatbot **KHÔNG** được import từ `app.api.v1.*` để tránh circular import + giữ AI testable độc lập.
> Logic dùng chung (vd "highest GPA wins") nằm ở `services/grade_aggregator.py` — single source of truth.

---

# Database Schema (10 bảng)

![ER diagram](https://mermaid.ink/svg/ZXJEaWFncmFtCiAgICB1c2VycyB8fC0tb3wgc3R1ZGVudHMgOiAiMS0xIgogICAgdXNlcnMgfHwtLW97IGV2ZW50cyA6ICJjcmVhdGVzIgogICAgc3R1ZGVudHMgfHwtLW97IGVucm9sbG1lbnRzIDogIiIKICAgIHN0dWRlbnRzIHx8LS1veyB3YXJuaW5ncyA6ICIiCiAgICBzdHVkZW50cyB8fC0tb3sgcHJlZGljdGlvbnMgOiAiIgogICAgc3R1ZGVudHMgfHwtLW97IG5vdGlmaWNhdGlvbnMgOiAiIgogICAgc3R1ZGVudHMgfHwtLW97IGNoYXRfbWVzc2FnZXMgOiAiIgogICAgY291cnNlcyB8fC0tb3sgZW5yb2xsbWVudHMgOiAiIgogICAgd2FybmluZ3MgfHwtLW98IG5vdGlmaWNhdGlvbnMgOiAiIg)

> Sơ đồ rút gọn — chi tiết từng cột (PK/FK/types/notes) trình bày trong
> [`docs/DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md). Bảng `documents` lưu vector
> 768-dim qua pgvector cho RAG retrieval.

---

# Quy chế HCMUT — Cảnh báo học vụ

| Mức | Điều kiện | Hậu quả |
|---|---|---|
| **Bình thường** | GPA tích lũy ≥ 1.2 và GPA học kỳ ≥ 0.8 | — |
| **Cảnh báo Mức 1** | GPA tích lũy < 1.2 **HOẶC** GPA học kỳ < 0.8 | Email + nhắc nhở |
| **Cảnh báo Mức 2** | GPA tích lũy < 1.0 **HOẶC** 2 lần liên tiếp Mức 1 | Email + cảnh báo nghiêm trọng |
| **Buộc thôi học** | GPA tích lũy < 0.8 **HOẶC** 3 lần cảnh báo / 2 lần Mức 2 | Quyết định kỷ luật |

**Ngoài quy chế:**
- **AI Early Warning** — risk_score ≥ 0.6 → cảnh báo sớm **ngay cả khi chưa vi phạm quy chế**

→ Logic được implement trong `services/warning_engine.py:check_regulation_warning()` (pure function, idempotent).

---

# Quy chế HCMUT — Highest GPA Wins

**Vấn đề:** sinh viên học lại / học cải thiện → có nhiều enrollment cho cùng một môn. Cách tính GPA tích lũy thường:

> ❌ Cách thông thường: lấy lần học **mới nhất**
> ✅ HCMUT đúng: lấy lần học **có điểm cao nhất**

**Implementation** ([`services/grade_aggregator.py`](../backend/app/services/grade_aggregator.py)):

```python
def effective_enrollments_per_course(enrollments):
    """Với mỗi course_id, lấy enrollment có gpa_point cao nhất.
    Trùng điểm → tiebreak bằng học kỳ muộn hơn.
    Toàn RT/MT/DT → fallback lấy lần mới nhất."""
```

**Áp dụng vào 3 chỉ số:**
- `gpa_cumulative` — chỉ tính trên enrollment "winner" của mỗi môn
- `credits_earned` — mỗi môn chỉ tính 1 lần
- `failed_courses_total` — chỉ đếm nếu winner vẫn là F

> **Per-semester GPA KHÔNG dedup** → `/me/gpa/history` show GPA từng học kỳ historical (F vẫn nằm ở HK đó dù sau này đã học lại đạt).

---

<!-- _class: section -->

# Phần 3
## AI / Machine Learning

---

# AI #1: XGBoost Prediction — Pipeline

![Mermaid diagram 4](https://mermaid.ink/svg/Zmxvd2NoYXJ0IExSCiAgICBBW1N5bnRoZXRpYyBEYXRhPGJyLz4xMDAwIFNWIMK3IDY1ayBlbnJvbGxtZW50czxici8-MTYlIHBvc2l0aXZlIGNsYXNzXSAtLT4gQltGZWF0dXJlIEVuZ2luZWVyaW5nPGJyLz4xMSBydWxlLWF3YXJlIGZlYXR1cmVzXQogICAgQiAtLT4gQ1tUcmFpbjxici8-T3B0dW5hIDI1IHRyaWFsczxici8-NS1mb2xkIENWXQogICAgQyAtLT4gRFtUaHJlc2hvbGQgVHVuaW5nPGJyLz52YWwgc2V0XQogICAgRCAtLT4gRVtTYXZlZCBNb2RlbDxici8-MC4xNCBNQiDCtyBqb2JsaWJdCiAgICBFIC0tPiBGW1ByZWRpY3Rpb24gU2VydmljZTxici8-c2luZ2xldG9uIGxvYWQgbGlmZXNwYW5dCiAgICBGIC0tPiBHW0NhbGlicmF0aW9uPGJyLz5ydWxlLWJhc2VkIGZsb29yXQogICAgRyAtLT4gSFtSaXNrIFNjb3JlPGJyLz4wLjAg4oaSIDEuMF0KICAgIEggLS0-IElbU0hBUCBFeHBsYWluZXI8YnIvPnRvcCBmYWN0b3JzIFZJXQogICAgSSAtLT4gSltGRSBEaXNwbGF5PGJyLz5SYWRpYWxCYXIgKyBiYXJzXQoKICAgIHN0eWxlIEUgZmlsbDojZGNmY2U3CiAgICBzdHlsZSBHIGZpbGw6I2ZlZjNjNwogICAgc3R5bGUgSSBmaWxsOiNmY2U3ZjM)

> Báo cáo cần trình bày: **AI = ML + product calibration**, không phải pure XGBoost score.

---

# AI #1: 11 Features (rule-aware, no leakage)

| Feature | Ý nghĩa | Hướng |
|---|---|---|
| `gpa_cumulative_deficit` | GPA tích lũy thiếu so với mốc 2.0 | + tăng risk |
| `gpa_recent_deficit` | GPA HK gần nhất thiếu so với 2.0 | + |
| `gpa_trend_drop` | Phần GPA đang giảm trong 3 HK | + |
| `low_gpa_streak` | Số HK liên tiếp GPA < 2.0 | + |
| `unresolved_failed_courses` | Môn F mà điểm hiệu lực vẫn F | + |
| `unresolved_failed_last_semester` | F ở HK gần nhất vẫn chưa qua | + |
| `unresolved_failed_retake_count` | Học lại nhưng điểm hiệu lực vẫn F | + |
| `withdrawn_count` | Số môn rút | + |
| `pass_rate_deficit` | 1 − tỉ lệ qua môn | + |
| `attendance_risk` | > 0 chỉ khi điểm danh < 75% | + |
| `recovered_failed_courses` | Từng F nhưng đã học lại đạt | **−** |

> **KHÔNG có** `warning_level_current` → tránh **label leakage**.

---

# AI #1: Metrics (test set, retrain 2026-05-04)

<div class="columns">

**Chỉ số chính**

| Metric | Value |
|---|---|
| F1 score | <span class="metric metric-good">0.79</span> |
| AUC-ROC | <span class="metric metric-good">0.98</span> |
| Recall | <span class="metric metric-good">92%</span> |
| Precision | <span class="metric metric-warn">69%</span> |
| Threshold | 0.70 |

**Confusion Matrix (n_test = 150)**

|  | Predict ✗ | Predict ✓ |
|---|---|---|
| Actual ✗ | 116 | 10 |
| Actual ✓ | 2 | **22** |

</div>

<div class="columns">

**Diễn giải**
- **Recall 92%** → bắt được 22/24 SV thực sự cần cảnh báo
- **Precision 69%** → 10/32 cảnh báo là false positive (acceptable cho early warning, vì cost của miss > cost của extra check)
- **AUC 0.98** → model phân tách tốt 2 class trên toàn dải threshold

**Limitation thẳng thắn:**
- Train trên synthetic data 1000 SV — chưa validate trên dữ liệu thực HCMUT
- Cần ground-truth label thực để fine-tune

</div>

---

# AI #1: SHAP Explainability

**Mỗi prediction trả về top 5 yếu tố** ảnh hưởng risk score, normalize sao cho tổng ≈ 100%:

```python
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(features)
# Convert sang (label_vi, impact_pct, direction) cho FE
```

**Ví dụ output cho SV có risk_score = 0.67:**

| # | Yếu tố | Đóng góp | Hướng |
|---|---|---|---|
| 1 | GPA giảm 3 HK liên tiếp | 35% | + (tăng risk) |
| 2 | Số môn F chưa qua | 28% | + |
| 3 | Pass rate thấp | 18% | + |
| 4 | GPA HK gần nhất thiếu | 12% | + |
| 5 | Đã học lại đạt 1 môn F cũ | 7% | **−** (giảm risk) |

> Lọc các SHAP reason ngược trực giác do baseline comparison → chỉ surface yếu tố có nghĩa.

---

# AI #2: RAG Chatbot — Kiến trúc

![Mermaid diagram 5](https://mermaid.ink/svg/Zmxvd2NoYXJ0IFRECiAgICBRW0PDonUgaOG7j2kgU1ZdIC0tPiBFTUJbRW1iZWRkaW5nPGJyLz5HZW1pbmkgbW9kZWxzL2VtYmVkZGluZy0wMDE8YnIvPjc2OCBkaW1zXQogICAgUSAtLT4gS1dbS2V5d29yZCBFeHRyYWN0b3I8YnIvPkhDTVVUIHRlcm1zIHdoaXRlbGlzdF0KCiAgICBFTUIgLS0-IFZTW1ZlY3RvciBTZWFyY2g8YnIvPnBndmVjdG9yIGNvc2luZV9kaXN0YW5jZTxici8-dG9wLUtdCiAgICBLVyAtLT4gS1NbS2V5d29yZCBTZWFyY2g8YnIvPklMSUtFICsgc2NvcmluZyBydWxlc10KCiAgICBWUyAtLT4gTVtIeWJyaWQgTWVyZ2U8YnIvPmRlZHVwIHRoZW8gZG9jX2lkPGJyLz5tYXRjaF90eXBlIHRhZ10KICAgIEtTIC0tPiBNCgogICAgTSAtLT4gUFtQcm9tcHQgQnVpbGRlcjxici8-Vkkgbm8taGFsbHVjaW5hdGlvbjxici8-KyBzdHVkZW50IGNvbnRleHRdCiAgICBQIC0tPiBMTE1bR2VtaW5pIDIuNSBGbGFzaDxici8-Z2VuZXJhdGVfY29udGVudF9hc3luYyBzdHJlYW1dCiAgICBMTE0gLS0-IFJbUmVzcG9uc2U8YnIvPisgY2l0YXRpb25zIGZpbGUvdHJhbmddCgogICAgc3R5bGUgVlMgZmlsbDojZGJlYWZlCiAgICBzdHlsZSBLUyBmaWxsOiNmZWYzYzcKICAgIHN0eWxlIE0gZmlsbDojZGNmY2U3CiAgICBzdHlsZSBMTE0gZmlsbDojZmNlN2Yz)

---

# AI #2: Hybrid Retrieval — vì sao 2 cách?

<div class="columns">

**Vector search**
- Cosine similarity trên Gemini embedding 768d
- Hiểu **ngữ nghĩa**
- Hợp với câu hỏi tự nhiên
- Ví dụ: "Bao giờ thì bị buộc thôi học?" → match "đình chỉ học tập"

**Keyword search**
- ILIKE + scoring rule-based
- Match từ khóa quy chế cứng (gpa, xếp loại, "từ 3,2 đến cận 3,6"...)
- Hợp với câu hỏi có **số liệu cụ thể**
- Ví dụ: "GPA 3.2 xếp loại gì?" → match đoạn ngưỡng

</div>

**Merged**: doc xuất hiện ở cả 2 → confidence cao nhất (`match_type="merged"`).

> Code: [`backend/app/ai/chatbot/vectorstore.py`](../backend/app/ai/chatbot/vectorstore.py:85-216)

**Stack RAG đầy đủ:**
- PDF/Word parser (PyMuPDF + python-docx + OCR fallback)
- Chunking 800 từ + overlap 120
- pgvector cho vector store
- Streaming response qua SSE (real Gemini streaming, không fake)
- ChatMessage table lưu lịch sử multi-turn

---

<!-- _class: section -->

# Phần 4
## Sản phẩm

---

# Module sinh viên (8 trang)

| # | Trang | Tính năng chính |
|---|---|---|
| 1 | **Dashboard** | 5 stat card · GPA trend chart · risk AI snapshot |
| 2 | **Bảng điểm** | Filter HK · Add/Edit/Delete môn · 12 weight templates · myBK paste import |
| 3 | **Dự báo AI** | Risk gauge · Top 5 SHAP factors · Pass/fail dự đoán môn · History chart |
| 4 | **Cảnh báo** | List by level · Mark resolved · Info quy chế |
| 5 | **Tư vấn AI** | RAG chat · Streaming · Citations [n] file/trang · Multi-turn |
| 6 | **Sự kiện** | Upcoming/All tabs · Type icons · Mandatory + countdown |
| 7 | **Kế hoạch học** | Credit load đề xuất · Retake priority · Suggested courses |
| 8 | **Thông báo** | Bell badge polling 60s · Mark read · Email opt-out toggle |

---

# Module admin (8 trang)

| # | Trang | Tính năng chính |
|---|---|---|
| 1 | **Dashboard** | 4 stat card · Risk distribution · By-faculty · Top-10 SV nguy cơ |
| 2 | **Sinh viên** | Search · Filter (warning/high-risk) · Pagination · Detail link |
| 3 | **Chi tiết SV** | Profile + stats · Risk factors · GPA chart · Warnings history · Manual warning |
| 4 | **Quản lý cảnh báo** | Pending AI · Approve/Dismiss · Run Batch AI · Threshold info |
| 5 | **Import dữ liệu** | Excel students/grades · Download templates · Result + error table · History |
| 6 | **Quy chế RAG** | Upload PDF/DOCX · Toggle active · Delete · Chunks info |
| 7 | **Sự kiện** | Create form · List · Audience targeting · Delete |
| 8 | **Báo cáo** | 4 stat · By-semester chart · GPA distribution · Export buttons |

---

# Email + Notification flow (M6)

![Mermaid diagram 6](https://mermaid.ink/svg/c2VxdWVuY2VEaWFncmFtCiAgICBwYXJ0aWNpcGFudCBTViBhcyBTaW5oIHZpw6puCiAgICBwYXJ0aWNpcGFudCBGRSBhcyBGcm9udGVuZAogICAgcGFydGljaXBhbnQgQVBJIGFzIEZhc3RBUEkKICAgIHBhcnRpY2lwYW50IFdFIGFzIHdhcm5pbmdfZW5naW5lCiAgICBwYXJ0aWNpcGFudCBOIGFzIG5vdGlmaWNhdGlvbiBzdmMKICAgIHBhcnRpY2lwYW50IEVNIGFzIGVtYWlsX3NlcnZpY2UKICAgIHBhcnRpY2lwYW50IERCIGFzIFBvc3RncmVTUUwKICAgIHBhcnRpY2lwYW50IFNNVFAgYXMgR21haWwgU01UUAoKICAgIFNWLT4-RkU6IE5o4bqtcCDEkWnhu4NtIG3DtG4KICAgIEZFLT4-QVBJOiBQT1NUIC9tZS9lbnJvbGxtZW50cwogICAgQVBJLT4-V0U6IGV2YWx1YXRlX2FuZF9wZXJzaXN0KHN0dWRlbnQpCiAgICBXRS0-PkRCOiBJbnNlcnQgV2FybmluZyAoaWRlbXBvdGVudCkKICAgIFdFLT4-TjogY3JlYXRlKHR5cGU9d2FybmluZywgLi4uKQogICAgTi0-PkRCOiBJbnNlcnQgTm90aWZpY2F0aW9uCiAgICBOLS0-PkVNOiBkaXNwYXRjaCh0ZW1wbGF0ZSwgY29udGV4dCk8YnIvPmZpcmUtYW5kLWZvcmdldAogICAgRU0tPj5TTVRQOiBzZW5kIChmYWlsLXNvZnQpCiAgICBFTS0-PkRCOiBVcGRhdGUgZW1haWxfc2VudF9hdAogICAgQVBJLS0-PkZFOiAyMDAgT0sKICAgIE5vdGUgb3ZlciBFTTogRGVtbyBtb2RlOiBsb2cgW0VNQUlMIERFViBNT0RFXTxici8-a2hpIFNNVFBfVVNFUiBy4buXbmc)

---

# Demo flow — Sinh viên (4 phút)

1. **Login** sinh viên (`student@hcmut.edu.vn / password123`)
2. **Dashboard** — show GPA trend giảm 3 HK liên tiếp + risk badge
3. **Bảng điểm** → click "Cập nhật từ myBK" → paste raw text → modal show số môn tạo/cập nhật
4. **Dự báo AI** → RadialBar gauge + Top 5 SHAP reasons (giải thích bằng tiếng Việt) + dự đoán pass/fail từng môn
5. **Tư vấn AI** → hỏi "GPA 1.8 có bị cảnh báo không?" → streaming response + citation [1] *Quy chế đào tạo trang 12*
6. **Cảnh báo** → list cảnh báo Mức 1 + click "Đánh dấu đã xử lý"
7. **Bell** sidebar — click → notifications page → toggle email opt-out

---

# Demo flow — Admin (3 phút)

1. **Login** admin (`admin@hcmut.edu.vn / admin123`)
2. **Dashboard admin** — 4 stat card + biểu đồ phân bố risk + top-10 SV nguy cơ
3. **Import dữ liệu**:
   - Tải template Excel → mở thấy sample row
   - Upload `students.xlsx` (50 SV) → modal show "+50 created · 0 errors"
   - Upload `grades.xlsx` (200 records) → modal show stats
4. **Sinh viên** → search MSSV → click Chi tiết → xem profile + GPA chart + risk factors
5. **Quản lý cảnh báo** → click "Run Batch AI" → đợi 5s → list pending xuất hiện → click "Duyệt gửi" trên 1 dòng
6. **(Verify)** Login lại tài khoản SV vừa được duyệt → notifications có 1 cái mới + console docker log `[EMAIL DEV MODE]`

---

# Bảo mật

| Vector tấn công | Phòng thủ |
|---|---|
| **Authentication bypass** | JWT Bearer token + 24h expire · `get_current_user` dependency |
| **Privilege escalation** | `require_admin` dependency check role enum · Layout guard FE redirect non-admin |
| **SQL injection** | SQLAlchemy parameterized queries · không raw string concat |
| **XSS** | Next.js escape mặc định · Jinja2 `autoescape=True` cho email |
| **CSRF** | JWT trong header (Bearer) thay vì cookie session — không exploit được CSRF |
| **Password storage** | bcrypt 12 rounds (`passlib`) · không lưu plaintext |
| **Email spoofing** | Gmail SMTP App Password — không cho gửi từ domain khác |
| **Prompt injection** (RAG) | Prompt cứng "no-hallucination" + retrieval whitelist + citation forced |

> **Layered architecture** giúp hạn chế blast radius: AI module bị compromise không truy cập trực tiếp HTTP layer.

---

# Số liệu thống kê

<div class="columns">

**Backend**
- 10 SQLAlchemy models
- 4 Alembic migrations
- 11 API modules · ~50 endpoints
- 8 service modules
- 8+ test files
- ~6,000 LOC Python

**Frontend**
- 16 trang (8 SV + 8 admin)
- 1 student layout + 1 admin layout
- 30+ shadcn components
- ~8,000 LOC TypeScript

</div>

<div class="columns">

**AI**
- XGBoost: 11 features · 0.14MB model
- Synthetic: 1000 SV · 65k enrollments
- F1 = 0.79 · AUC = 0.98
- RAG: pgvector 768-dim
- Hybrid: vector + keyword + merged

**Infrastructure**
- PostgreSQL 16 + pgvector
- Redis 7
- Docker Compose 4 services
- APScheduler daily batch
- Gmail SMTP (demo mode fallback)

</div>

---

# Hạn chế còn tồn tại

| # | Hạn chế | Ghi chú |
|---|---|---|
| 1 | XGBoost model train trên **synthetic data** | Cần ground-truth thực HCMUT để fine-tune |
| 2 | RAG chưa có **PDF quy chế thật** trong `data/regulations/` | Hiện chỉ `.gitkeep`, demo phải upload tay |
| 3 | **PDF/Excel export** trong báo cáo admin chưa làm | Buttons hiện disable |
| 4 | **Threshold AI** chỉ display, chưa edit qua UI | Phải sửa `.env` rồi restart |
| 5 | **Edit event inline** chưa làm | Hiện chỉ delete, muốn sửa thì xóa rồi tạo lại |
| 6 | Scheduler **không có job auto warnings_batch_daily** | Hiện chỉ trigger qua admin endpoint hoặc grade-update hook |
| 7 | Pytest **chưa baked vào Docker image** | Phải `pip install pytest` mỗi lần test trong container |
| 8 | Improvement_rate trong /admin/statistics | Cần multi-semester GPA history — placeholder NULL hiện tại |

---

# Hướng phát triển

**Ngắn hạn (M8 — Tuần 12-13):**
- E2E test full flow + viết test_admin_api.py
- PDF export cho báo cáo admin (reportlab hoặc HTML→PDF)
- Sample PDF quy chế thật → RAG demo có nguồn cite chuẩn

**Trung hạn (M9 — optional):**
- Admin Portal hoàn chỉnh: edit event inline, threshold edit qua UI, audit log
- Mobile responsive (hiện tối ưu desktop)
- Push notifications (Web Push API) thay vì chỉ email

**Dài hạn (sau đồ án):**
- Train model trên dữ liệu thực HCMUT → cần MOU với phòng đào tạo
- Recommender system gợi ý môn tự chọn theo curriculum + GPA target
- Integration HCMUT SSO thay JWT thuần
- Multi-tenant cho các trường khác

---

<!-- _class: title -->

# Cảm ơn quý thầy cô

## Q & A

**Source code:**
github.com/Zackerville/student-academic-warning-system

**Tech stack repo:**
FastAPI · Next.js · XGBoost · Gemini RAG · pgvector

*Slide deck cũng có trong repo — `docs/SLIDES.md` (Marp).*
