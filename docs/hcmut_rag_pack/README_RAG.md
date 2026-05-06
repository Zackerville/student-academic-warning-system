# HCMUT RAG Source Pack

Gói này gom các tài liệu chính thức phục vụ xây dựng RAG cho trợ lý sinh viên Trường Đại học Bách khoa - ĐHQG-HCM.

## Có gì trong gói

- `pdfs/`: các PDF tải trực tiếp được từ domain chính thức `hcmut.edu.vn/document`.
- `links/`: các link MyBK/HCMUT quan trọng dạng `.url` và một file Markdown tổng hợp link.
- `manifest/sources_manifest.csv`: bảng nguồn để import vào pipeline crawler/ingestion.
- `manifest/sources_manifest.json`: bản JSON của manifest.
- `scripts/download_html_sources.py`: script tải các nguồn HTML/link-only về máy bạn nếu muốn crawl nội dung đầy đủ.

## Cách dùng nhanh cho RAG

1. Ingest trực tiếp toàn bộ PDF trong `pdfs/`.
2. Với các file `.url` trong `links/`, dùng crawler riêng để tải HTML chính thức rồi convert sang Markdown/text.
3. Gắn metadata theo các cột trong `sources_manifest.csv`: `folder`, `title`, `source_url`, `rag_topic`.
4. Ưu tiên trả lời theo thứ tự: thông báo/quy định mới nhất > kết luận hội đồng học vụ > quy định học vụ hợp nhất > FAQ MyBK > trang khoa/đơn vị.

## Lưu ý quan trọng

Tài liệu học vụ có thể đổi theo học kỳ. Khi chạy production, nên crawl lại định kỳ các trang `hcmut.edu.vn/dao-tao/quy-che-quy-dinh`, `hcmut.edu.vn/dao-tao/lich-hoc-vu`, `mybk.hcmut.edu.vn/bksi/public/vi/blog/...`.

Mình đã tải được các PDF public chính thức. Một số trang MyBK là HTML động nên được đưa vào dạng link + downloader script thay vì giả lập PDF.
