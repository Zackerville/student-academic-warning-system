-- Kích hoạt các PostgreSQL extensions cần thiết
-- Script này chạy tự động khi database được khởi tạo lần đầu

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;