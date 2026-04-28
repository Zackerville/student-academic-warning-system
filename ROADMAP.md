# 🗺️ Implementation Roadmap — AI Student Warning System

> **Phase 1 — Đồ án chuyên ngành:** Hoàn chỉnh cho sinh viên + admin tối giản (~14 tuần)
> **Phase 2 — Đồ án tốt nghiệp:** Hoàn chỉnh admin + research nâng cao (+6-8 tuần)

---

## 🎯 Nguyên Tắc Triển Khai (Backend-Led + FE Companion)

1. **Backend-led**: Backend của mỗi chức năng làm trước, FE làm sau ngay trong cùng milestone
2. **Vertical slice mỗi milestone**: Kết thúc milestone là 1 demo point — chức năng end-to-end work
3. **FE đủ để demo**: Không cần polish UI ngay, chỉ cần hiển thị data và flow chạy được
4. **Polish UI ở M8**: Tuần cuối dành để làm UI đẹp, animation, error states
5. **Deps theo nhu cầu**: Mỗi milestone chỉ cài deps mình cần, không cài thừa

---

## 📊 Tiến Độ Tổng Quan Phase 1

```
[x] M1 — Foundation Setup                            (Tuần 1)        — 4/4 steps ✅ 2026-04-28
[x] M2 — Auth End-to-End + FE Setup     [DEMO 1]    (Tuần 2)        — 8/8 steps ✅ 2026-04-29
[ ] M3 — Student Profile & Grades       [DEMO 2]    (Tuần 3-4)      — 0/6 steps  ← CURRENT
[ ] M4 — AI: XGBoost Prediction         [DEMO 3]    (Tuần 5-6)      — 0/10 steps (+ synthetic data)
[ ] M5 — AI: RAG Chatbot                [DEMO 4]    (Tuần 7-8)      — 0/9 steps
[ ] M6 — Warnings & Study Plan & Events [DEMO 5]    (Tuần 9-10)     — 0/10 steps
[ ] M7 — Admin Minimal Tools            [DEMO 6]    (Tuần 11)       — 0/4 steps
[ ] M8 — Integration & Polish                       (Tuần 12-13)    — 0/6 steps
[ ] M9 — Wow Features (Optional)                    (Tuần 14)       — 0/4 steps
```

**Tổng Phase 1:** 63 steps trong 14 tuần. **6 demo points** trải đều suốt project.

---

## 🎬 Demo Points Map

| Demo | Sau Tuần | User Thấy Được Gì |
|------|----------|-------------------|
| **DEMO 1** | Tuần 2 | Login UI đẹp, đăng ký + đăng nhập SV/admin work, vào dashboard skeleton |
| **DEMO 2** | Tuần 4 | SV xem profile, bảng điểm, đăng ký môn, nhập điểm, GPA tự cập nhật |
| **DEMO 3** | Tuần 6 | SV thấy risk score AI + top-5 lý do tiếng Việt + dự đoán pass/fail từng môn |
| **DEMO 4** | Tuần 8 | Chatbot streaming + citations + tư vấn cá nhân hoá theo data SV |
| **DEMO 5** | Tuần 10 | Cảnh báo học vụ tự động + thông báo + study plan + lịch sự kiện |
| **DEMO 6** | Tuần 11 | Admin import Excel/PDF + trigger AI batch + tools đủ vận hành |

---

# 🏗️ MILESTONE 1: Foundation Setup (Tuần 1)

> **Mục tiêu:** Backend chạy được trong Docker, kết nối PostgreSQL có pgvector, sẵn sàng tạo migration. *Chưa có FE.*

## Step 1.1 — Backend Dependencies (Core only)

**Loại:** Backend
**Chức năng:** Cài deps tối thiểu cho FastAPI + Database + Auth (đủ cho M1 + M2).

**Files:** `backend/requirements.txt`, `backend/Dockerfile`

**Tasks:**
- [ ] Web framework: `fastapi`, `uvicorn[standard]`
- [ ] Database: `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pgvector`
- [ ] Settings: `pydantic`, `pydantic-settings`, `python-multipart`
- [ ] Auth: `python-jose[cryptography]`, `passlib[bcrypt]`
- [ ] Logging: `loguru`
- [ ] Pin versions cụ thể

**Output:**
- ✅ `docker compose build backend` thành công
- ✅ `docker compose up backend` log hiện "Uvicorn running on 0.0.0.0:8000"
- ✅ http://localhost:8000/docs hiện Swagger UI

---

## Step 1.2 — Docker Compose: Lean Stack

**Loại:** Backend
**Chức năng:** Đảm bảo Docker Compose chỉ chạy services đang dùng (db + backend + pgadmin).

**Files:** `docker-compose.yml`

**Tasks:**
- [ ] Giữ `db`, `backend`, `pgadmin` (3 services)
- [ ] Verify Redis, Celery, Frontend vẫn comment

**Output:**
- ✅ `docker compose ps` thấy đúng 3 containers up + healthy
- ✅ `/health` trả `{"status":"ok","database":"connected",...}`

---

## Step 1.3 — Enable pgvector + Base Model

**Loại:** Backend
**Chức năng:** Bật pgvector extension, tạo `db/base.py` cho SQLAlchemy DeclarativeBase.

**Files:** `backend/scripts/init.sql`, `backend/app/db/base.py`, `docker-compose.yml`

**Tasks:**
- [ ] `init.sql`: `CREATE EXTENSION IF NOT EXISTS vector;`
- [ ] Mount init.sql vào db container
- [ ] Tạo `Base = DeclarativeBase()`
- [ ] Recreate db: `docker compose down -v && docker compose up -d`

**Output:**
- ✅ `\dx` trong psql thấy extension `vector`
- ✅ Có thể `CREATE TABLE test (id int, emb vector(3));` không lỗi

---

## Step 1.4 — Alembic Setup

**Loại:** Backend
**Chức năng:** Setup Alembic để quản lý migration.

**Files:** `backend/alembic.ini`, `backend/migrations/env.py`

**Tasks:**
- [ ] `alembic init migrations`
- [ ] Sửa `env.py`: import Base, async engine, target_metadata
- [ ] Set `compare_type=True`, `compare_server_default=True`

**Output:**
- ✅ `alembic current` chạy không lỗi
- ✅ Có thể `alembic revision -m "test"` tạo file trống

---

# 🔐 MILESTONE 2: Auth End-to-End + FE Setup (Tuần 2) — [DEMO 1]

> **Mục tiêu:** SV register/login work end-to-end. FE setup xong với layout cơ bản. Đây là demo đầu tiên.

## Step 2.1 — SQLAlchemy Models (9 bảng)

**Loại:** Backend
**Chức năng:** Định nghĩa toàn bộ data structure (xem chi tiết trong CLAUDE.md).

**Files:** 9 files trong `backend/app/models/` + `__init__.py`

