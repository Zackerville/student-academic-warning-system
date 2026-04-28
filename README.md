# 🎓 AI Student Warning System

> Hệ thống Cảnh báo Học vụ thông minh cho Trường Đại học Bách Khoa TP.HCM

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)

---

## 📌 Giới thiệu

Hệ thống AI hỗ trợ **sinh viên chủ động theo dõi tình hình học tập**, nhận cảnh báo sớm về nguy cơ học vụ và được tư vấn quy chế trực tiếp qua chatbot AI — giúp sinh viên có cơ hội cải thiện kết quả trước khi bị xử lý kỷ luật học vụ.

Ở chiều ngược lại, **Văn phòng Đào tạo** sử dụng hệ thống để import dữ liệu điểm, vận hành AI batch prediction và quản lý toàn bộ danh sách sinh viên có nguy cơ.

### 👨‍🎓 Tính năng dành cho Sinh viên (Người dùng chính)
- 📊 **Dashboard cá nhân** – Xem GPA theo từng học kỳ, số tín chỉ tích lũy, mức cảnh báo hiện tại
- 📥 **Cập nhật từ myBK** – Copy bảng điểm từ myBK và paste để hệ thống tự nhận
- 🔮 **Risk Score AI** – Biết mức độ nguy cơ học vụ (0–100%) và lý do cụ thể (feature importance)
- 🎯 **Dự đoán từng môn** – AI dự báo khả năng pass/fail cho các môn đang học dựa trên điểm GK/TN
- 💬 **Chatbot tư vấn quy chế** – Hỏi đáp RAG dựa trên quy chế đào tạo ĐHBK, có trích dẫn văn bản gốc
- 📋 **Kế hoạch học tập** – Gợi ý chiến lược đăng ký môn, số TC phù hợp cho học kỳ tới
- 🔔 **Thông báo & Sự kiện** – Nhận thông báo cảnh báo sớm, nhắc nhở deadline thi/nộp bài

### 🏛️ Tính năng dành cho Văn phòng Đào tạo
- 📥 **Import dữ liệu** – Upload Excel danh sách SV và bảng điểm hàng học kỳ
- ⚡ **Batch Prediction** – Chạy AI đánh giá rủi ro toàn bộ sinh viên bằng một thao tác
- 📈 **Dashboard tổng quan** – Phân bố risk level, top SV nguy cơ cao, thống kê theo khoa/ngành
- ✅ **Duyệt & gửi cảnh báo** – Xem xét kết quả AI, duyệt cảnh báo trước khi gửi cho sinh viên
- 📄 **Quản lý quy chế RAG** – Upload/cập nhật tài liệu quy chế đào tạo cho chatbot

---

## 🏗️ Kiến trúc hệ thống

```
student-academic-warning-system/
├── backend/                # FastAPI + Python 3.11
│   ├── app/
│   │   ├── ai/             # ML models (XGBoost) & RAG engine
│   │   ├── api/v1/         # API routers
│   │   ├── core/           # Config, security, deps
│   │   ├── db/             # Session, base, init_db
│   │   ├── models/         # SQLAlchemy ORM (9 bảng)
│   │   ├── schemas/        # Pydantic request/response
│   │   └── services/       # Business logic (warning_engine, mybk_parser, ...)
│   ├── data/               # Synthetic CSVs + RAG PDF docs
│   ├── migrations/         # Alembic migrations
│   ├── scripts/            # init.sql, seed, cleanup synthetic
│   └── tests/              # pytest
├── frontend/               # Next.js 14 (App Router) + TypeScript
│   ├── app/                # Pages & layouts
│   ├── components/         # shadcn/ui + custom
│   └── lib/                # Axios client, auth store
├── docs/                   # Tài liệu đồ án
├── docker-compose.yml      # PostgreSQL + Backend + PgAdmin
├── .env.example
├── Makefile
├── CLAUDE.md               # Project context cho AI assistant
├── roadmap.md              # 9 milestones, 14 tuần
├── feature_list.md         # 67 chức năng chi tiết
└── implementation_plan.md  # Kế hoạch triển khai
```

---

## 🚀 Cài đặt từ đầu (Lần đầu chạy project)

### Yêu cầu

- **Docker Desktop** v4.20+ (kèm Docker Compose v2)
- **Node.js** v20 LTS (để chạy frontend local)
- **Git**

> Backend chạy trong Docker — không cần cài Python/Postgres trực tiếp trên máy.

### Bước 1 — Clone repo và tạo `.env`

```bash
git clone https://github.com/Zackerville/student-academic-warning-system.git
cd student-academic-warning-system
cp .env.example .env
```

### Bước 2 — Sửa `.env` (BẮT BUỘC)

Mở file `.env`, **sửa 2 dòng sau** để đồng bộ credentials với `docker-compose.yml`:

```bash
POSTGRES_USER=admin
POSTGRES_PASSWORD=zackerville2004
```

> ⚠️ **Lưu ý quan trọng:** `docker-compose.yml` đang hardcode connection string với user `admin` và password `zackerville2004`. Nếu để giá trị mặc định trong `.env.example` thì backend không kết nối được DB.

### Bước 3 — Khởi động database

```bash
docker compose up -d db
```

Đợi ~10 giây cho DB pass healthcheck. Verify:

```bash
docker compose ps
# db phải có status "Up (healthy)"
```

### Bước 4 — Chạy migration tạo 9 bảng

```bash
docker compose run --rm backend alembic upgrade head
```

Lệnh này tự build image backend nếu chưa có, rồi apply migration. Sau khi chạy xong, DB sẽ có 10 bảng (9 entities + `alembic_version`).

