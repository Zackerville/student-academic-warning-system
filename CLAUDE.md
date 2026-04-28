# CLAUDE.md — AI Student Warning System (HCMUT)

## Tổng Quan Project

Hệ thống cảnh báo học vụ thông minh cho sinh viên Đại học Bách Khoa TP.HCM.
- **Solo developer**: 1 sinh viên IT làm toàn bộ hệ thống
- **Mức độ**: Đồ án chuyên ngành, có thể nâng lên đồ án tốt nghiệp
- **GitHub**: https://github.com/Zackerville/student-academic-warning-system

## Tech Stack

| Layer | Công nghệ | Ghi chú |
|-------|-----------|---------|
| Backend | FastAPI (Python 3.11), async | Swagger tự sinh tại /docs |
| Database | PostgreSQL 16 + pgvector | Quan hệ + vector search chung 1 DB |
| Cache | Redis 7 | Cache API response |
| Task Scheduler | APScheduler (thay Celery) | Nhẹ hơn Celery, đủ dùng cho demo |
| AI - Prediction | XGBoost | Risk score + feature importance |
| AI - Chatbot | LangChain + Gemini API (gemini-1.5-flash) | RAG tư vấn quy chế |
| AI - Embeddings | Google Generative AI Embeddings | models/embedding-001 |
| Frontend | Next.js 14 (App Router) + TypeScript | shadcn/ui + Tailwind CSS |
| Container | Docker + Docker Compose | PostgreSQL + Redis + Backend |

> **Lý do dùng APScheduler thay Celery**: Celery yêu cầu Redis làm broker, cần 3 process riêng (worker + beat + broker), phức tạp để debug khi solo dev. APScheduler chạy in-process, đủ cho batch prediction daily + deadline reminders.

## Cấu Trúc Project

```
student-academic-warning-system/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── migrations/          # Alembic migration files
│   ├── data/
│   │   ├── synthetic/       # CSV dữ liệu giả lập
│   │   └── regulations/     # PDF quy chế HCMUT cho RAG
│   ├── tests/
│   └── app/
│       ├── main.py              # FastAPI entry + lifespan
│       ├── api/v1/
│       │   ├── auth.py          # POST /register, /login, /refresh
│       │   ├── students.py      # /me, /me/grades, /me/enrollments, /me/gpa
│       │   ├── warnings.py      # /me, /me/{id}, / [admin], /batch-run
│       │   ├── predictions.py   # /me, /me/courses, /batch-run [admin]
│       │   ├── chatbot.py       # /ask, /history, /suggestions
│       │   ├── admin.py         # /dashboard, /students, /import/*, /statistics
│       │   ├── events.py        # CRUD events + /me/upcoming
│       │   └── documents.py     # /upload, /toggle, /delete [admin]
│       ├── core/
│       │   ├── config.py        # Settings từ .env (pydantic-settings)
│       │   ├── security.py      # JWT create/decode, bcrypt hashing
│       │   ├── deps.py          # get_db, get_current_user, require_admin
│       │   └── scheduler.py     # APScheduler setup (thay celery_app.py)
│       ├── models/              # SQLAlchemy ORM (9 bảng)
│       │   ├── user.py          # users
│       │   ├── student.py       # students
│       │   ├── course.py        # courses
│       │   ├── enrollment.py    # enrollments (SV đăng ký môn + điểm)
│       │   ├── warning.py       # warnings
│       │   ├── prediction.py    # predictions (AI output)
│       │   ├── notification.py  # notifications
│       │   ├── event.py         # events + deadlines
│       │   └── document.py      # RAG documents + pgvector embeddings
│       ├── schemas/             # Pydantic request/response (9 files)
│       ├── services/
│       │   ├── warning_engine.py    # Logic cảnh báo + ngưỡng theo quy chế HCMUT
│       │   ├── study_plan.py        # Gợi ý chiến lược học
│       │   ├── notification.py      # In-app + email notification
│       │   ├── import_service.py    # Import Excel/CSV
│       │   └── event_manager.py     # CRUD + auto-reminder
│       ├── ai/
│       │   ├── prediction/
│       │   │   ├── features.py      # Feature engineering từ DB
│       │   │   ├── train.py         # Train XGBoost, save model
│       │   │   └── model.py         # Load model, batch predict
│       │   ├── chatbot/
│       │   │   ├── rag.py           # Chunk + embed + pgvector store
│       │   │   └── chains.py        # LangChain RAG chain với Gemini
│       │   └── recommender/
│       │       └── engine.py        # Gợi ý môn học
│       └── db/
│           ├── session.py           # AsyncSession factory
│           ├── base.py              # DeclarativeBase
│           └── init_db.py           # Tạo tables + seed admin account
├── frontend/                        # Next.js 14 App Router
│   ├── app/
│   │   ├── (auth)/login/
│   │   ├── (student)/               # Layout student
│   │   │   ├── dashboard/
│   │   │   ├── grades/
│   │   │   ├── warnings/
│   │   │   ├── predictions/
│   │   │   ├── chatbot/
│   │   │   ├── study-plan/
│   │   │   └── events/
│   │   └── admin/                   # Layout admin
│   │       ├── dashboard/
│   │       ├── students/
│   │       ├── warnings/
│   │       ├── import/
│   │       ├── documents/
│   │       └── events/
│   ├── components/
│   ├── lib/
│   │   ├── api.ts                   # Axios client + interceptors
│   │   └── auth.ts                  # Auth helpers
│   └── types/
├── docs/
├── docker-compose.yml               # db + redis + backend + pgadmin
├── .env.example
├── Makefile
└── pyproject.toml
```