**Tasks:**
- [x] 9 models: user, student, course, enrollment, warning, prediction, notification, event, document
- [x] Quan hệ: User 1-1 Student, Student 1-N Enrollments, Course 1-N Enrollments
- [x] Document model dùng `Vector(768)` từ pgvector
- [x] Enum classes cần thiết
- [x] UUID PK + timestamps cho mọi bảng

**Output:**
- ✅ Import tất cả không lỗi
- ✅ `Base.metadata.tables` có đủ 9 keys

---

## Step 2.2 — First Migration

**Loại:** Backend
**Chức năng:** Tạo migration đầu tiên + apply lên DB.

**Tasks:**
- [x] `alembic revision --autogenerate -m "initial schema"`
- [x] Review migration: pgvector, enums, FK đúng chưa
- [x] `alembic upgrade head`
- [x] Verify trong PgAdmin: 10 bảng (9 + alembic_version)

**Output:**
- ✅ DB có đủ 10 bảng đúng schema
- ✅ `documents.embedding` có type `vector(768)`

---

## Step 2.3 — Pydantic Schemas

**Loại:** Backend
**Chức năng:** Request/response schemas cho API layer.

**Files:** 9 files trong `backend/app/schemas/`

**Tasks:**
- [x] Mỗi entity: `Base`, `Create`, `Update`, `Response`
- [x] User: thêm `UserLogin`, `Token`, `TokenPayload`
- [x] Generic `PaginatedResponse[T]`

**Output:**
- ✅ Import không lỗi
- ✅ Validation hoạt động (email, password length, GPA range)

---

## Step 2.4 — Core Modules: Security + Deps + Logging

**Loại:** Backend
**Chức năng:** Utility cho Auth + Dependencies cho FastAPI.

**Files:** `backend/app/core/security.py`, `deps.py`, `logging.py`

**Tasks:**
- [x] `security.py`: hash_password, verify_password, create_access_token, decode_token
- [x] `deps.py`: get_db, get_current_user, get_current_student, require_admin
- [x] Logging: dùng loguru trực tiếp (`from loguru import logger`), không cần file setup riêng

**Output:**
- ✅ Hash + verify password OK với bcrypt
- ✅ Encode + decode JWT OK với HS256

---

## Step 2.5 — Auth API + Bootstrap Admin

**Loại:** Backend
**Chức năng:** A1, A2, A3, A5 trong feature_list — đăng ký/đăng nhập + tạo admin mặc định.

**Files:** `backend/app/api/v1/__init__.py`, `auth.py`, `backend/app/db/init_db.py`

**Endpoints:**
- [x] `POST /api/v1/auth/register` — Register sinh viên
- [x] `POST /api/v1/auth/login` — Login → JWT
- [x] `GET /api/v1/auth/me` — User info hiện tại

**Tasks:**
- [x] Bootstrap admin trong lifespan: `admin@hcmut.edu.vn / admin123`
- [x] Register tạo cả User + Student record
- [x] Validate email format

**Output:**
- ✅ Đăng ký được SV mới qua Swagger
- ✅ Login đúng/sai → response phù hợp
- ✅ Sau startup đầu, admin account tồn tại

---

## Step 2.6 — Frontend Setup (Next.js + shadcn/ui)

**Loại:** Frontend
**Chức năng:** Khởi tạo Next.js project + cài shadcn/ui + theme cơ bản.

**Tasks:**
- [x] `npx create-next-app@latest frontend --typescript --tailwind --app`
- [x] `npx shadcn-ui@latest init`
- [x] Cài deps: axios, @tanstack/react-query, zustand, zod, react-hook-form, @hookform/resolvers
- [x] Cài shadcn components: button, card, input, label, badge, separator
- [x] Setup `lib/api.ts` Axios client + interceptors
- [x] Setup `lib/auth.ts` auth helpers

**Output:**
- ✅ `docker compose up frontend` → http://localhost:3000 hiện Next.js page
- ✅ Import shadcn `Button` work

---

## Step 2.7 — FE: Theme + API Client + Auth Store

**Loại:** Frontend
**Chức năng:** Hạ tầng FE cho theme + gọi API + quản lý auth state.

**Files:** `frontend/app/layout.tsx`, `globals.css`, `components/providers.tsx`, `theme-toggle.tsx`, `lib/api.ts`, `types.ts`, `stores/auth-store.ts`

**Tasks:**
- [x] Inter font + Vietnamese subset
- [x] HCMUT color palette trong tailwind.config
- [x] Axios instance với interceptors (Bearer token, 401 → logout)
- [x] Zustand auth store (`lib/auth.ts`)
- [x] TypeScript types: User, Student, Token

**Output:**
- ✅ Toggle dark/light mode work
- ✅ `apiClient.get('/auth/me')` tự gắn token
- ✅ Token expire → auto logout + redirect

---

## Step 2.8 — FE: Login + Register + Student Layout Skeleton

**Loại:** Frontend
**Chức năng:** A1, A2 — UI đăng nhập/đăng ký + layout student có sidebar/header.

**Files:**
- `frontend/app/(auth)/layout.tsx`, `login/page.tsx`, `register/page.tsx`
- `frontend/app/(student)/layout.tsx`, `dashboard/page.tsx` (placeholder)
- `frontend/components/student/sidebar.tsx`, `header.tsx`, `user-menu.tsx`
- `frontend/middleware.ts` (auth guard)

**Tasks:**
- [x] Login form: email + password với react-hook-form + zod
- [x] Register form: email + password + mssv + full_name
- [x] Student layout: sidebar + header
- [x] Middleware: auth guard (exact `/`, prefix `/login` `/register`)
- [x] Dashboard placeholder
- [x] Landing page `/` với navbar VI/EN + nút Đăng nhập (thêm ngoài roadmap gốc)

**Output:**
- ✅ Login UI đẹp, validation inline
- ✅ Login flow end-to-end work với backend
- ✅ Sau login redirect dashboard với layout đầy đủ
- ✅ Logout clear token + redirect login

---

## 🎬 [DEMO POINT 1] — Cuối Tuần 2

**Demo flow:**
1. Mở http://localhost:3000 → trang login đẹp
2. Click "Đăng ký" → form đăng ký SV mới
3. Submit form → tự động login → vào dashboard
4. Dashboard hiện sidebar + header + welcome message + 4 placeholder cards
5. Toggle dark mode work, mobile responsive
6. Logout → quay về login

**Báo cáo GVHD:** "Em đã setup xong nền tảng, sang tuần 3 em sẽ làm chức năng quản lý điểm và profile sinh viên."

---

# 📚 MILESTONE 3: Student Profile & Grades (Tuần 3-4) — [DEMO 2]

> **Mục tiêu:** SV xem được profile, bảng điểm, đăng ký môn, nhập điểm, GPA tự tính. Có 1,000 SV synthetic trong DB.