### Bước 5 — Khởi động backend

```bash
docker compose up -d backend
```

Trong lifespan, backend sẽ tự tạo admin mặc định: `admin@hcmut.edu.vn / admin123`.

**Verify:**
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health) → trả `{"status":"ok","database":"connected"}`

### Bước 6 — Cài đặt và chạy frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend chạy ở [http://localhost:3000](http://localhost:3000)

> **Chưa cài Node.js?** `winget install OpenJS.NodeJS.LTS` (Windows) hoặc tải từ [nodejs.org](https://nodejs.org) (chọn LTS v20).

---

## 🔄 Các lần chạy sau (đã setup rồi)

```bash
# Khởi động toàn bộ
docker compose up -d              # db + backend
cd frontend && npm run dev        # frontend

# Dừng toàn bộ
docker compose down
# Ctrl+C trong terminal frontend
```

---

## 🌐 Endpoints sau khi chạy

| Service | URL | Tài khoản |
|---------|-----|-----------|
| **Frontend** | [http://localhost:3000](http://localhost:3000) | Xem bảng dưới |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | — |
| **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | — |
| **Health Check** | [http://localhost:8000/health](http://localhost:8000/health) | — |
| **PgAdmin** | [http://localhost:5050](http://localhost:5050) | `admin@admin.com` / `admin123` |

### Tài khoản mặc định

| Role | Email | Password |
|------|-------|----------|
| **Admin** | `admin@hcmut.edu.vn` | `admin123` |
| **Sinh viên** | Đăng ký mới qua trang `/register` | — |

---

## ⚙️ Lệnh hữu ích

### Backend (Docker)

```bash
# Xem logs realtime
docker compose logs -f backend

# Vào shell container
docker compose exec backend bash

# Tạo migration mới sau khi sửa model
docker compose exec backend alembic revision --autogenerate -m "your message"

# Apply migration
docker compose exec backend alembic upgrade head

# Mở psql shell
docker compose exec db psql -U admin -d warning_ai_db

# Chạy tests
docker compose exec backend pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm run dev      # Dev server với hot reload
npm run build    # Build production
npm run start    # Chạy production build
npm run lint     # Kiểm tra ESLint
```

### Reset toàn bộ database (cẩn thận!)

```bash
docker compose down -v          # Xoá containers + volumes
docker compose up -d db         # Tạo DB mới
docker compose run --rm backend alembic upgrade head
docker compose up -d backend
```

---

## 🐛 Troubleshooting

### Backend không start được, log báo "password authentication failed"

→ Bạn quên sửa `POSTGRES_USER=admin` và `POSTGRES_PASSWORD=zackerville2004` trong `.env`.

**Fix:**
```bash
docker compose down -v          # xoá DB volume cũ (credentials cũ)
# Sửa .env
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose up -d backend
```

### Frontend báo lỗi `npm: command not found`

→ Chưa cài Node.js. Cài theo Bước 6 phần trên.

### Port 5432, 8000, 3000, 5050 đã bị dùng

→ Tắt service đang dùng port đó, hoặc đổi port trong `.env`:

```bash
POSTGRES_PORT=5433
BACKEND_PORT=8001
```

### `docker compose run` báo lỗi network

→ DB chưa healthy. Đợi thêm rồi retry:
```bash
docker compose ps         # check db status = "healthy"
```

---

## 🗓️ Tiến độ phát triển (xem [roadmap.md](roadmap.md))

| Milestone | Mục tiêu | Trạng thái |
|-----------|----------|-----------|
| **M1** | Foundation Setup | ✅ Done |
| **M2** | Auth End-to-End + FE Setup | ✅ Done |
| **M3** | Student Profile & Grades + myBK paste | 🚧 In progress |
| **M4** | AI XGBoost Prediction | ⬜ Pending |
| **M5** | RAG Chatbot (Gemini) | ⬜ Pending |
| **M6** | Warnings, Study Plan, Events | ⬜ Pending |
| **M7** | Admin Minimal Tools | ⬜ Pending |
| **M8** | Integration & Polish | ⬜ Pending |
| **M9** | Wow Features (optional) | ⬜ Pending |

---

## 📚 Tech Stack

| Layer | Công nghệ | Ghi chú |
|-------|-----------|---------|
| Backend | FastAPI 0.111 (Python 3.11), async | Swagger tự sinh |
| Database | PostgreSQL 16 + pgvector | Quan hệ + vector search 1 DB |
| Cache/Scheduler | APScheduler (in-process) | Thay Celery để giảm complexity |
| AI Prediction | XGBoost + SHAP | Risk score + feature importance |
| AI Chatbot | LangChain + Gemini 1.5 Flash | RAG tư vấn quy chế |
| AI Embeddings | Google `models/embedding-001` | 768 dims → pgvector |
| Frontend | Next.js 14 (App Router) + TypeScript | shadcn/ui + Tailwind |
| Container | Docker + Docker Compose | DB + Backend + PgAdmin |

---

## 📖 Tài liệu liên quan

- [`CLAUDE.md`](CLAUDE.md) — Project context, schema, conventions, warning logic HCMUT
- [`roadmap.md`](roadmap.md) — 9 milestones × 14 tuần × 6 demo points
- [`feature_list.md`](feature_list.md) — 67 chức năng chi tiết với mức ưu tiên
- [`implementation_plan.md`](implementation_plan.md) — Kế hoạch triển khai theo phase

---

## 👤 Tác giả

**Zackerville** — Đồ án chuyên ngành CS, ĐH Bách Khoa TP.HCM

GitHub: [@Zackerville](https://github.com/Zackerville)
