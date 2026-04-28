# 🎯 Kế Hoạch Triển Khai Chi Tiết (v2 — Cập Nhật)
## Hệ Thống AI Cảnh Báo Học Tập — ĐH Bách Khoa TPHCM

> [!NOTE]
> Phiên bản cập nhật — đồng bộ với project structure thực tế và tất cả chức năng đã thảo luận.

---

## Tổng Quan

| Mục | Chi tiết |
|-----|----------|
| **Đề tài** | Xây dựng hệ thống AI cảnh báo học tập cho sinh viên |
| **Người dùng chính** | Sinh viên |
| **Người dùng phụ** | Văn phòng Đào tạo (Admin) |
| **Tổng chức năng** | 67 (xem chi tiết trong [feature_list.md](file:///Users/bravesoft/.gemini/antigravity/brain/20372964-c953-417a-bde0-2ce4dcb15766/feature_list.md)) |
| **GitHub** | [student-academic-warning-system](https://github.com/Zackerville/student-academic-warning-system) |

---

## Tech Stack

| Layer | Công nghệ | Lý do |
|-------|-----------|-------|
| **Backend** | FastAPI (Python 3.11) | Async, tự sinh docs, tích hợp ML tốt |
| **Frontend** | Next.js (React) | SSR, routing, responsive |
| **Database** | PostgreSQL 16 + pgvector | Quan hệ + vector search cùng 1 DB |
| **Cache + MQ** | Redis 7 | Cache API + Message Queue cho notification |
| **AI Prediction** | XGBoost | Nhẹ, nhanh, hiệu quả với tabular data |
| **AI Chatbot** | LangChain + Gemini API | RAG cho tư vấn quy chế học vụ |
| **AI Recommender** | Collaborative Filtering | Gợi ý môn học phù hợp |
| **Scheduler** | Celery + Celery Beat | Batch prediction, sync data, nhắc deadline |
| **Container** | Docker + Docker Compose | Dễ deploy, demo nhất quán |

---

## Cấu Trúc Dự Án (Chính xác với code thực tế)

```
WarningAI_system/
├── .gitignore
├── .env.example                          # Template biến môi trường
├── README.md
├── docker-compose.yml                    # PostgreSQL + Redis + Backend + Frontend + Celery
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                       # FastAPI entry point
│   │   │
│   │   ├── api/                          # === API Routes ===
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py               # Đăng nhập, đăng ký, JWT
│   │   │       ├── students.py           # CRUD sinh viên, nhập điểm
│   │   │       ├── warnings.py           # Xem/quản lý cảnh báo
│   │   │       ├── predictions.py        # Kết quả dự đoán AI
│   │   │       ├── chatbot.py            # Chat tư vấn quy chế (RAG)
│   │   │       ├── admin.py              # Dashboard admin, thống kê
│   │   │       ├── events.py             # Sự kiện, deadline, lịch
│   │   │       └── documents.py          # Upload/quản lý tài liệu quy chế
│   │   │
│   │   ├── core/                         # === Core Config ===
│   │   │   ├── __init__.py
│   │   │   ├── config.py                 # Settings từ .env
│   │   │   ├── security.py               # JWT, hashing password
│   │   │   ├── deps.py                   # Dependencies (get_db, get_current_user)
│   │   │   └── celery_app.py             # Celery config + scheduled tasks
│   │   │
│   │   ├── models/                       # === SQLAlchemy Models (Database) ===
│   │   │   ├── __init__.py
│   │   │   ├── user.py                   # Bảng users (email, password, role)
│   │   │   ├── student.py                # Bảng students (MSSV, khoa, GPA)
│   │   │   ├── course.py                 # Bảng courses (mã môn, tên, số TC)
│   │   │   ├── enrollment.py             # Bảng enrollments (SV đăng ký môn, điểm)
│   │   │   ├── warning.py                # Bảng warnings (cảnh báo học tập)
│   │   │   ├── prediction.py             # Bảng predictions (kết quả AI dự đoán)
│   │   │   ├── notification.py           # Bảng notifications (thông báo)
│   │   │   ├── event.py                  # Bảng events (sự kiện, deadline)
│   │   │   └── document.py              # Bảng documents (tài liệu quy chế + vector)
│   │   │
│   │   ├── schemas/                      # === Pydantic Schemas (API Request/Response) ===
│   │   │   ├── __init__.py
│   │   │   ├── user.py                   # UserCreate, UserResponse, Token
│   │   │   ├── student.py                # StudentCreate, StudentResponse
│   │   │   ├── course.py                 # CourseCreate, CourseResponse
│   │   │   ├── enrollment.py             # EnrollmentCreate, GradeUpdate
│   │   │   ├── warning.py                # WarningResponse, WarningCreate
│   │   │   ├── prediction.py             # PredictionResponse
│   │   │   ├── notification.py           # NotificationResponse
│   │   │   ├── event.py                  # EventCreate, EventResponse
│   │   │   └── document.py              # DocumentUpload, DocumentResponse
│   │   │
│   │   ├── services/                     # === Business Logic ===
│   │   │   ├── __init__.py
│   │   │   ├── warning_engine.py         # Logic cảnh báo + ngưỡng
│   │   │   ├── study_plan.py             # Chiến lược học tập gợi ý
│   │   │   ├── notification.py           # Gửi thông báo đa kênh
│   │   │   ├── import_service.py         # Import Excel/CSV bảng điểm
│   │   │   └── event_manager.py          # Quản lý sự kiện + nhắc nhở
│   │   │
│   │   ├── ai/                           # === AI Modules ===
│   │   │   ├── __init__.py
│   │   │   ├── prediction/               # Dự báo rớt môn
│   │   │   │   ├── __init__.py
│   │   │   │   ├── model.py              # Load model + predict
│   │   │   │   ├── features.py           # Feature engineering
│   │   │   │   └── train.py              # Train + evaluate XGBoost
│   │   │   ├── chatbot/                  # Tư vấn quy chế
│   │   │   │   ├── __init__.py
│   │   │   │   ├── rag.py                # RAG pipeline (chunk, embed, search)
│   │   │   │   └── chains.py             # LangChain prompt + chain
│   │   │   └── recommender/              # Gợi ý môn học
│   │   │       ├── __init__.py
│   │   │       └── engine.py             # Recommendation logic
│   │   │
│   │   └── db/                           # === Database ===
│   │       ├── __init__.py
│   │       ├── session.py                # AsyncSession factory
│   │       └── init_db.py                # Tạo tables, seed data
│   │
│   ├── migrations/                       # Alembic migrations
│   │   └── .gitkeep
│   ├── data/
│   │   ├── synthetic/                    # Dữ liệu giả lập (CSV)
│   │   │   └── .gitkeep
│   │   └── regulations/                  # PDF quy chế cho RAG
│   │       └── .gitkeep
│   └── tests/
│       ├── __init__.py
│       ├── test_api.py                   # Test API endpoints
│       └── test_ai.py                    # Test AI models
│
├── frontend/                             # Next.js (init ở Phase 5)
│   └── .gitkeep
│
└── docs/                                 # Tài liệu đồ án
    └── .gitkeep
```

> [!IMPORTANT]
> **Models vs Schemas:** Tên file giống nhau nhưng mục đích khác:
> - `models/student.py` = SQLAlchemy → định nghĩa **bảng student trong PostgreSQL**
> - `schemas/student.py` = Pydantic → định nghĩa **dữ liệu API** (request gửi lên, response trả về)

---

## Database Schema (9 bảng)

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│    users     │      │   students   │      │   courses    │
├──────────────┤      ├──────────────┤      ├──────────────┤
│ id (PK)      │      │ id (PK)      │      │ id (PK)      │
│ email        │◄─────│ user_id (FK) │      │ course_code  │
│ hashed_pass  │      │ mssv         │      │ name         │
│ role (enum)  │      │ full_name    │      │ credits      │
│ is_active    │      │ faculty      │      │ semester     │
│ created_at   │      │ major        │      │ category     │
└──────────────┘      │ cohort       │      └──────┬───────┘
                      │ gpa_cumul    │             │
                      │ credits_earn │      ┌──────┴───────┐
                      │ warning_lvl  │      │ enrollments  │
                      └──────┬───────┘      ├──────────────┤
                             │              │ id (PK)      │
  ┌──────────────┐    ┌──────┴───────┐      │ student_id   │
  │ predictions  │    │   warnings   │      │ course_id    │
  ├──────────────┤    ├──────────────┤      │ semester     │
  │ id (PK)      │    │ id (PK)      │      │ midterm      │
  │ student_id   │    │ student_id   │      │ final        │
  │ course_id    │    │ level (1/2/3)│      │ total_score  │
  │ risk_score   │    │ semester     │      │ grade_letter │
  │ predicted_gr │    │ reason       │      │ status       │
  │ risk_factors │    │ gpa_at_warn  │      │ attendance   │
  │ created_at   │    │ ai_risk_score│      └──────────────┘
  └──────────────┘    │ is_resolved  │
                      └──────────────┘
  ┌──────────────┐    ┌──────────────┐      ┌──────────────┐
  │notifications │    │    events    │      │  documents   │
  ├──────────────┤    ├──────────────┤      ├──────────────┤
  │ id (PK)      │    │ id (PK)      │      │ id (PK)      │
  │ student_id   │    │ title        │      │ content      │
  │ type (enum)  │    │ description  │      │ embedding    │
  │ channel      │    │ event_type   │      │ source_file  │
  │ title        │    │ target_aud   │      │ chunk_index  │
  │ content      │    │ start_time   │      │ is_active    │
  │ is_read      │    │ end_time     │      │ uploaded_at  │
  │ sent_at      │    │ is_mandatory │      └──────────────┘
  └──────────────┘    │ created_by   │
                      └──────────────┘
```

---

## API Endpoints Đầy Đủ (8 nhóm route)

### 🔐 auth.py — Xác thực
| Method | Endpoint | Mô tả |
|--------|----------|--------|
| POST | `/api/v1/auth/register` | Đăng ký |
| POST | `/api/v1/auth/login` | Đăng nhập → JWT |
| POST | `/api/v1/auth/refresh` | Refresh token |
| POST | `/api/v1/auth/forgot-password` | Quên mật khẩu |

### 👤 students.py — Sinh viên
| Method | Endpoint | Mô tả |
|--------|----------|--------|
| GET | `/api/v1/students/me` | Thông tin cá nhân |
| GET | `/api/v1/students/me/grades` | Bảng điểm theo HK |
| POST | `/api/v1/students/me/enrollments` | Đăng ký môn đang học |
| PUT | `/api/v1/students/me/enrollments/{id}` | Cập nhật điểm |
| GET | `/api/v1/students/me/gpa` | GPA tích lũy + dự kiến |

### ⚠️ warnings.py — Cảnh báo
| Method | Endpoint | Mô tả |
|--------|----------|--------|
| GET | `/api/v1/warnings/me` | Lịch sử cảnh báo của SV |
| GET | `/api/v1/warnings/me/{id}` | Chi tiết 1 cảnh báo |
| GET | `/api/v1/warnings/` | [Admin] Tất cả cảnh báo |
| POST | `/api/v1/warnings/batch-run` | [Admin] Chạy batch cảnh báo |
| POST | `/api/v1/warnings/manual` | [Admin] Tạo cảnh báo thủ công |
| PUT | `/api/v1/warnings/{id}/approve` | [Admin] Duyệt cảnh báo |

### 🤖 predictions.py — Dự đoán AI
| Method | Endpoint | Mô tả |
|--------|----------|--------|
| GET | `/api/v1/predictions/me` | Xem risk score + factors |
| GET | `/api/v1/predictions/me/courses` | Dự đoán từng môn |
| POST | `/api/v1/predictions/batch-run` | [Admin] Chạy batch prediction |

### 💬 chatbot.py — Chatbot tư vấn
| Method | Endpoint | Mô tả |
|--------|----------|--------|
| POST | `/api/v1/chatbot/ask` | Gửi câu hỏi → nhận trả lời |
| GET | `/api/v1/chatbot/history` | Lịch sử chat |
| GET | `/api/v1/chatbot/suggestions` | Câu hỏi gợi ý |

### 🏛️ admin.py — Admin Dashboard
| Method | Endpoint | Mô tả |
|--------|----------|--------|
| GET | `/api/v1/admin/dashboard` | Tổng quan hệ thống |
| GET | `/api/v1/admin/students` | Danh sách SV + filter |
| GET | `/api/v1/admin/students/{id}` | Chi tiết 1 SV |
| POST | `/api/v1/admin/import/students` | Import danh sách SV |
| POST | `/api/v1/admin/import/grades` | Import bảng điểm |
| GET | `/api/v1/admin/statistics` | Thống kê theo khoa/ngành |
| GET | `/api/v1/admin/export/warnings` | Xuất báo cáo cảnh báo |

### 📅 events.py — Sự kiện & Deadline
| Method | Endpoint | Mô tả |
|--------|----------|--------|
| POST | `/api/v1/events/` | [Admin] Tạo sự kiện |
| GET | `/api/v1/events/` | [Admin] Danh sách sự kiện |
| PUT | `/api/v1/events/{id}` | [Admin] Sửa sự kiện |
| DELETE | `/api/v1/events/{id}` | [Admin] Xóa sự kiện |
| GET | `/api/v1/events/me` | [SV] Sự kiện của tôi |
| GET | `/api/v1/events/me/upcoming` | [SV] Sự kiện sắp tới |

### 📄 documents.py — Quản lý quy chế (RAG)
| Method | Endpoint | Mô tả |
|--------|----------|--------|
| POST | `/api/v1/documents/upload` | [Admin] Upload PDF/Word quy chế |
| GET | `/api/v1/documents/` | [Admin] Danh sách tài liệu |
| PUT | `/api/v1/documents/{id}/toggle` | [Admin] Bật/tắt tài liệu |
| DELETE | `/api/v1/documents/{id}` | [Admin] Xóa tài liệu + vectors |

---

## Timeline 7 Phases / 14 Tuần

### Phase 0: Chuẩn Bị (Tuần 1)
- [ ] Nghiên cứu quy chế đào tạo ĐHBK TPHCM
- [ ] Thu thập tài liệu quy chế (PDF) cho RAG
- [ ] Xác định tiêu chí cảnh báo theo quy chế
- [ ] Setup Git repo + Docker Compose ✅
- [ ] Tạo project structure ✅

### Phase 1: Database & Backend Core (Tuần 2-3)
- [ ] Tạo SQLAlchemy models (9 bảng):
  - `user.py` → users
  - `student.py` → students
  - `course.py` → courses
  - `enrollment.py` → enrollments
  - `warning.py` → warnings
  - `prediction.py` → predictions
  - `notification.py` → notifications
  - `event.py` → events
  - `document.py` → documents (+ pgvector embedding)
- [ ] Setup Alembic migrations
- [ ] Tạo Pydantic schemas (9 files tương ứng)
- [ ] `core/config.py` — Settings từ .env
- [ ] `core/security.py` — JWT + password hashing
- [ ] `core/deps.py` — get_db, get_current_user, require_admin
- [ ] `db/session.py` — AsyncSession factory
- [ ] `db/init_db.py` — Tạo tables + seed data
- [ ] API routes: `auth.py`, `students.py` (CRUD cơ bản)
- [ ] Tạo script synthetic data (500-1000 SV)

### Phase 2: Data Pipeline (Tuần 4)
- [ ] `services/import_service.py`:
  - Import danh sách SV từ Excel/CSV
  - Import bảng điểm từ Excel/CSV
  - Validation dữ liệu (MSSV trùng, thiếu cột)
  - Template mẫu Excel
- [ ] `core/celery_app.py`:
  - Celery config
  - Scheduled tasks (batch prediction, nhắc deadline)
- [ ] Feature engineering cho XGBoost:
  - GPA từng HK, tích lũy, xu hướng
  - Số môn rớt, tỷ lệ điểm danh
  - Số TC đăng ký vs hoàn thành
- [ ] API routes: `admin.py` (import endpoints)

### Phase 3: AI Models (Tuần 5-7) ⭐

> [!IMPORTANT]
> Đây là phần quan trọng nhất — dành nhiều thời gian nhất.

**Tuần 5-6: XGBoost Prediction**
- [ ] `ai/prediction/features.py` — Feature engineering
- [ ] `ai/prediction/train.py` — Train + evaluate:
  - EDA trên synthetic data
  - Hyperparameter tuning (Optuna)
  - Cross-validation (k-fold)
  - Metrics: Accuracy, F1, AUC-ROC
- [ ] `ai/prediction/model.py` — Load model + predict API
- [ ] API routes: `predictions.py`

**Tuần 6-7: RAG Chatbot**
- [ ] `ai/chatbot/rag.py` — Document processing:
  - Đọc PDF/Word (PyPDF2, python-docx)
  - Chunking (500-1000 tokens, overlap 100)
  - Embedding (Gemini / sentence-transformers)
  - Lưu vectors vào pgvector
- [ ] `ai/chatbot/chains.py` — LangChain:
  - Retriever → pgvector search
  - LLM → Gemini API
  - Prompt template tiếng Việt
- [ ] API routes: `chatbot.py`, `documents.py`

**Tuần 7: Recommender**
- [ ] `ai/recommender/engine.py`:
  - Gợi ý môn học dựa trên pattern SV tương tự
  - Gợi ý số TC phù hợp theo GPA

### Phase 4: Business Logic (Tuần 8-9)
- [ ] `services/warning_engine.py`:
  - Ngưỡng cảnh báo theo quy chế ĐHBK
  - Kết hợp AI risk_score + quy chế cứng
  - Cảnh báo sớm (AI phát hiện trước khi vi phạm)
  - Batch warning qua Celery
- [ ] `services/study_plan.py`:
  - Gợi ý chiến lược HK tới
  - Gợi ý giảm tải cho SV nguy cơ cao
- [ ] `services/notification.py`:
  - In-app notification (lưu DB)
  - Email notification (fastapi-mail)
  - Redis queue cho async sending
- [ ] `services/event_manager.py`:
  - CRUD sự kiện
  - Auto-reminder (3 ngày + 1 ngày trước deadline)
- [ ] API routes: `warnings.py`, `events.py`

### Phase 5: Frontend (Tuần 10-12)
- [ ] Init Next.js project trong `frontend/`
- [ ] **Login page** (`/login`)
- [ ] **Student pages:**
  - `/dashboard` — Tổng quan: GPA chart, risk gauge, cảnh báo, sự kiện
  - `/grades` — Bảng điểm + nhập điểm
  - `/warnings` — Lịch sử cảnh báo
  - `/predictions` — Risk score + factors
  - `/study-plan` — Kế hoạch gợi ý
  - `/chatbot` — Chat tư vấn quy chế
  - `/events` — Lịch sự kiện + deadline
- [ ] **Admin pages:**
  - `/admin/dashboard` — Tổng quan: số SV cảnh báo, biểu đồ
  - `/admin/students` — Danh sách SV + filter + search
  - `/admin/students/[id]` — Chi tiết 1 SV
  - `/admin/warnings` — Quản lý cảnh báo
  - `/admin/import` — Import dữ liệu
  - `/admin/documents` — Quản lý quy chế
  - `/admin/events` — Quản lý sự kiện
  - `/admin/reports` — Thống kê

### Phase 6: Tích Hợp & Testing (Tuần 13)
- [ ] Kết nối Frontend ↔ Backend
- [ ] Test flows hoàn chỉnh:
  1. SV đăng nhập → xem dashboard → xem risk → chat
  2. Admin import điểm → chạy prediction → gửi cảnh báo
  3. Admin tạo sự kiện → SV nhận nhắc nhở
  4. Admin upload quy chế → SV hỏi chatbot
- [ ] Unit tests cho AI models
- [ ] API tests cho endpoints

### Phase 7: Deploy & Demo (Tuần 14)
- [ ] Docker Compose hoàn chỉnh
- [ ] Deploy lên Railway / Render (nếu cần)
- [ ] Viết hướng dẫn cài đặt
- [ ] Chuẩn bị slide + video demo
- [ ] Viết báo cáo đồ án

---

## Timeline Visual

```
Tuần 1  ████░░░░░░░░░░░░░░░░░░░░░░░░ Phase 0: Chuẩn bị
Tuần 2  ░░░░████████░░░░░░░░░░░░░░░░ Phase 1: Database + Backend
Tuần 3  ░░░░████████░░░░░░░░░░░░░░░░ Phase 1: API + Auth
Tuần 4  ░░░░░░░░░░░░████░░░░░░░░░░░░ Phase 2: Data Pipeline
Tuần 5  ░░░░░░░░░░░░░░░░████████░░░░ Phase 3: XGBoost ⭐
Tuần 6  ░░░░░░░░░░░░░░░░████████░░░░ Phase 3: XGBoost + RAG ⭐
Tuần 7  ░░░░░░░░░░░░░░░░████████░░░░ Phase 3: RAG + Recommender ⭐
Tuần 8  ░░░░░░░░░░░░░░░░░░░░████░░░░ Phase 4: Warning Engine
Tuần 9  ░░░░░░░░░░░░░░░░░░░░████░░░░ Phase 4: Notification + Events
Tuần 10 ░░░░░░░░░░░░░░░░░░░░░░░░████ Phase 5: Frontend SV
Tuần 11 ░░░░░░░░░░░░░░░░░░░░░░░░████ Phase 5: Frontend SV
Tuần 12 ░░░░░░░░░░░░░░░░░░░░░░░░████ Phase 5: Frontend Admin
Tuần 13 ░░░░░░░░░░░░░░░░░░░░░░░░░░██ Phase 6: Testing
Tuần 14 ░░░░░░░░░░░░░░░░░░░░░░░░░░██ Phase 7: Deploy + Demo
```

---

## Rủi Ro & Giải Pháp

| Rủi ro | Giải pháp |
|--------|-----------|
| Không có data thật từ trường | Tạo synthetic data chất lượng cao |
| AI model accuracy thấp | Thử XGBoost, LightGBM, Random Forest; feature engineering kỹ |
| Gemini API rate limit | Cache câu hỏi tương tự trong Redis |
| Không đủ thời gian | Ưu tiên P0 → P1 → P2 (xem bảng dưới) |
| Docker quá nặng khi demo | Chuẩn bị video demo backup |

---

## Thứ Tự Ưu Tiên

| Mức | Tính năng | Bắt buộc? |
|-----|-----------|-----------|
| 🥇 P0 | XGBoost Prediction + Warning Engine | ✅ Core đề tài |
| 🥈 P0 | RAG Chatbot tư vấn quy chế | ✅ Điểm nhấn AI |
| 🥉 P0 | Dashboard SV + Admin (có data) | ✅ Cần để demo |
| P1 | Import Excel, Events, Notification | Nên có |
| P2 | Recommender, Study Plan, Export PDF | Điểm cộng |
| P3 | Email notification, cấu hình ngưỡng | Nếu kịp |