> **Thay đổi vs roadmap gốc:**
> - **Synthetic 1000 SV** (Step 3.3, 3.4 cũ) → dời sang **M4** vì chỉ cần khi train AI + load test
> - **Thêm myBK paste import** — flow chính để SV nhập bảng điểm (Step 3.3 mới)
> - **Schema mới**: thêm `lab_score`, `other_score`, 4 weights, `is_finalized`, `source`, enum `exempt`

## Step 3.1 — BE: GPA Calculator + Pandas Deps

**Loại:** Backend
**Chức năng:** Logic tính GPA HCMUT thang 4 + cài pandas/numpy cho sau này.

**Files:** `backend/requirements.txt`, `backend/app/services/gpa_calculator.py`, `backend/tests/test_gpa_calculator.py`

**Tasks:**
- [ ] Thêm `pandas`, `openpyxl`, `numpy` vào requirements
- [ ] `score_to_grade_letter(score: float) -> str` — Thang HCMUT (A+/A/B+/B/C+/C/D+/D/F)
- [ ] `grade_letter_to_gpa(letter: str) -> float` — A+/A=4.0, B+=3.5, B=3.0, C+=2.5, C=2.0, D+=1.5, D=1.0, F=0
- [ ] `compute_total_from_components(midterm, lab, other, final, weights) -> float | None` — Trả None nếu thiếu điểm cho weight > 0
- [ ] `calculate_semester_gpa(enrollments: list) -> float` — Bỏ qua exempt/withdrawn/DT (credits = 0 hoặc letter đặc biệt)
- [ ] `calculate_cumulative_gpa(student_id, db) -> float`
- [ ] `calculate_gpa_trend(history: list[float]) -> float` — Slope 3 HK gần nhất
- [ ] Unit tests cover: thang điểm, môn F, môn RT, môn MT, weight tùy chỉnh

**Output:**
- ✅ `pytest tests/test_gpa_calculator.py -v` → all passed
- ✅ Convert đúng: 8.5 → A → 4.0; 7.0 → B → 3.0; 4.0 → D → 1.0; 3.9 → F → 0

---

## Step 3.2 — BE: Schema Migration + Student/Course API

**Loại:** Backend
**Chức năng:** Migration schema mới + endpoints cho SV xem/nhập điểm.

**Files:** `backend/migrations/versions/0002_*`, `backend/app/api/v1/students.py`, `courses.py`, `backend/app/models/enrollment.py`

**Migration tasks:**
- [ ] Add columns vào `enrollments`: `lab_score`, `other_score`, `midterm_weight` (default 0.3), `lab_weight` (0), `other_weight` (0), `final_weight` (0.7), `is_finalized` (default false), `source` (default "manual")
- [ ] Update enum `EnrollmentStatus`: thêm `exempt`
- [ ] `alembic revision --autogenerate -m "add component weights and mybk fields"`

**Endpoints (Student):**
- [ ] `GET /students/me` — Profile
- [ ] `GET /students/me/dashboard` — Compound: profile + GPA + warning + noti + events
- [ ] `GET /students/me/grades` — Bảng điểm grouped by semester
- [ ] `POST /students/me/enrollments` — Đăng ký môn (với template weights hoặc tùy chỉnh)
- [ ] `PUT /students/me/enrollments/{id}/grades` — Nhập điểm GK/TN/BTL/CK
- [ ] `GET /students/me/gpa` — GPA tích lũy + GPA HK hiện tại + dự kiến
- [ ] `GET /students/me/gpa/history` — Mảng `[{semester, gpa, credits}]` cho chart

**Endpoints (Course):**
- [ ] `GET /courses?search=&page=1&size=20` — Search by code/name
- [ ] `GET /courses/{id}`

**Logic tasks:**
- [ ] Validation: `midterm_weight + lab_weight + other_weight + final_weight = 1.0` (tolerance 0.001)
- [ ] Khi nhập điểm thành phần → re-compute `total_score` nếu đủ → re-compute `grade_letter` → update `student.gpa_cumulative` + `warning_level`
- [ ] Block edit nếu `is_finalized=true`

**Output:**
- ✅ SV gọi `/dashboard` 1 request → đầy đủ data
- ✅ Nhập điểm CK đầy đủ → GPA tự update real-time
- ✅ Validation reject weights không tổng 100%

---

## Step 3.3 — BE: myBK Paste Parser + Import Endpoint ⭐

**Loại:** Backend
**Chức năng:** Parse text copy từ myBK → upsert enrollments + courses + recompute GPA.

**Files:** `backend/app/services/mybk_parser.py`, `backend/tests/test_mybk_parser.py`, `backend/app/api/v1/students.py`

**Parser tasks:**
- [ ] `parse_mybk_text(raw: str) -> ParsedTranscript`
  - Detect HK header: regex `Năm học (\d{4}) - (\d{4}) / Học kỳ (\d)` → semester code `YYN` (vd: 251)
  - Match course row: regex `^\d+\t([A-Z]{2,3}\d{4})\t...` (10 tab fields)
  - Skip lines: "Tích lũy chung/học kỳ", "Môn học chuyển điểm", header lines
- [ ] Map letter → status:
  - A+/A/B+/B/C+/C/D+/D → `passed`, lưu nguyên score
  - F → `failed`, lưu nguyên score
  - RT → `withdrawn`, **bỏ score** (placeholder)
  - MT → `exempt`, **bỏ score**
  - DT → `passed`, **bỏ score**, ko tính GPA
  - CT/VT/CH/KD/VP/HT → `enrolled` (skip hoặc giữ pending)
- [ ] Tự tạo `Course` nếu chưa có (lấy code + name từ paste)
- [ ] Unit tests với fixture chính là sample của user (đã có)

**Endpoints:**
- [ ] `POST /students/me/grades/import-mybk` body: `{"raw_text": "...", "dry_run": true}`
- [ ] Response (dry_run): `{"semesters": [...], "summary": {"new": N, "updated": M, "errors": [...]}, "preview_gpa": x.x}`
- [ ] Response (commit): same + `{"finalized_count": N}`

**Upsert logic:**
- [ ] Khớp enrollment theo `(student_id, course_id, semester)`
- [ ] Nếu `is_finalized=true` đã set → skip (không override)
- [ ] Nếu môn cũ có component scores SV tự nhập → giữ scores, chỉ thêm `total_score` + set `is_finalized=true`
- [ ] Source = `"mybk_paste"` cho môn mới import

**Output:**
- ✅ Paste sample của user (~70 môn, 9 HK) → parse đúng, không lỗi
- ✅ Re-paste lần 2 → idempotent, không duplicate
- ✅ GPA tính lại khớp với myBK (sai số < 0.05)

---

## Step 3.4 — FE: Dashboard Page

**Loại:** Frontend
**Chức năng:** B1, B2, B5, B6 — tổng quan SV với data thật.

**Files:** `frontend/app/(student)/dashboard/page.tsx`, `components/dashboard/*.tsx`