## Database Schema (9 bảng)

### users
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | VARCHAR UNIQUE | |
| hashed_password | VARCHAR | bcrypt |
| role | ENUM(student, admin) | |
| is_active | BOOLEAN | default true |
| created_at | TIMESTAMP | |

### students
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | 1-1 |
| mssv | VARCHAR UNIQUE | VD: 2110001 |
| full_name | VARCHAR | |
| faculty | VARCHAR | VD: Khoa CNTT |
| major | VARCHAR | VD: Khoa học Máy tính |
| cohort | INTEGER | VD: 2021 |
| gpa_cumulative | FLOAT | Tự tính, cập nhật sau mỗi HK |
| credits_earned | INTEGER | Tổng TC tích lũy |
| warning_level | INTEGER | 0=BT, 1=Cảnh báo 1, 2=Cảnh báo 2, 3=Buộc thôi học |

### courses
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| course_code | VARCHAR | VD: CO1007 |
| name | VARCHAR | |
| credits | INTEGER | Số tín chỉ |
| faculty | VARCHAR | Khoa phụ trách |

### enrollments
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| student_id | UUID FK | |
| course_id | UUID FK | |
| semester | VARCHAR | VD: 241 (HK1 2024-2025), 252 (HK2 2025-2026) |
| midterm_score | FLOAT nullable | Điểm GK |
| lab_score | FLOAT nullable | Điểm TN (thí nghiệm) |
| other_score | FLOAT nullable | Điểm BTL / Đồ án / Báo cáo |
| final_score | FLOAT nullable | Điểm CK |
| midterm_weight | FLOAT default 0.3 | Trọng số GK (sum 4 weights = 1.0) |
| lab_weight | FLOAT default 0.0 | Trọng số TN |
| other_weight | FLOAT default 0.0 | Trọng số BTL / Đồ án |
| final_weight | FLOAT default 0.7 | Trọng số CK |
| total_score | FLOAT nullable | Điểm tổng kết (auto-compute hoặc lấy từ myBK) |
| grade_letter | VARCHAR nullable | A+, A, B+, ..., F, RT, MT, DT |
| status | ENUM(enrolled, passed, failed, withdrawn, exempt) | |
| is_finalized | BOOLEAN default false | true = điểm chính thức (từ myBK), không sửa được |
| source | VARCHAR(20) default "manual" | "manual" \| "mybk_paste" \| "admin_import" |
| attendance_rate | FLOAT nullable | % điểm danh |

### warnings
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| student_id | UUID FK | |
| level | INTEGER | 1, 2, 3 |
| semester | VARCHAR | |
| reason | TEXT | Lý do cụ thể |
| gpa_at_warning | FLOAT | GPA tại thời điểm cảnh báo |
| ai_risk_score | FLOAT | Risk score từ AI |
| is_resolved | BOOLEAN | Admin xử lý chưa |
| sent_at | TIMESTAMP | |
| created_by | ENUM(system, admin) | |

### predictions
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| student_id | UUID FK | |
| semester | VARCHAR | |
| risk_score | FLOAT | 0.0 - 1.0 |
| risk_level | ENUM(low, medium, high, critical) | |
| risk_factors | JSONB | {"gpa_trend": -0.5, "failed_courses": 2, ...} |
| predicted_courses | JSONB | [{"course_id": ..., "pass_prob": 0.7}, ...] |
| created_at | TIMESTAMP | |

### notifications
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| student_id | UUID FK | |
| type | ENUM(warning, reminder, event, system) | |
| title | VARCHAR | |
| content | TEXT | |
| is_read | BOOLEAN | |
| sent_at | TIMESTAMP | |

