# Kiến trúc hệ thống — AI Warning System (HCMUT)

Tài liệu này mô tả kiến trúc tổng thể, các luồng dữ liệu chính, và rule thiết kế của hệ thống. Tất cả diagram dùng Mermaid — render trực tiếp trên GitHub, VSCode, Marp, hoặc copy vào draw.io.

---

## 1. Kiến trúc tổng quan

```mermaid
flowchart LR
    subgraph Client
        SV[👤 Sinh viên<br/>Browser]
        AD[👨‍💼 Admin<br/>Browser]
    end

    subgraph Frontend["Frontend — Next.js 14"]
        FE_S[Student pages<br/>/student/*]
        FE_A[Admin pages<br/>/admin/*]
        MW[middleware.ts<br/>token check]
        ZS[Zustand auth + i18n]
    end

    subgraph Backend["Backend — FastAPI async"]
        API[API v1 router<br/>/api/v1/*]
        DEP[Dependencies<br/>get_current_user<br/>require_admin]
        SVC[Services layer<br/>business logic]
        AI[AI modules<br/>prediction · chatbot]
        SCH[APScheduler<br/>daily 02:00]
    end

    subgraph Storage
        PG[(PostgreSQL 16<br/>+ pgvector)]
        RD[(Redis 7<br/>cache — optional)]
    end

    subgraph External
        GEM[Gemini 2.5 Flash<br/>+ embedding-001]
        SMTP[Gmail SMTP<br/>App Password]
    end

    SV --> FE_S
    AD --> FE_A
    FE_S --> MW
    FE_A --> MW
    MW --> API
    API --> DEP
    DEP --> SVC
    SVC --> AI
    SVC --> PG
    AI --> PG
    AI --> GEM
    SVC --> SMTP
    SCH --> SVC
    SVC --> RD

    style FE_S fill:#dbeafe,stroke:#0052a3
    style FE_A fill:#dbeafe,stroke:#0052a3
    style API fill:#e0e7ff,stroke:#003e80
    style SVC fill:#e0e7ff,stroke:#003e80
    style AI fill:#dcfce7,stroke:#16a34a
    style PG fill:#fef3c7,stroke:#d97706
    style GEM fill:#fce7f3,stroke:#be185d
```

**Ghi chú:**
- Frontend Next.js là **client-side rendered** với app router — token JWT lưu trong localStorage + cookie để middleware đọc được.
- Backend FastAPI **async toàn bộ** — SQLAlchemy 2 với asyncpg driver.
- pgvector extension chạy trong cùng PostgreSQL — không cần Pinecone/Weaviate riêng.
- Redis là **optional** — hệ thống chạy được khi không có Redis (config `REDIS_URL` empty).

---

## 2. Layered Architecture (rule cứng)

```mermaid
flowchart TD
    HTTP["app/api/v1/*<br/><br/>HTTP layer · route handlers · request/response wiring<br/>auth.py · students.py · admin.py · warnings.py · ..."]

    SVC["app/services/*<br/><br/>Business logic · pure async functions<br/>gpa_calculator · grade_aggregator · warning_engine ·<br/>notification · email_service · import_service · ..."]

    AI["app/ai/*<br/><br/>ML / RAG<br/>prediction/{features,model,explainer,train}<br/>chatbot/{rag,vectorstore,chains,providers,personal}"]

    M["app/models/*<br/><br/>SQLAlchemy ORM · 10 bảng<br/>User · Student · Course · Enrollment · Warning ·<br/>Prediction · Notification · Event · Document · ChatMessage"]

    SCH["app/core/{scheduler,security,config,deps}.py"]

    HTTP -->|depends on| SVC
    HTTP -->|depends on| M
    SVC -->|depends on| M
    AI -->|depends on| SVC
    AI -->|depends on| M
    SCH --> SVC
    SCH --> AI

    HTTP -.->|❌ KHÔNG được import| AI

    style HTTP fill:#dbeafe,stroke:#0052a3,color:#000
    style SVC fill:#e0e7ff,stroke:#003e80,color:#000
    style AI fill:#dcfce7,stroke:#16a34a,color:#000
    style M fill:#fef3c7,stroke:#d97706,color:#000
    style SCH fill:#fce7f3,stroke:#be185d,color:#000
```

### Rule cụ thể

> **AI / chatbot KHÔNG được import từ `app.api.v1.*`.** Đây là rule cứng để tránh circular import + giữ AI testable độc lập.