**Components:**
- [ ] Welcome card (avatar + tên + MSSV + khoa + ngành)
- [ ] 4 stats cards: GPA tích lũy, TC tích lũy, Mức cảnh báo, Số môn đang học
- [ ] GPA line chart qua các HK (Recharts) + ngưỡng warning 1.2/1.0/0.8
- [ ] Notifications gần nhất 3-5 (hardcoded ở M3, real ở M6)
- [ ] Sự kiện sắp tới 3-5 (hardcoded ở M3, real ở M6)
- [ ] Empty state nếu chưa có data: card lớn "Chưa có dữ liệu — Cập nhật từ myBK ngay" → link sang /grades

**Output:**
- ✅ Dashboard load < 1.5s
- ✅ Đầy đủ data từ `/students/me/dashboard`
- ✅ Chart render đẹp với ngưỡng warning

---

## Step 3.5 — FE: Grades Page (2 luồng nhập) ⭐

**Loại:** Frontend
**Chức năng:** C1-C5 — bảng điểm + import myBK + tự nhập GK/TN/BTL/CK.

**Files:** `frontend/app/(student)/grades/page.tsx`, `components/grades/*.tsx`

**Components chính:**
- [ ] Tabs theo HK (sắp xếp giảm dần)
- [ ] Bảng điểm: STT, Mã, Tên, TC, GK, TN, BTL, CK, Tổng kết, Điểm chữ, Trạng thái
- [ ] Cột "Trạng thái" có icon: ✓ Đạt | ✗ Rớt | ⏳ Đang học | 🚫 Rút | 📋 Miễn
- [ ] Footer mỗi tab: GPA HK, TC đăng ký, TC đậu
- [ ] Nút lớn ở header: **"Cập nhật từ myBK"**
- [ ] Nút phụ: "Đăng ký môn cho HK hiện tại"

**Modal "Cập nhật từ myBK":**
- [ ] Tab 1 — Hướng dẫn: 3 bước (mở myBK → trang bảng điểm → Ctrl+A Ctrl+C) với screenshot
- [ ] Tab 2 — Paste & Preview: textarea lớn → click "Xem trước" → call `dry_run=true` → bảng preview group by HK
- [ ] Tab 3 — Xác nhận: hiển thị summary (X môn mới, Y môn cập nhật, Z lỗi) → "Lưu vào hệ thống" → call `dry_run=false`
- [ ] Toast success: "Đã import N môn từ myBK"

**Modal "Đăng ký môn cho HK hiện tại":**
- [ ] Search course (autocomplete `/courses?search=`)
- [ ] Radio chọn template:
  - `Lý thuyết thuần (GK 30% + CK 70%)`
  - `Lý thuyết + TN (30+20+50)`
  - `Lý thuyết + Đồ án (30+0+30+40)`
  - `Đồ án thuần (BTL 100%)`
  - `Báo cáo (CK 100%)`
  - `Tùy chỉnh` → 4 input weight + validation tổng = 100%
- [ ] Submit → `POST /enrollments`

**Modal "Nhập điểm":**
- [ ] Hiển thị 4 ô input GK/TN/BTL/CK theo weights đã set (component nào weight=0 thì disable)
- [ ] Click vào điểm hiện có để sửa
- [ ] What-if calculator: "Cần CK ≥ X.X để đạt B (7.0+)"
- [ ] Submit → `PUT /enrollments/{id}/grades`

**Output:**
- ✅ Paste myBK của bạn → bảng điểm hiện đầy đủ
- ✅ GPA tích lũy match myBK
- ✅ Đăng ký môn HK hiện tại + nhập GK → AI sẽ predict ở M4

---

## Step 3.6 — FE: Notifications Stub + Events Stub

**Loại:** Frontend
**Chức năng:** UI placeholders để dashboard không trống. Logic thật ở M6.

**Tasks:**
- [ ] Dashboard hiện 3-5 notifications hardcoded
- [ ] Dashboard hiện 3-5 events hardcoded
- [ ] Comment `// TODO: M6 — replace với /notifications/me` & `/events/me/upcoming`

**Output:**
- ✅ Dashboard nhìn đầy đủ

---

## 🎬 [DEMO POINT 2] — Cuối Tuần 4

**Demo flow (with real myBK data):**
1. SV mới đăng ký (chưa có data) → dashboard empty state
2. Click "Cập nhật từ myBK" → dán bảng điểm thật → preview → confirm
3. Dashboard refresh: GPA tích lũy đúng, chart 9 HK đẹp, mức cảnh báo hiển thị đúng theo quy chế HCMUT
4. Vào Grades → tabs HK, thấy đầy đủ điểm + cột TN/BTL nếu có
5. Đăng ký môn cho HK đang học (chọn template "Lý thuyết + TN") → môn xuất hiện
6. Nhập điểm GK 7.5 → modal show what-if "Cần CK ≥ 6.79 để được B"

**Báo cáo GVHD:** "Em đã hoàn thành chức năng quản lý điểm với UX import từ myBK — SV không cần nhập tay từng môn. Tuần sau em làm AI dự đoán risk."

---

# 🤖 MILESTONE 4: AI XGBoost Prediction (Tuần 5-6) — [DEMO 3]

> **Mục tiêu:** D1, D2, D3 — SV thấy risk score AI + giải thích SHAP + dự đoán pass/fail từng môn.
>
> **Note:** Synthetic data 1000 SV được dời từ M3 sang đây vì chỉ cần khi train model + load test.

## Step 4.1 — BE: Cài ML Deps

**Loại:** Backend
**Chức năng:** Cài XGBoost + SHAP + Optuna.

**Files:** `backend/requirements.txt`

**Tasks:**
- [ ] Thêm: `xgboost`, `scikit-learn`, `shap`, `optuna`, `joblib`

**Output:**
- ✅ Build container OK, import `xgboost` không lỗi

---

## Step 4.1b — BE: Synthetic Data Generator (1000 SV)

**Loại:** Backend
**Chức năng:** Tạo 1,000 SV synthetic với MSSV pattern `SYN*` để dễ cleanup sau.

**Files:** `backend/scripts/generate_synthetic_data.py`, `backend/scripts/seed_synthetic.py`, `backend/scripts/cleanup_synthetic.py`, `backend/data/synthetic/*.csv`

**Tasks:**
- [ ] 10 khoa, 30 ngành sát HCMUT
- [ ] ~150 courses (CO1xxx-CO5xxx, ngoại ngữ, đại cương)
- [ ] 1,000 SV với MSSV `SYN00001` → `SYN01000`, cohorts 2021-2024
- [ ] Phân bố Gaussian: 15% xuất sắc, 60% TB, 20% yếu, 5% cực yếu
- [ ] ~10% SV có lịch sử cảnh báo (≈ 100 positive samples cho ML)
- [ ] Generate cả component scores + weights (để consistent với schema M3)
- [ ] `seed_synthetic.py` — import vào DB (idempotent)
- [ ] `cleanup_synthetic.py` — `DELETE WHERE mssv LIKE 'SYN%'` xoá toàn bộ + cascade