### events
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| title | VARCHAR | |
| description | TEXT | |
| event_type | ENUM(exam, submission, activity, evaluation) | |
| target_audience | ENUM(all, faculty_specific, cohort_specific) | |
| target_value | VARCHAR nullable | Tên khoa/khóa nếu targeted |
| start_time | TIMESTAMP | |
| end_time | TIMESTAMP nullable | |
| is_mandatory | BOOLEAN | |
| created_by | UUID FK → users | |

### documents (RAG)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| filename | VARCHAR | Tên file gốc |
| content | TEXT | Nội dung chunk |
| embedding | VECTOR(768) | pgvector, Google embedding-001 |
| source_file | VARCHAR | File PDF/Word gốc |
| chunk_index | INTEGER | Thứ tự chunk trong file |
| is_active | BOOLEAN | Có dùng cho RAG không |
| uploaded_at | TIMESTAMP | |
| uploaded_by | UUID FK → users | |

## API Conventions

- Prefix: `/api/v1/`
- Auth: Bearer JWT token trong header `Authorization`
- Responses: `{"data": ..., "message": "..."}` hoặc `{"detail": "..."}` khi lỗi
- Phân trang: `?page=1&size=20`
- Admin endpoints đều check `role == "admin"` qua `require_admin` dependency

## Coding Conventions

- **Python**: async/await toàn bộ (FastAPI + SQLAlchemy async)
- **Import**: Absolute imports từ `app.`
- **Models**: Dùng `DeclarativeBase` từ `app.db.base`
- **UUID**: Tất cả primary key dùng UUID, generated ở Python side
- **Timestamps**: Tất cả bảng có `created_at`, một số có `updated_at`
- **Enums**: Dùng Python `Enum` class + `sa.Enum` type cho SQLAlchemy
- **Alembic**: Mỗi lần thay đổi model phải tạo migration mới, không sửa migration cũ

## Cấu trúc điểm môn học (M3 Design Decision)

Mỗi enrollment có thể có nhiều cấu trúc điểm khác nhau — trọng số được lưu **per-enrollment** (không phải per-course):

**Templates phổ biến HCMUT:**
| Template | GK | TN | BTL | CK | Áp dụng |
|----------|----|----|-----|----|----|
| Lý thuyết thuần (default) | 30% | 0 | 0 | 70% | Phần lớn môn |
| Lý thuyết + TN | 30% | 20% | 0 | 50% | Vật lý, Mạng MT, OS... |
| Lý thuyết + Đồ án | 30% | 0 | 30% | 40% | Lập trình, CSDL... |
| Đồ án thuần | 0 | 0 | 100% | 0 | Đồ án CN |
| Báo cáo / Seminar | 0 | 0 | 0 | 100% | Sinh hoạt SV, Khởi nghiệp |
| Tùy chỉnh | tùy | tùy | tùy | tùy | Mọi case khác |

**Logic tính total_score:**
- Khi import từ myBK: `total_score` lấy nguyên từ paste, weights đều = 0 (không cần)
- Khi SV tự nhập: tính `total = Σ(score_i × weight_i)` chỉ khi đủ điểm cho mọi `weight > 0`
- Thiếu điểm → `total = NULL`, hiển thị "what-if" calculator cho SV

## myBK Paste Import Flow

**Vấn đề:** myBK chỉ hiển thị `Điểm tổng kết` cho mỗi môn (không show điểm thành phần qua Ctrl+A copy).

**Giải pháp:**
- HK quá khứ: import qua paste → chỉ có `total_score` + `grade_letter` + `status`, set `is_finalized=true`
- HK đang học: SV tự nhập điểm thành phần khi có (GK/TN/BTL) → AI dùng làm features
- Re-paste cuối HK: parser detect các môn `is_finalized=false` → cập nhật total từ myBK + giữ nguyên component scores SV đã nhập

**Special grade letters từ myBK:**
| Letter | Nghĩa | Status | Xử lý điểm số |
|--------|-------|--------|----------------|
| A+ → D | Đạt | passed | Lưu nguyên |
| F | Không đạt | failed | Lưu nguyên |
| RT | Rút môn | withdrawn | Bỏ điểm số (placeholder) |
| MT | Miễn điểm | exempt | Bỏ điểm số, đếm TC ko tính GPA |
| DT | Điểm đạt (ko có điểm) | passed | Bỏ điểm số, ko tính GPA |
| CT, VT, CH, KD, VP, HT | Tình trạng đặc biệt | enrolled | Skip |

## Warning Logic (Quy chế HCMUT)