**Cụ thể:**
- ✅ `app/api/v1/predictions.py` import từ `app/ai/prediction/model.py`
- ❌ `app/ai/prediction/features.py` **không** import từ `app/api/v1/students.py`
- ✅ Logic dùng chung (vd "highest GPA wins" theo quy chế HCMUT) PHẢI nằm ở `app/services/grade_aggregator.py` — single source of truth
- ✅ AI/chatbot có thể `from app.services.grade_aggregator import effective_enrollments_per_course` thoải mái

### Hệ quả thiết kế

- Có thể test `app/ai/prediction/*` mà không cần khởi động FastAPI app — chỉ cần một AsyncSession.
- Đổi HTTP layer (vd thêm GraphQL) không phải sửa AI logic.
- Service layer là nơi đặt **invariants** của domain (quy chế HCMUT, validation, idempotency).

---

## 3. Request flow điển hình — SV nhập điểm môn

```mermaid
sequenceDiagram
    autonumber
    participant SV as Sinh viên (Browser)
    participant FE as Next.js FE
    participant MW as middleware.ts
    participant API as FastAPI /enrollments
    participant SVC as services/grade_aggregator
    participant WE as services/warning_engine
    participant N as services/notification
    participant EM as services/email_service
    participant DB as PostgreSQL
    participant SMTP as Gmail SMTP

    SV->>FE: Click "Lưu điểm"
    FE->>MW: PUT /api/v1/me/enrollments/{id}
    MW->>MW: Kiểm tra access_token cookie
    MW->>API: forward request với Bearer JWT
    API->>API: get_current_student dependency<br/>decode JWT → User → Student
    API->>DB: UPDATE enrollment SET ...
    API->>SVC: sync_student_stats(student, db)
    SVC->>SVC: effective_enrollments_per_course<br/>(highest GPA wins dedup)
    SVC->>DB: UPDATE students SET gpa_cumulative, credits_earned, warning_level
    API->>WE: evaluate_and_persist(student, semester)
    WE->>DB: SELECT existing Warning (idempotency check)
    alt cảnh báo mới
        WE->>DB: INSERT Warning
        WE->>N: create(type=warning, student, ...)
        N->>DB: INSERT Notification
        N-->>EM: fire_and_forget(template, context)<br/>không block response
        EM->>SMTP: SMTP send (try/except — fail-soft)
        EM->>DB: UPDATE notifications.email_sent_at
    end
    API-->>FE: 200 OK + updated enrollment
    FE-->>SV: Toast "Đã lưu"
```

**Điểm thiết kế quan trọng:**
1. **Bước 8** — `sync_student_stats` áp rule "highest GPA wins" trước khi đánh giá cảnh báo. Nếu không, SV đã học lại đạt môn F vẫn bị cảnh báo nhầm.
2. **Bước 11** — `evaluate_and_persist` **idempotent**: nếu đã có Warning cho cùng `(student, semester, level)` thì skip.
3. **Bước 14-15** — Email **fire-and-forget**: caller không đợi SMTP response. Nếu Gmail timeout, request vẫn trả 200 cho FE.
4. **Demo mode**: khi `SMTP_USER` rỗng, email_service log `[EMAIL DEV MODE]` thay vì gọi SMTP — vẫn lưu `email_sent_at` để hiển thị "đã gửi" trên UI.

---

## 4. Request flow — AI Prediction

```mermaid
sequenceDiagram
    autonumber
    participant SV as Sinh viên
    participant FE as Frontend
    participant API as /predictions/me
    participant PS as prediction_service<br/>(singleton)
    participant FE_X as features.py
    participant XGB as XGBoost model<br/>(loaded lifespan)
    participant CAL as Calibration layer
    participant EXP as RiskExplainer<br/>(SHAP)
    participant DB as PostgreSQL

    SV->>FE: Mở /predictions
    FE->>API: GET /predictions/me
    API->>DB: SELECT latest Prediction
    alt prediction còn fresh (cùng ngày)
        API-->>FE: trả prediction cached
    else
        API->>PS: predict(student)
        PS->>FE_X: build_features(student, db)
        FE_X->>DB: SELECT enrollments + courses
        FE_X->>FE_X: effective_enrollments_per_course<br/>(reuse từ services/grade_aggregator)
        FE_X-->>PS: 11-dim feature vector
        PS->>XGB: predict_proba(features)
        XGB-->>PS: raw_score (0..1)
        PS->>CAL: _early_warning_rules(student, raw_score)
        CAL->>CAL: gpa < 1.6 → floor 0.62<br/>gpa < 1.2 → floor 0.85
        CAL-->>PS: final_score = max(raw, floor)
        PS->>EXP: explain(features, final_score)
        EXP->>EXP: SHAP TreeExplainer<br/>top 5 factors VI<br/>normalize tổng = 100%
        EXP-->>PS: risk_factors[]
        PS->>DB: INSERT Prediction
        PS-->>API: PredictionResponse
        API-->>FE: 200 OK
    end
    FE->>FE: Render RadialBar gauge + factor bars
```