**Output:**
- ✅ 1,000 students, ~150 courses, ~6,000-10,000 enrollments
- ✅ Histogram GPA giống thực tế
- ✅ ~100 SV warning_level >= 1 (đủ cho ML stratified split)
- ✅ Cleanup script chạy 1 lệnh xoá hết synthetic, giữ admin + SV thật

---

## Step 4.2 — BE: Feature Engineering

**Loại:** Backend
**Chức năng:** Trích xuất 15+ features từ data SV.

**Files:** `backend/app/ai/prediction/features.py`, `tests/test_features.py`

**Tasks:**
- [ ] `extract_features(student_id, db) -> dict` với 15+ features (xem CLAUDE.md)
- [ ] `extract_features_batch(student_ids, db) -> DataFrame`
- [ ] Tests với 3 mock SV

**Output:**
- ✅ Test pass, dict đúng 15+ keys
- ✅ DataFrame columns chuẩn

---

## Step 4.3 — BE: Training Pipeline

**Loại:** Backend
**Chức năng:** Train XGBoost với Optuna tuning + cross-validation.

**Files:** `backend/app/ai/prediction/train.py`, `backend/data/models/`

**Tasks:**
- [ ] Load 1,000 SV → features → DataFrame
- [ ] Target: `is_warned = warning_level >= 1`
- [ ] Train/val/test 70/15/15 stratified
- [ ] Baseline + Optuna tuning (10 trials)
- [ ] Cross-validation 5-fold
- [ ] Evaluate: Accuracy, F1, Precision, Recall, AUC-ROC, Confusion Matrix
- [ ] Save: `xgboost_v1.pkl`, `metrics_v1.json`, `feature_names.json`

**Command:** `python -m app.ai.prediction.train`

**Output:**
- ✅ F1 >= 0.75, AUC-ROC >= 0.85
- ✅ Model file < 5MB
- ✅ Classification report in console

---

## Step 4.4 — BE: SHAP Explainer

**Loại:** Backend
**Chức năng:** D2 — giải thích risk score bằng tiếng Việt.

**Files:** `backend/app/ai/prediction/explainer.py`

**Tasks:**
- [ ] `Explainer` load `shap.TreeExplainer`
- [ ] `explain(features) -> list[RiskFactor]` top-5
- [ ] Map feature name → tiếng Việt: "GPA tích lũy 1.5 (đóng góp +30% rủi ro)"
- [ ] `get_global_importance()`

**Output:**
- ✅ SV nguy cơ cao → top-5 lý do tiếng Việt
- ✅ Format dễ hiểu

---

## Step 4.5 — BE: Prediction Service

**Loại:** Backend
**Chức năng:** Service load model singleton + predict + lưu DB.

**Files:** `backend/app/ai/prediction/model.py`

**Tasks:**
- [ ] `PredictionService` singleton load model lúc startup
- [ ] `predict_single(student_id, db)` lưu Prediction
- [ ] `predict_batch(student_ids, db)`
- [ ] `predict_courses(student_id, db)` heuristic pass/fail
- [ ] Risk level mapping (low/medium/high/critical)

**Output:**
- ✅ Predict 1,000 SV < 10s
- ✅ Bảng predictions có records
- ✅ Distribution risk level hợp lý

---

## Step 4.6 — BE: Predictions API + APScheduler

**Loại:** Backend
**Chức năng:** D1, D2, D3 endpoints + auto batch hàng ngày.

**Files:** `backend/app/api/v1/predictions.py`, `backend/app/core/scheduler.py`, `requirements.txt` (apscheduler)

**Endpoints:**
- [ ] `GET /predictions/me` — Risk score + factors mới nhất
- [ ] `GET /predictions/me/courses` — Pass/fail từng môn
- [ ] `GET /predictions/me/history` — Lịch sử cho chart
- [ ] `POST /predictions/batch-run` — [Admin] Trigger batch

**Tasks:**
- [ ] APScheduler `AsyncIOScheduler` trong lifespan
- [ ] Job daily 02:00 AM chạy batch predict

**Output:**
- ✅ SV gọi `/me` → risk_score + risk_level + factors
- ✅ Admin trigger batch work
- ✅ Scheduler log "Started, 1 job"

---

## Step 4.7 — FE: Predictions Page

**Loại:** Frontend
**Chức năng:** D1, D2, D3 UI.

**Files:** `frontend/app/(student)/predictions/page.tsx`, `components/predictions/*.tsx`

**Components:**
- [ ] Big risk gauge (0-100%) ở giữa với risk_level badge
- [ ] Top-5 risk factors dạng horizontal bar chart
- [ ] Lời giải thích mỗi factor tiếng Việt từ SHAP
- [ ] Bảng dự đoán pass/fail từng môn HK hiện tại với progress bar
- [ ] Lịch sử risk score line chart

**Output:**
- ✅ SV xem được risk score + hiểu rõ tại sao
- ✅ Visualization rõ ràng

---

## Step 4.8 — FE: Update Dashboard với Risk Score

**Loại:** Frontend
**Chức năng:** Thêm risk gauge vào dashboard.

**Tasks:**
- [ ] Update Step 3.5 dashboard: thêm 1 card "Risk Score" với mini gauge
- [ ] Click → navigate `/predictions`

**Output:**
- ✅ Dashboard có thêm risk indicator

---

## 🎬 [DEMO POINT 3] — Cuối Tuần 6

**Demo flow:**
1. Login SV nguy cơ cao (đã chuẩn bị sẵn)
2. Dashboard hiện risk score 75% màu cam
3. Click vào → trang Predictions
4. Big gauge 75% với badge "Cao"
5. Top-5 lý do: "GPA tích lũy 1.5 (+30%)", "Rớt 2 môn HK trước (+25%)",...
6. Bảng dự đoán môn: môn Toán cao cấp 30% pass, môn Vật lý 65% pass

**Báo cáo GVHD:** "Em đã hoàn thành AI dự đoán với XGBoost, F1=0.78. Tuần sau em làm chatbot RAG."

---

# 💬 MILESTONE 5: AI RAG Chatbot (Tuần 7-8) — [DEMO 4]

> **Mục tiêu:** E1, E2 — chatbot quy chế + tư vấn cá nhân với streaming + citations.

## Step 5.1 — BE: Cài RAG Deps + Gemini Setup

**Loại:** Backend
**Chức năng:** Cài LangChain + Gemini libs.

**Files:** `backend/requirements.txt`, `.env.example`

**Tasks:**
- [ ] Thêm: `langchain`, `langchain-google-genai`, `google-generativeai`, `pypdf`, `python-docx`, `tiktoken`, `sse-starlette`
- [ ] `.env.example`: thêm `GEMINI_API_KEY=`
- [ ] Setup Gemini API key (lấy từ aistudio.google.com)

**Output:**
- ✅ Build container OK, import `langchain_google_genai` không lỗi
- ✅ `.env` có Gemini key

