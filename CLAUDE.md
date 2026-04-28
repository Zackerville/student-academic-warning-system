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
| semester | VARCHAR | VD: 241 (HK1 2024-2025) |
| midterm_score | FLOAT nullable | Điểm GK |
| final_score | FLOAT nullable | Điểm CK |
| total_score | FLOAT nullable | Điểm tổng kết |
| grade_letter | VARCHAR nullable | A+, A, B+,... F |
| status | ENUM(enrolled, passed, failed, withdrawn) | |
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
- [x] Project structure
- [x] Docker Compose (PostgreSQL + pgAdmin)
- [x] `main.py` — FastAPI app entry
- [x] `core/config.py` — Settings từ .env
- [x] `db/session.py` — AsyncSession factory + health check
- [x] `.env.example`, `Makefile`, `pyproject.toml`, `docker-compose.yml`
- [x] **Step 1 (M1)**: 9 SQLAlchemy models + `db/base.py` + Alembic (alembic.ini + async env.py) + `scripts/init.sql` + pyrightconfig.json

### Cần làm (theo thứ tự):
- [x] **Step 1 (M1)**: Foundation Setup — __init__.py, requirements.txt, db/base.py, scripts/init.sql, Alembic (alembic.ini + async env.py) ✅ 2026-04-28
- [ ] **Step 2 (M2)**: SQLAlchemy models (9 bảng) + First migration + Pydantic schemas + Auth API + FE Setup
- [ ] **Step 3**: DB init_db.py + seed data + Auth API
- [ ] **Step 4**: Student API + Admin API (CRUD cơ bản)
- [ ] **Step 5**: Import service (Excel/CSV)
- [ ] **Step 6**: Synthetic data generation (1,000 SV, 6 HK)
- [ ] **Step 7**: XGBoost training + prediction API
- [ ] **Step 8**: RAG chatbot (Gemini + pgvector)
- [ ] **Step 9**: Warning engine + Notification service
- [ ] **Step 10**: Frontend setup (Next.js + shadcn/ui)
- [ ] **Step 11**: Frontend — Student pages
- [ ] **Step 12**: Frontend — Admin pages
- [ ] **Step 13**: Integration testing + Polish

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