**Điểm thiết kế:**
- **Calibration layer** đặt floor lên raw score theo product expectation. Điều này khiến hệ thống KHÔNG phải pure XGBoost — báo cáo cần trình bày: **AI = ML + product calibration**.
- `prediction_service` là **singleton load lúc startup** (`lifespan` event của FastAPI), tránh re-load model 0.14MB cho mỗi request.

---

## 5. Request flow — RAG Chatbot (streaming)

```mermaid
sequenceDiagram
    autonumber
    participant SV as Sinh viên
    participant FE as Frontend
    participant API as /chatbot/ask/stream
    participant CH as chains.py
    participant VS as vectorstore.py
    participant EM as embedding-001
    participant PG as pgvector
    participant LLM as Gemini 2.5 Flash
    participant DB as PostgreSQL

    SV->>FE: Hỏi câu hỏi + click Send
    FE->>API: POST /chatbot/ask/stream (SSE)

    API->>CH: stream_chatbot_response(question, student)

    par Vector path
        CH->>EM: embed(question, task=retrieval_query)
        EM-->>CH: 768-dim vector
        CH->>VS: search by cosine_distance
        VS->>PG: SELECT ... ORDER BY embedding <=> :v LIMIT 5
        PG-->>VS: top-K vector hits<br/>match_type="vector"
    and Keyword path
        CH->>VS: keyword search
        VS->>PG: SELECT WHERE content ILIKE %term%<br/>+ scoring rules
        PG-->>VS: keyword hits<br/>match_type="keyword"
    end

    VS->>VS: _merge_hits<br/>dedup theo doc_id<br/>doc xuất hiện cả 2 → match_type="merged"
    VS-->>CH: top-K SearchHits

    CH->>CH: build_student_context(student, db)<br/>profile + GPA + warning + risk
    CH->>CH: build_prompt VI no-hallucination

    CH->>LLM: generate_content_async(stream=True)
    loop streaming chunks
        LLM-->>CH: chunk text
        CH-->>API: yield SSE event "data: {chunk}"
        API-->>FE: SSE chunk
        FE->>FE: append to UI realtime
    end

    LLM-->>CH: [DONE]
    CH->>DB: INSERT ChatMessage(role=assistant, citations)
    API-->>FE: SSE close
```

**Điểm thiết kế:**
- **Hybrid retrieval** chứ không pure vector — vì câu hỏi quy chế thường có số liệu cụ thể ("GPA 3.2 xếp loại gì") mà vector embed dễ bỏ sót.
- **Fallback nhiều tầng** ở `providers.py`: Gemini → Hugging Face → local LLM → extractive (no API key vẫn chạy).
- **Streaming thật** với Gemini `stream=True`, không phải fake chunking.
- **Student context inject** vào prompt — chatbot biết được SV này GPA bao nhiêu, đang ở mức cảnh báo nào → trả lời cá nhân hóa.

---

## 6. Background jobs — APScheduler

```mermaid
flowchart LR
    LF[FastAPI lifespan startup] --> SCH[setup_scheduler]
    SCH --> SCH_S[AsyncIOScheduler<br/>timezone=Asia/Ho_Chi_Minh]
    SCH_S --> J1[Job: predictions_batch_daily<br/>cron 02:00 hằng ngày]
    J1 --> PS[prediction_service.predict_batch]
    PS --> DB1[(predictions table)]

    style LF fill:#fef3c7
    style J1 fill:#dcfce7
```

**Tại sao APScheduler thay Celery?**

| Aspect | Celery | APScheduler |
|---|---|---|
| Process mới | worker + beat + broker (3) | in-process |
| Broker | Redis/RabbitMQ bắt buộc | không cần |
| Setup | ~50 dòng config | ~15 dòng |
| Debug | log scattered | log inline với app |
| Phù hợp | hệ thống production scale | demo + đồ án solo dev |

**Hạn chế hiện tại:** chỉ có 1 job (`predictions_batch_daily`). Job `warnings_batch_daily` **chưa có** — hiện trigger qua admin endpoint hoặc grade-update hook. Đây là điểm có thể bổ sung trong M8.

---

## 7. Frontend architecture