---

## Step 5.2 — BE: Document Processing

**Loại:** Backend
**Chức năng:** L1 — đọc PDF/Word, chunk + embed.

**Files:** `backend/app/ai/chatbot/rag.py`, `backend/data/regulations/`

**Tasks:**
- [ ] `parse_pdf` (giữ page number)
- [ ] `parse_docx`
- [ ] `chunk_text(text, 800, 100)` với RecursiveCharacterTextSplitter
- [ ] `embed_text` với Gemini embedding-001 (768 dims)
- [ ] `process_document` → list chunks với metadata

**Output:**
- ✅ PDF 20 trang → 50-80 chunks
- ✅ Mỗi chunk có embedding 768 dims
- ✅ Page number preserved

---

## Step 5.3 — BE: Vector Store Operations

**Loại:** Backend
**Chức năng:** L1, L2, L3, L4 — CRUD documents trong pgvector.

**Files:** `backend/app/ai/chatbot/vectorstore.py`

**Tasks:**
- [ ] `add_document` full pipeline
- [ ] `search_similar` dùng `<=>` operator
- [ ] `delete_document`, `toggle_active`
- [ ] List grouped by source_file

**Output:**
- ✅ Upload PDF → ~50 rows trong DB
- ✅ Search query → top-5 chunks gần nghĩa

---

## Step 5.4 — BE: RAG Chain với LangChain

**Loại:** Backend
**Chức năng:** E1 — chatbot quy chế.

**Files:** `backend/app/ai/chatbot/chains.py`

**Tasks:**
- [ ] `ChatGoogleGenerativeAI(model="gemini-1.5-flash")`
- [ ] Custom retriever wrap pgvector
- [ ] Prompt template tiếng Việt yêu cầu citation
- [ ] `ConversationalRetrievalChain` với memory
- [ ] `ask_question(query, history, db)` + streaming version

**Output:**
- ✅ Hỏi quy chế → trả đúng + citation
- ✅ Multi-turn hiểu context
- ✅ Streaming yields tokens

---

## Step 5.5 — BE: Personalized Chat

**Loại:** Backend
**Chức năng:** E2 — chatbot cá nhân hoá theo data SV.

**Files:** `backend/app/ai/chatbot/personal.py`

**Tasks:**
- [ ] `get_student_context(student_id)` → text profile
- [ ] `personal_chat` inject context vào prompt
- [ ] Heuristic detect intent: regulation vs personal vs hybrid

**Output:**
- ✅ "Tôi có nguy cơ buộc thôi học không?" → trả lời cá nhân với data SV

---

## Step 5.6 — BE: Chatbot API + Documents API

**Loại:** Backend
**Chức năng:** E1, E3, E4 + L1, L2, L3, L4 endpoints.

**Files:** `backend/app/api/v1/chatbot.py`, `documents.py` + migration mới cho `chat_messages`

**Tasks:**
- [ ] Tạo model + migration `chat_messages`
- [ ] `POST /chatbot/ask` streaming SSE
- [ ] `GET /chatbot/history`, `/suggestions`, `DELETE /history`
- [ ] `POST /documents/upload`, `GET /documents`, `PUT /toggle`, `DELETE`

**Output:**
- ✅ FE gọi `/ask` nhận stream SSE
- ✅ History lưu DB
- ✅ Admin upload PDF → chunks tạo

---

## Step 5.7 — FE: Chatbot Page với Streaming

**Loại:** Frontend
**Chức năng:** E1, E2, E3, E4 UI.

**Files:** `frontend/app/(student)/chatbot/page.tsx`, `components/chatbot/*.tsx`

**Components:**
- [ ] Welcome screen với 5 suggested questions chips
- [ ] Message bubbles user/assistant
- [ ] Markdown rendering (react-markdown)
- [ ] Streaming text effect (EventSource hoặc fetch ReadableStream)
- [ ] Citations footnote `[1] Quy chế, trang 12` clickable
- [ ] Auto-scroll, typing indicator
- [ ] Reset conversation

**Output:**
- ✅ UX mượt như ChatGPT
- ✅ Streaming work
- ✅ Citations hiển thị

---

## Step 5.8 — FE: Documents Upload Page (Admin Stub)

**Loại:** Frontend
**Chức năng:** L1, L2 — admin upload PDF (basic UI cho M5 demo).

**Files:** `frontend/app/admin/documents/page.tsx`

**Tasks:**
- [ ] Drag-drop upload PDF
- [ ] List documents grouped + toggle/delete
- [ ] Toast feedback

**Output:**
- ✅ Admin upload PDF qua UI → chunks tạo
- ✅ Bảng documents hiển thị

---

## 🎬 [DEMO POINT 4] — Cuối Tuần 8

**Demo flow:**
1. Login admin → upload PDF quy chế HCMUT
2. Login SV → vào Chatbot
3. Hỏi: "GPA bao nhiêu thì bị cảnh báo mức 1?"
4. AI streaming text reply với citation [1]
5. Hỏi tiếp: "Còn mức 2?" → multi-turn hiểu context
6. Hỏi: "Tôi có nguy cơ buộc thôi học không?" → AI trả lời cá nhân với data SV

**Báo cáo GVHD:** "Em đã hoàn thành chatbot RAG với streaming + citations. Tuần sau em làm cảnh báo + sự kiện."

---

# ⚠️ MILESTONE 6: Warnings, Study Plan, Events (Tuần 9-10) — [DEMO 5]

> **Mục tiêu:** D4, D5, F1-F3, G1-G3 — cảnh báo tự động + thông báo + study plan + lịch sự kiện.

## Step 6.1 — BE: Warning Engine Service

**Loại:** Backend
**Chức năng:** Logic cảnh báo theo quy chế HCMUT + AI early warning.

**Files:** `backend/app/services/warning_engine.py`, `tests/test_warning_engine.py`

**Tasks:**
- [ ] `check_regulation_warning(student) -> int` (0-3)
- [ ] `check_ai_early_warning(student, prediction) -> bool`
- [ ] `create_warning(...)` + tự tạo notification
- [ ] `batch_check_warnings(db)` idempotent

**Output:**
- ✅ Test pass 5 scenarios
- ✅ Warning + notification được tạo

---

## Step 6.2 — BE: Notification + Recommender Services

**Loại:** Backend
**Chức năng:** G1, G2 + F1, F2, F3.

**Files:** `backend/app/services/notification.py`, `recommender.py`

**Tasks:**
- [ ] Notification CRUD + unread count
- [ ] `recommend_credit_load` rule-based theo GPA
- [ ] `recommend_retake_courses`
- [ ] `generate_study_plan`

**Output:**
- ✅ Notification work
- ✅ Recommender trả về study plan logic

---

## Step 6.3 — BE: Warnings + Notifications + Study Plan APIs

**Loại:** Backend
**Chức năng:** D4, D5, G1, G2, F1, F3 endpoints.

