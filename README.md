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
- 🔮 **Risk Score AI** – Biết mức độ nguy cơ học vụ (0–100%) và lý do cụ thể (feature importance)
- 🎯 **Dự đoán từng môn** – AI dự báo khả năng pass/fail cho các môn đang học
- 💬 **Chatbot tư vấn quy chế** – Hỏi đáp RAG dựa trên quy chế đào tạo ĐHBK, được trả lời kèm trích dẫn văn bản gốc
- 📋 **Kế hoạch học tập** – Gợi ý chiến lược đăng ký môn, số TC phù hợp cho học kỳ tới
- 🔔 **Thông báo & Sự kiện** – Nhận thông báo cảnh báo sớm, nhắc nhở deadline thi/nộp bài

### 🏛️ Tính năng dành cho Văn phòng Đào tạo (Người dùng phụ)
- 📥 **Import dữ liệu** – Upload Excel danh sách SV và bảng điểm hàng học kỳ
- ⚡ **Batch Prediction** – Chạy AI đánh giá rủi ro toàn bộ sinh viên bằng một thao tác
- 📈 **Dashboard tổng quan** – Phân bố risk level, top SV nguy cơ cao, thống kê theo khoa/ngành
- ✅ **Duyệt & gửi cảnh báo** – Xem xét kết quả AI, duyệt cảnh báo trước khi gửi cho sinh viên
- 📄 **Quản lý quy chế RAG** – Upload/cập nhật tài liệu quy chế đào tạo cho chatbot

---

## 🏗️ Kiến trúc hệ thống

```
WarningAI_system/
├── backend/               # FastAPI + Python
│   ├── app/
│   │   ├── ai/            # ML models & RAG engine
│   │   ├── api/           # API routers (v1)
│   │   ├── core/          # Config, security, logging
│   │   ├── db/            # Database session & base
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   └── services/      # Business logic layer
│   ├── data/              # Sample data, CSV, PDF docs
│   ├── migrations/        # Alembic migration files
│   └── tests/             # Unit & integration tests
├── frontend/              # Next.js 14 (App Router)
│   ├── app/               # Pages & layouts
│   ├── components/        # Reusable UI components
│   └── lib/               # API clients, utils
├── docs/                  # Project documentation
└── docker-compose.yml     # Local development stack
```

---

## 🚀 Khởi chạy nhanh (Quick Start)

### Yêu cầu
- Docker & Docker Compose v2+
- Node.js 20+ (cho frontend dev local)
- Python 3.11+ (cho backend dev local)

### 1. Clone & cấu hình môi trường
```bash
git clone <repo-url>
cd WarningAI_system
cp .env.example .env
# Chỉnh sửa .env với các giá trị thực của bạn
```

### 2. Chạy toàn bộ stack với Docker
```bash
docker compose up -d
```

Sau khi khởi động:
| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PgAdmin | http://localhost:5050 |

### 3. Chạy local (development)
```bash
# Backend
make dev-backend

# Frontend (terminal khác)
make dev-frontend
```

---

## ⚙️ Các lệnh hữu ích (Makefile)

```bash
make help          # Xem tất cả lệnh
make up            # Khởi động Docker stack
make down          # Dừng Docker stack
make dev-backend   # Chạy backend dev server
make dev-frontend  # Chạy frontend dev server
make migrate       # Chạy Alembic migrations
make test          # Chạy toàn bộ tests
make lint          # Kiểm tra code style
make seed          # Seed dữ liệu mẫu vào DB
```

---

## 🗓️ Kế hoạch phát triển (14 tuần)

| Tuần | Mục tiêu |
|---|---|
| 1–2 | Thiết lập môi trường, Auth (JWT), RBAC |
| 3–4 | CRUD Students, Courses, Grades |
| 5–6 | AI Pipeline – ML Risk Prediction |
| 7–8 | RAG Chatbot Engine |
| 9–10 | Event Management & Notification |
| 11–12 | Frontend – Student Portal & Admin Dashboard |
| 13 | Integration Testing & Performance |
| 14 | Deployment & Documentation |

---

## 👥 Đóng góp

1. Fork repository
2. Tạo feature branch: `git checkout -b feature/ten-tinh-nang`
3. Commit: `git commit -m "feat: mô tả ngắn gọn"`
4. Push & mở Pull Request

---

## 📄 Giấy phép

MIT License – © 2025 HCMUT