```mermaid
flowchart TD
    R[app/<br/>Next.js 14 App Router]
    R --> AU[auth/<br/>login · register]
    R --> ST[student/<br/>layout.tsx + 8 trang]
    R --> AD[admin/<br/>layout.tsx + 8 trang]
    R --> MW[middleware.ts<br/>token check]

    ST --> SS[StudentSidebar<br/>+ NotificationBell]
    AD --> AS[AdminSidebar<br/>+ role guard client-side]

    AU -.-> ST
    AU -.-> AD

    subgraph Lib["lib/"]
        AX[api.ts<br/>axios client + interceptors<br/>studentApi · adminApi · ...]
        AUTH[auth.ts<br/>Zustand persist<br/>user + token]
        I18N[i18n.ts<br/>Zustand persist<br/>VI / EN dict]
    end

    ST --> AX
    AD --> AX
    AX -->|Bearer JWT| BE[Backend FastAPI]
    AUTH --> AX
    I18N --> ST
    I18N --> AD

    style R fill:#dbeafe
    style ST fill:#e0e7ff
    style AD fill:#fce7f3
    style Lib fill:#fef3c7
```

**Điểm thiết kế:**
- 2 layout độc lập (`student/layout.tsx` + `admin/layout.tsx`) — mỗi layout có sidebar riêng + role guard riêng.
- `middleware.ts` chỉ check token tồn tại, không decode role (Edge runtime hạn chế lib). Role guard nằm ở admin layout client-side với redirect.
- `lib/api.ts` chia thành nhiều `*Api` object: `authApi`, `studentApi`, `predictionsApi`, `chatbotApi`, `documentsApi`, `warningsApi`, `notificationsApi`, `studyPlanApi`, `eventsApi`, `adminApi`, `adminEventsApi`.
- `i18n.ts` dùng Zustand persist localStorage → giữ ngôn ngữ cross-session. Cả VI lẫn EN dict đều có cùng keys (compile-time check qua `keyof typeof dict.vi`).

---

## 8. Deployment topology (development)

```mermaid
flowchart LR
    DEV[Developer<br/>laptop] -->|docker compose up| DC[docker-compose.yml]
    DC --> SVC1[backend container<br/>uvicorn :8000]
    DC --> SVC2[db container<br/>postgres:16 + pgvector<br/>:5432]
    DC --> SVC3[redis container<br/>redis:7 :6379]
    DC --> SVC4[pgadmin container<br/>:5050]

    DEV -->|npm run dev| FE[Frontend Turbopack<br/>:3000]
    FE -->|/api/v1| SVC1
    SVC1 --> SVC2
    SVC1 --> SVC3
```

**Production (chưa làm)** — gợi ý cho M9 hoặc sau đồ án:
- Backend: AWS ECS Fargate hoặc Railway / Render
- Database: AWS RDS PostgreSQL với pgvector enabled (region ap-southeast-1)
- Frontend: Vercel hoặc Cloudflare Pages
- Email: AWS SES thay Gmail SMTP để gửi volume lớn

---

## 9. AI Pipeline — Training (offline)

```mermaid
flowchart LR
    SD[scripts/seed_synthetic.py] --> S1[1000 SV synthetic<br/>4 GPA tiers + retake_success_rate]
    S1 --> S2[65k enrollments<br/>noisy labels v2<br/>+ admin discretion + risk_boost]
    S2 --> FE_BUILD[features.py<br/>build_dataset]
    FE_BUILD --> X[X: 11 features per row]
    FE_BUILD --> Y[y: warning_level >= 1<br/>(16% positive)]
    X --> SPLIT[train_test_split<br/>stratified]
    Y --> SPLIT
    SPLIT --> TR[Optuna 25 trials<br/>5-fold CV<br/>monotonic constraints]
    TR --> TUNE[Threshold tuning<br/>on val set<br/>F1 maximize]
    TUNE --> SAVE[joblib.dump<br/>data/models/v1.joblib]
    SAVE --> METRICS[metrics_v1.json<br/>F1=0.79, AUC=0.98]

    style SD fill:#fef3c7
    style TR fill:#dcfce7
    style SAVE fill:#dbeafe
```

**Lệnh train:**
```bash
docker compose exec backend python -m app.ai.prediction.train
```

**Output:**
- `backend/data/models/v1.joblib` — XGBoost model + feature encoder + threshold (0.14 MB)
- `backend/data/models/metrics_v1.json` — F1, AUC, recall, precision, confusion matrix, threshold

---

## 10. Tài liệu tham khảo nội bộ

- [`CLAUDE.md`](../CLAUDE.md) — Master spec + milestone tracker (source of truth)
- [`ROADMAP.md`](../ROADMAP.md) — Step-by-step plan từng milestone (M1→M9)
- [`docs/SLIDES.md`](./SLIDES.md) — Marp slide deck cho báo cáo
- [`docs/DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md) — ER diagram + per-table docs