**Files:** `backend/app/api/v1/warnings.py`, `notifications.py`, `study_plan.py`

**Endpoints:**
- [ ] `GET /warnings/me`, `/warnings/me/{id}`, `POST /warnings/batch-run` [Admin]
- [ ] `GET /notifications/me?is_read=false`, `/unread-count`, `PUT /{id}/read`, `PUT /me/read-all`
- [ ] `GET /study-plan/me`, `/study-plan/me/credit-load`

**Output:**
- ✅ Tất cả endpoints work với schema chuẩn

---

## Step 6.4 — BE: Events API

**Loại:** Backend
**Chức năng:** G3 + admin tạo events.

**Files:** `backend/app/api/v1/events.py`

**Endpoints:**
- [ ] `POST /events` [Admin], `GET /events` [Admin], `PUT /{id}` [Admin], `DELETE /{id}` [Admin]
- [ ] `GET /events/me`, `/events/me/upcoming`

**Output:**
- ✅ Admin CRUD events
- ✅ SV thấy events theo target audience

---

## Step 6.5 — FE: Warnings Page

**Loại:** Frontend
**Chức năng:** D4, D5 UI.

**Files:** `frontend/app/(student)/warnings/page.tsx`, `components/warnings/*.tsx`

**Components:**
- [ ] Hero card tình trạng cảnh báo hiện tại
- [ ] Timeline lịch sử
- [ ] Click → dialog chi tiết
- [ ] Empty state đẹp

**Output:**
- ✅ Timeline color-coded theo level

---

## Step 6.6 — FE: Notifications Center (Header + Page)

**Loại:** Frontend
**Chức năng:** G1, G2 UI.

**Files:** `components/notifications-popover.tsx`, `app/(student)/notifications/page.tsx`

**Components:**
- [ ] Bell icon + badge count (poll 30s)
- [ ] Dropdown 5 noti gần nhất
- [ ] Click noti → mark read + navigate
- [ ] Trang full với pagination

**Output:**
- ✅ Badge real-time
- ✅ Click cảnh báo → /warnings/{id}

---

## Step 6.7 — FE: Study Plan Page

**Loại:** Frontend
**Chức năng:** F1, F2, F3 UI.

**Files:** `frontend/app/(student)/study-plan/page.tsx`, `components/study-plan/*.tsx`

**Components:**
- [ ] Card credit load (min/recommended/max)
- [ ] Card retake courses
- [ ] Card suggested courses
- [ ] One-click enroll

**Output:**
- ✅ Recommendations rõ ràng

---

## Step 6.8 — FE: Events Page

**Loại:** Frontend
**Chức năng:** G3 UI.

**Files:** `frontend/app/(student)/events/page.tsx`, `components/events/*.tsx`

**Components:**
- [ ] Toggle Calendar ↔ List view
- [ ] Calendar tháng
- [ ] Filter theo loại
- [ ] Detail dialog

**Output:**
- ✅ Calendar đúng events
- ✅ Click work

---

## Step 6.9 — FE: Update Dashboard với Real Notifications & Events

**Loại:** Frontend
**Chức năng:** Replace placeholders ở Step 3.7 bằng data thật.

**Tasks:**
- [ ] Dashboard noti = `/notifications/me?limit=5&unread=true`
- [ ] Dashboard events = `/events/me/upcoming?limit=5`

**Output:**
- ✅ Dashboard data 100% thật

---

## Step 6.10 — BE+FE: Warning Auto-Trigger After Grade Update

**Loại:** Backend + Frontend
**Chức năng:** Khi SV nhập điểm CK → check warning ngay.

**Tasks:**
- [ ] BE: hook trong `PUT /enrollments/{id}/grades` → call `check_regulation_warning` + AI predict
- [ ] FE: nếu response có new warning → toast warning ngay

**Output:**
- ✅ Demo flow: nhập điểm thấp → xuất hiện cảnh báo + notification

---

## 🎬 [DEMO POINT 5] — Cuối Tuần 10

**Demo flow:**
1. Login SV trung bình
2. Vào Grades → nhập điểm CK rất thấp cho 2 môn
3. Toast hiện "Cảnh báo mức 1 đã được tạo"
4. Notification badge tăng → click → vào /warnings
5. Timeline có cảnh báo mới + chi tiết lý do
6. Vào Study Plan → AI gợi ý giảm TC, học lại 2 môn rớt
7. Vào Events → calendar có lịch thi cuối kỳ + sinh hoạt cô ng dân

**Báo cáo GVHD:** "Em đã hoàn thành flow cảnh báo end-to-end. Tuần sau em làm admin tools."

---

# 🛠️ MILESTONE 7: Admin Minimal Tools (Tuần 11) — [DEMO 6]

> **Mục tiêu:** J1, J2, J5, K1 + L1 — admin import data + trigger AI + upload quy chế.

## Step 7.1 — BE: Import Service + Admin APIs

**Loại:** Backend
**Chức năng:** J1, J2, J5 import + templates.

**Files:** `backend/app/services/import_service.py`, `app/api/v1/admin.py`, `backend/data/templates/*.xlsx`

**Endpoints:**
- [ ] `POST /admin/import/students`
- [ ] `POST /admin/import/grades`
- [ ] `GET /admin/templates/students`, `/templates/grades`
- [ ] `GET /admin/import/history` (optional)

**Tasks:**
- [ ] Pandas parse Excel + validate
- [ ] Báo lỗi cụ thể (row, column, reason)
- [ ] Idempotent upsert
- [ ] Sau grades import → tự update GPA
- [ ] Tạo templates với header + example row

**Output:**
- ✅ File đúng → import success
- ✅ File sai → errors list rõ ràng

---

## Step 7.2 — FE: Admin Layout + Auth Guard

**Loại:** Frontend
**Chức năng:** A5 — admin RBAC layout.

**Files:** `frontend/app/admin/layout.tsx`, `middleware.ts` update

**Tasks:**
- [ ] Middleware: `/admin/*` chỉ cho role=admin
- [ ] Header đơn giản với logo + user menu
- [ ] Tabs hoặc sections cho 4 tools

**Output:**
- ✅ Admin login → redirect /admin
- ✅ Student vào /admin → redirect /

---

## Step 7.3 — FE: Admin Tools Page (4 sections)

**Loại:** Frontend
**Chức năng:** J1, J2, J5, K1, L1 trong 1 trang.

**Files:** `frontend/app/admin/page.tsx`, `components/admin/*.tsx`

**Sections:**
- [ ] **Import Students**: drag-drop Excel + download template + result table
- [ ] **Import Grades**: tương tự
- [ ] **RAG Documents** (đã có ở Step 5.8, refine UI): upload PDF + bảng documents + toggle/delete + reload button
- [ ] **AI Triggers**: button "Run Batch Prediction" + "Run Warning Check" + last run time + status

**Output:**
- ✅ Upload Excel → import success + summary
- ✅ Upload PDF → chunks tạo
- ✅ Trigger button → toast + status update