```
Cảnh báo học vụ theo quy chế Bách Khoa:
- Cảnh báo mức 1: GPA tích lũy < 1.2 (thang 4) HOẶC GPA học kỳ < 0.8
- Cảnh báo mức 2: GPA tích lũy < 1.0 HOẶC 2 lần liên tiếp cảnh báo mức 1
- Buộc thôi học: GPA tích lũy < 0.8 HOẶC 3 lần cảnh báo, hoặc cảnh báo 2 lần mức 2

AI Early Warning: Risk score >= 0.6 → cảnh báo sớm ngay cả khi chưa vi phạm quy chế
```

## AI Models

### XGBoost Risk Prediction
**Features** (input):
- `gpa_semester_1..N`: GPA từng học kỳ
- `gpa_cumulative`: GPA tích lũy
- `gpa_trend_3hk`: Xu hướng GPA 3 HK gần nhất (slope)
- `credits_enrolled`: Số TC đang đăng ký HK này
- `credits_earned_ratio`: TC tích lũy / TC cần tốt nghiệp
- `failed_courses_total`: Tổng số môn rớt
- `failed_courses_last_semester`: Môn rớt HK trước
- `avg_attendance`: Điểm danh trung bình
- `midterm_gpa_current`: GPA giữa kỳ HK này (nếu có)

**Output**: `risk_score` (0-1), `risk_level` (low/medium/high/critical)

### RAG Chatbot
- **Documents**: PDF quy chế đào tạo HCMUT (đặt trong `backend/data/regulations/`)
- **Chunking**: 800 tokens, overlap 100 tokens
- **Embedding**: Google `models/embedding-001` (768 dims) → pgvector
- **Retrieval**: Top-5 similar chunks (cosine similarity)
- **LLM**: Gemini 1.5 Flash, prompt template tiếng Việt
- **Chain**: LangChain ConversationalRetrievalChain với chat history

## Environment Variables Quan Trọng

```bash
DATABASE_URL=postgresql+asyncpg://warning_user:warning_password@db:5432/warning_ai_db
GEMINI_API_KEY=                 # Required cho RAG chatbot
SECRET_KEY=                     # JWT signing key (min 32 chars)
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REDIS_URL=redis://redis:6379/0  # Optional, dùng khi bật Redis
```

## Trạng Thái Hiện Tại

### Đã hoàn thành:
- [x] Project structure, Docker Compose, `main.py`, `core/config.py`, `db/session.py`, `.env.example`, `Makefile`
- [x] **M1** — Foundation Setup ✅ 2026-04-28
  - 9 SQLAlchemy models, `db/base.py`, Alembic async, `scripts/init.sql`
- [x] **M2** — Auth End-to-End + FE Setup ✅ 2026-04-29
  - First migration `e55f5d666040_initial_schema`, 9 Pydantic schemas
  - `core/security.py`, `core/deps.py` (get_current_user, require_admin, get_current_student)
  - Auth API: `POST /register`, `POST /login`, `GET /me`
  - Admin auto-bootstrap qua lifespan (`admin@hcmut.edu.vn / admin123`)
  - Frontend: Next.js 14 + shadcn/ui, login/register pages, student layout + sidebar
  - Landing page `/` với navbar VI/EN toggle + nút Đăng nhập
  - Middleware auth guard chuẩn (exact `/`, prefix `/login` `/register`)

### Cần làm (theo thứ tự):
- [ ] **M3** (Tuần 3-4): Student Profile & Grades — GPA calculator HCMUT thang 4, Student/Course API, **myBK paste parser**, Migration thêm component weights + is_finalized + source, FE Dashboard + Grades page với 2 luồng nhập (paste myBK + tự nhập GK/TN/BTL/CK với weights). Synthetic 1000 SV để sang M4 (chỉ cần khi train AI + load test)
- [ ] **M4** (Tuần 5-6): AI XGBoost Prediction
- [ ] **M5** (Tuần 7-8): AI RAG Chatbot
- [ ] **M6** (Tuần 9-10): Warnings, Study Plan, Events
- [ ] **M7** (Tuần 11): Admin Minimal Tools
- [ ] **M8** (Tuần 12-13): Integration & Polish
- [ ] **M9** (Tuần 14): Wow Features — optional

## Lệnh Thường Dùng

```bash
# Khởi động Docker stack
docker compose up -d

# Chạy backend local
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tạo Alembic migration
cd backend && alembic revision --autogenerate -m "description"

# Apply migrations
cd backend && alembic upgrade head

# Chạy tests
cd backend && pytest tests/ -v

# Seed dữ liệu
cd backend && python -m app.db.init_db

# Train AI model
cd backend && python -m app.ai.prediction.train
```