---

## Step 7.4 — Test Full Admin Flow

**Loại:** Integration
**Chức năng:** Verify flow admin end-to-end.

**Tasks:**
- [ ] Reset DB → admin login → import students.xlsx (50 SV)
- [ ] Import grades.xlsx (200 records)
- [ ] Upload quy chế.pdf
- [ ] Trigger batch prediction → 50 SV có prediction
- [ ] Trigger warning check → cảnh báo tự tạo cho SV nguy cơ
- [ ] SV login → thấy data + cảnh báo

**Output:**
- ✅ Admin tự setup được hệ thống không cần seed script

---

## 🎬 [DEMO POINT 6] — Cuối Tuần 11

**Demo flow:**
1. Login admin
2. Section 1: Upload `students_50.xlsx` → 50 imported
3. Section 2: Upload `grades_200.xlsx` → 200 records, GPA tự cập nhật
4. Section 3: Upload `quy_che_v2.pdf` → 60 chunks tạo
5. Section 4: Click "Run Batch Prediction" → 50 SV có prediction
6. Logout → login 1 SV → dashboard đầy đủ

**Báo cáo GVHD:** "Hệ thống có thể tự vận hành từ admin. 2 tuần cuối em polish UI và viết báo cáo."

---

# 🧪 MILESTONE 8: Integration & Polish (Tuần 12-13)

> **Mục tiêu:** Hệ thống production-quality. UI đẹp polish. Bug-free. Documented. Demo-ready.

## Step 8.1 — End-to-End Testing 4 Flows

**Tasks:**
- [ ] Flow 1: SV register → login → grades → predictions
- [ ] Flow 2: SV chat về quy chế + tư vấn cá nhân
- [ ] Flow 3: Admin import → batch → SV nhận warning
- [ ] Flow 4: Admin upload PDF → SV hỏi content mới
- [ ] Document test steps trong `docs/test-flows.md`
- [ ] Fix bugs phát hiện

**Output:**
- ✅ 4 flows pass không bug critical
- ✅ Mobile responsive OK

---

## Step 8.2 — UI Polish (Animation, Empty States, Errors)

**Tasks:**
- [ ] Framer Motion transitions cho page navigation
- [ ] Skeleton loaders cho mọi page
- [ ] Empty states với illustration SVG (undraw.co)
- [ ] Error boundaries (Next.js error.tsx)
- [ ] 404 page custom
- [ ] Toast cho mọi action
- [ ] Hover states + focus rings đẹp
- [ ] Consistent spacing/typography

**Output:**
- ✅ UI cảm giác như SaaS production
- ✅ Lighthouse design score >= 90

---

## Step 8.3 — Performance Optimization

**Tasks:**
- [ ] Backend: eager loading (selectinload) cho N+1
- [ ] Backend: cache hot endpoints (optional Redis nếu cần)
- [ ] Frontend: React Query staleTime config
- [ ] Frontend: lazy load charts với dynamic import
- [ ] Frontend: next/image cho images
- [ ] Backend: indexes cho columns hay query

**Output:**
- ✅ Dashboard load < 1s
- ✅ Chatbot first token < 2s
- ✅ Lighthouse perf >= 85

---

## Step 8.4 — Documentation

**Files:** `README.md`, `docs/architecture.md`, `ai-models.md`, `api-reference.md`, `deployment.md`

**Tasks:**
- [ ] README với 5-10 screenshots + GIF demo
- [ ] Hướng dẫn cài đặt (Win/Linux/Mac)
- [ ] Architecture diagram (Mermaid)
- [ ] AI models doc: features, training, metrics, SHAP examples
- [ ] API reference link Swagger
- [ ] Deployment guide

**Output:**
- ✅ Dev khác clone + chạy < 15 phút

---

## Step 8.5 — Deploy

**Tasks:**
- [ ] Deploy lên Railway hoặc Render free tier
- [ ] Tạo 5 demo accounts đặc biệt:
  - SV xuất sắc (GPA 3.8+)
  - SV trung bình (GPA 2.5)
  - SV cảnh báo mức 1
  - SV cảnh báo mức 2
  - SV nguy cơ buộc thôi học

**Output:**
- ✅ Demo URL public live
- ✅ 5 accounts ready

---

## Step 8.6 — Demo Materials

**Tasks:**
- [ ] Quay video demo 5-7 phút
- [ ] Slide thuyết trình 15-20 slides
- [ ] Báo cáo đồ án 80-100 trang

**Output:**
- ✅ Video YouTube unlisted
- ✅ Slide + báo cáo final

---

# ✨ MILESTONE 9: Wow Features (Tuần 14 / Buffer)

> Chỉ làm sau khi M1-M8 đã xong. Skip nếu hết thời gian.

## Step 9.1 — Personalized Greeting & Insights
- [ ] "Chào An! GPA tăng 0.2 so với HK trước 🎉"
- [ ] Insights cards trên dashboard

## Step 9.2 — Risk Simulator (What-If)
- [ ] Page `/predictions/simulator`
- [ ] Slider điểm môn → real-time risk update
- [ ] Compare với risk hiện tại

## Step 9.3 — Onboarding Tour
- [ ] react-joyride first login
- [ ] Highlight từng phần với tooltip
- [ ] Skip + complete

## Step 9.4 — Smart Suggested Questions
- [ ] 5 câu hỏi gợi ý động theo context SV
- [ ] SV cảnh báo → "Làm sao thoát cảnh báo?"
- [ ] Update `/chatbot/suggestions`

---

# 📅 PHASE 2 — Đồ Án Tốt Nghiệp (Tóm Tắt)

## Phần A: Admin Portal Hoàn Chỉnh (3-4 tuần)
- Admin Dashboard với charts + stats
- Quản lý SV: table + filter + search + chi tiết
- Duyệt cảnh báo AI trước khi gửi
- Cấu hình ngưỡng cảnh báo
- Quản lý sự kiện đầy đủ
- Báo cáo PDF/Excel
- Email notifications
- Lịch sử import + xử lý lỗi

## Phần B: Research Enhancement (3-4 tuần)
- So sánh models: XGBoost vs LightGBM vs LSTM
- Recommender hybrid (CF + Content-Based)
- Real data integration
- WebSocket real-time
- Monitoring (Prometheus + Grafana)
- Paper draft + benchmark

---

# 📈 Tracking Convention

Mỗi step có 3 trạng thái:
- `[ ]` — Chưa làm
- `[~]` — Đang làm (in progress)
- `[x]` — Đã làm xong

Sau mỗi step, tôi sẽ:
1. Cập nhật checkbox trong file này
2. Yêu cầu bạn verify (chạy command/test cụ thể trong "Output")
3. Đợi confirmation rồi qua step tiếp

Sau mỗi **Demo Point**, dừng lại để bạn report với GVHD.

---

**Last updated:** 2026-04-29
**Current step:** M3 — Student Profile & Grades (Step 3.1)
