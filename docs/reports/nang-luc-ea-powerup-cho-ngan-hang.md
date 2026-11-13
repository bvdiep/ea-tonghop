# Danh mục Năng lực EA & PowerUp — Góc nhìn Nhu cầu Ngân hàng

> **Ngày:** 12/10/2026
> **Loại:** Tài liệu nội bộ (bổ trợ cho proposal khách hàng) — liệt kê năng lực thật của 2 nền tảng, đánh dấu rõ giá trị với bank và khoảng trống cần xây
> **Nguồn:** docs/FEATURES.md v1.13, docs/architecture/overview.md v2.3 (EA); khảo sát code power-up-dev 12/10/2026 (PU); các con số dòng file đã verify trực tiếp
> **Ký hiệu trạng thái:** ✅ đang chạy thật · 🟡 chạy một phần/có ghi chú · 📋 đã thiết kế, chưa code
> **Nhu cầu bank tham chiếu:** N1 = chatbot nội bộ (truy vấn đa nguồn, suy luận, tính toán) · N2 = chatbot khách hàng (hỏi đáp–bán hàng) · N3 = AI kiểm soát quy trình (không chạm giao dịch)

---

## 1. EA — Enterprise Assistant

Next.js monolith + Hermes agent runtime + MCP gateway in-app · ~96.500 dòng TypeScript (src) · 13 module MCP / 43 tool đang vận hành · MySQL 8 + Redis 7 · on-premise (Docker MySQL/Redis + PM2, có sổ tay deploy đa server).

### 1.1 Trải nghiệm trò chuyện & agent runtime

| Năng lực | Trạng thái | Giá trị với bank |
|---|---|---|
| Chat streaming, đa luồng hội thoại, resume, gắn file (dán/kéo-thả), nhập giọng nói | ✅ | Nền chat nội bộ đạt chuẩn thương mại, không cần xây lại |
| Agent tự nhận diện ý định, tự chọn công cụ (không cây menu cứng) | ✅ | N1: câu hỏi phức tạp đa nguồn không cần định nghĩa trước luồng |
| Chip thu hẹp phạm vi tool từng câu hỏi (user tự giới hạn AI, chỉ thu hẹp) | ✅ | Cán bộ tự kiểm soát phạm vi AI từng câu — điểm cộng tuân thủ |
| Icon hiển thị luồng xử lý (câu hỏi đi luồng nào), thẻ tham chiếu nguồn | ✅ | Minh bạch với người dùng — yêu cầu sẵn của môi trường bank |
| Biểu đồ dữ liệu inline trong chat | 🟡 #504 | N1: trả lời kèm biểu đồ — cần hoàn thiện rule cấu hình |
| Phục hồi câu trả lời khi gián đoạn (reconnect, gửi lại, gia hạn) | ✅ | Ổn định vận hành thật |

### 1.2 Kho tri thức & dữ liệu

| Năng lực | Trạng thái | Giá trị với bank |
|---|---|---|
| **Admin tự CRUD kho tri thức RAG** ngay trong web (thêm/sửa/xóa tài liệu, chống trùng, retry) | ✅ #875 | N2/N1: phòng ban tự quản tài liệu, không cần IT thao tác hệ RAG |
| Pipeline nạp tài liệu bất đồng bộ: PDF/DOCX/PPTX/XLSX/**ảnh scan** trích xuất tự động qua OCR-headless | ✅ #875 | N2: văn bản giấy scan của bank nạp được vào kho tri thức |
| Provider RAG hoán đổi được (LightRAG / AnythingLLM) qua cấu hình | ✅ | Không khóa vendor ở tầng tri thức |
| Truy vấn Google Sheets/Dataset bằng tiếng Việt tự nhiên (SQL tổng hợp trong DuckDB in-memory, SELECT-only, cap 1.000 dòng, allow-list dataset) | ✅ | N1: mẫu chuẩn cho "hỏi dữ liệu có kiểm soát" — không SQL tự do, giới hạn cứng |
| Leadership Workspace: không gian phân tích theo đơn vị, câu hỏi gợi ý, artifact biểu đồ, lưu hội thoại, khôi phục gián đoạn | ✅ khung / 🟡 8.2 đang chạy dữ liệu mẫu | N1 cho lãnh đạo: khung có sẵn — cần nạp dữ liệu thật theo đơn vị |
| Truy vấn dữ liệu leadership qua DuckDB đồng bộ từ REST hoặc Postgres-direct | ✅ #482 | Tiền lệ kỹ thuật kết nối nguồn dữ liệu ngoài cho N1 |
| Memory dài hạn theo user (Honcho self-host: ngữ cảnh, tra cứu, lưu, kết luận) + admin backfill | ✅ #1198 | Trợ lý "nhớ" ngữ cảnh làm việc từng cán bộ |

### 1.3 Làm việc thay người (Action Skills)

| Năng lực | Trạng thái | Giá trị với bank |
|---|---|---|
| Công việc & dự án: tạo/sửa/liệt kê task, task theo dự án, bình luận | ✅ | Quản lý công việc nội bộ ngay trong trợ lý |
| Văn bản & mẫu: lưu/tra cứu văn bản, điền theo mẫu tài liệu | ✅ | Soạn nháp công văn/hợp đồng theo mẫu chuẩn bank |
| Chấm công & nghỉ phép: tạo đơn, duyệt/từ chối (bắt buộc vai trò MANAGER+ ở lớp thực thi) | ✅ | Quy trình nội bộ có phê duyệt — chứng minh human-in-the-loop |
| Biên bản họp: ghi âm → STT → sinh biên bản; transcript trực tiếp; nhập transcript từ file/link có tách người nói | ✅ | Đắt giá cho họp giao ban/thẩm định — tiết kiệm thời gian ghi chép |
| Quản lý file cá nhân theo user (hạn mức, tổng quan dung lượng admin) | ✅ | Làm việc với chứng từ/tài liệu cá nhân |
| Thông báo trung tâm + đẩy Telegram cá nhân (token mã hóa AES-256-GCM, bật/tắt từng người) | ✅ | Kênh thông báo cá nhân — tiền lệ kênh ngoài cho bank |
| Trợ lý y khoa (module dọc ngành y: voice command, phiếu khám) | ✅ | Chứng minh khả năng làm **module dọc theo ngành** — mẫu cho module dọc bank (tín dụng, SWIFT) |

### 1.4 Quản trị & governance (điểm mạnh nhất)

| Năng lực | Trạng thái | Giá trị với bank |
|---|---|---|
| **Fail-closed tool gateway**: mặc định AI không được dùng nhóm công cụ nào; super admin bật từng nhóm; tool bị tắt trả lời y như "không tồn tại" (không lộ); chặn cả ở lớp thực thi | ✅ #171 | Yêu cầu số 1 của bank về kiểm soát AI — đã enforce thật, không phải khẩu hiệu |
| Module on/off theo đơn vị (3 tính năng lõi khóa, còn lại toggle per-row, chat bị chặn nhắc tới module đã tắt) | ✅ | Đóng gói tính năng theo phạm vi thỏa thuận với bank |
| **Tier theo nhóm nhân sự**: gói năng lực theo user (module addon + cấu hình model riêng + workspace memory riêng), enforce ở tools/call | ✅ #1051–#1122 | Phân quyền theo chức danh: giao dịch viên / trưởng phòng / lãnh đạo |
| Vai trò 4 cấp (Staff/Manager/Admin/Super Admin), duyệt đơn gate theo role lấy từ DB | ✅ | RBAC cho vận hành |
| Quy tắc hành vi AI (tone, ngôn ngữ, chỉ dẫn) cấu hình trên web | ✅ #7.4 | N2: guardrail giọng điệu/thương hiệu quản được không cần sửa code |
| Prompt injects (chỉ dẫn phòng vệ chèn vào system prompt, bật/tắt từng cái, mặc định tắt) | ✅ #7.14 | Lớp phòng thủ defense-in-depth |
| Audit log (truy vấn + thao tác), xem trên web | ✅ #7.8 | Bắt buộc cho compliance bank — có sẵn |
| Phân tích sử dụng (user hoạt động, tin nhắn/ngày, truy vấn phổ biến) | ✅ #7.7 | Đo hiệu quả đầu tư AI |
| Branding: 8 theme, logo + tên hệ thống theo khách, khóa theme theo tổ chức | ✅ #7.12 | Bank tự thương hiệu hóa |
| Quản trị user (tạo/xóa/reset, hạn mức file), xem log hệ thống từng service trên web | ✅ | Vận hành không cần SSH |
| Bật/tắt module MCP + key riêng cho endpoint domain hẹp (`/api/mcp-coding` pattern: registry ∩ enabled groups, view chỉ thu hẹp) | ✅ #902 | **Mẫu kiến trúc trực tiếp cho N3**: mỗi quy trình bank một endpoint + key riêng, tool hẹp, fail-closed |
| Webhook inbound có secret per-bot (Telegram bridge) | ✅ #1371 | Mẫu nhận event từ hệ thống ngoài (tiền đề N3) |

### 1.5 Nền tảng & vận hành

| Năng lực | Trạng thái | Giá trị với bank |
|---|---|---|
| On-premise: 1 triển khai = 1 khách hàng, 1 DB riêng; Docker + PM2; sổ tay deploy/backup/migration đa server | ✅ | Đúng mô hình bank yêu cầu |
| Model gateway qua Hermes + LiteLLM: nhiều provider, đổi model không sửa app; model/tier riêng từng nhóm | ✅ | Không khóa vendor; chuyển model trong nước/self-host được |
| Langfuse tracing mọi luồng (chat/classifier/transcription/MCP) — bật/tắt theo env | ✅ #424–#447 | Truy vết sự cố AI — yêu cầu sẵn của audit bank |
| Realtime: Socket.io + Redis pub/sub cross-process | ✅ #183 | Thông báo/khôi phục tức thời |
| Mobile: chiến lược Capacitor đã thiết kế | 📋 | Kênh di động khi cần |
| Web + Socket + 2 worker (transcription, notification) + knowledge extraction worker | ✅ | Kiến trúc worker tách — scale được từng phần |

### 1.6 Đã thiết kế sẵn cho bài toán "AI chạm hệ thống lõi" (bối cảnh y tế, chuyển bối cảnh được sang bank) 📋→ đủ chi tiết để triển khai

| Năng lực | Trạng thái | Giá trị với bank |
|---|---|---|
| Cổng phân luồng truy vấn: realtime (hệ lõi) vs tổng hợp (kho dữ liệu) — AI tự chọn, user không chọn | 📋 thiết kế chi tiết | N3/N1: ánh xạ thẳng sang core banking vs DWH |
| Ghi ngược có cổng kiểm soát: thỏa thuận văn bản + xác nhận người thật + idempotency + kill-switch ≤10s + audit (người xác nhận, hash, mã hệ lõi) | 📋 thiết kế chi tiết | **N3: bộ 5 điều kiện sẵn sàng** — khung tuân thủ đã nghĩ kỹ |
| Định danh ký token: phương án A (JWT ngắn hạn tự ký — code sẵn chưa wire) → B (IAM/Keycloak token exchange) | 📋 A code sẵn / B thiết kế | Bước bắt buộc trước khi mở dữ liệu nhạy cảm bank |

### 1.7 Khoảng trống EA so với nhu cầu bank

1. Không có public API/OpenAI-compatible cho hệ thống ngoài gọi chat (`/api/chat` chỉ nhận session nội bộ) — N2 cần xây kênh public gateway.
2. Không có multi-tenant khách-cuối (mô hình 1 khách = 1 instance) — chấp nhận được cho bank (1 triển khai/bank), nhưng kênh khách hàng cần tách phiên + identity riêng.
3. Chưa có metadata hiệu lực văn bản theo thời gian — cần xây (nhỏ, quan trọng nhất cho N2).
4. Trust model: userId do model sinh — phải chốt phương án ký token trước khi mở dữ liệu nhạy cảm.
5. Leadership workspace còn chạy dữ liệu mẫu — cần nạp dữ liệu thật.

---

## 2. PowerUp

Workspace 7 app · ~78.400 dòng TS + ~60.400 dòng Python + ~13.800 dòng Dart · PostgreSQL + Qdrant + Celery + LiteLLM + Langfuse · multi-tenant SaaS theo domain · khách thật (VDI, 8 use case).

### 2.1 Quản trị dữ liệu (data governance)

| Năng lực | Trạng thái | Giá trị với bank |
|---|---|---|
| **50 Prisma models** — schema nghiệp vụ đầy đủ: Folder/FolderPermission (ACL tới từng thư mục, gắn vai trò), DataTable + DataColumn + relationship + permission, DocumentType, Category | ✅ | N1: nền quản trị dữ liệu có phân quyền chi tiết — thứ EA thiếu |
| ExternalDatabase: đăng ký kết nối CSDL ngoài (mỗi tenant tự khai báo nguồn) | ✅ | N1: kết nối nguồn dữ liệu bank/DWH có danh mục kiểm soát |
| Multi-tenant theo domain: AppDomain + DomainConfig + AdminDomain (24 tham chiếu), mỗi domain cấu hình riêng (branding, prompt, category) | ✅ | Kinh nghiệm cách ly theo đơn vị — hữu ích nếu bank muốn tách theo khối/công ty con |
| PersonalAccessToken: tokenHash, scope, expire/revoke, 1 user 1 PAT; API **OpenAI-compatible** cho bên ngoài | ✅ | **N2: tiền lệ kênh public chuẩn ngành** (endpoint /v1/chat/completions) |
| Audit Activity qua interceptor toàn cục (ai làm gì trên resource nào) | ✅ | Audit nền sẵn |
| RBAC + permission module riêng (Role/Permission/AdminDomain) | ✅ | Phân quyền chi tiết |

### 2.2 Pipeline tri thức (sâu hơn EA)

| Năng lực | Trạng thái | Giá trị với bank |
|---|---|---|
| **Ingestion pipeline ~25.300 dòng Python** riêng: OCR service, content extraction, **header parsing** (nhận diện cấu trúc bảng biểu tài liệu), metadata extraction + suggestion, file categorization | ✅ | N2: văn bản bank dạng bảng/biểu (biểu phí, điều kiện) — header parsing là lợi thế thật |
| Chunking (nhiều chiến lược) + embedding service | ✅ | Nền RAG chất lượng |
| **Qdrant hybrid search (weighted)** + **RerankerService** (lọc chunk theo relevance) | ✅ (reranker verify trong code) | Độ chính xác truy xuất cao hơn search thuần — giảm trả lời sai nguồn |
| Qdrant multi-collection theo domain, ACL resolve server-side (accessible_file_ids chỉ thu hẹp) | ✅ | Truy xuất có phân quyền ngay trong vector store |

### 2.3 Agent layer & truy vấn dữ liệu

| Năng lực | Trạng thái | Giá trị với bank |
|---|---|---|
| Datahub agent v4 (search chunks / grep / list / SQL), 901 dòng | ✅ | N1: truy vấn tài liệu + dữ liệu kết hợp |
| **Text-to-SQL** (service riêng + Postgres agent + project data agent) | ✅ | N1: hỏi số liệu CSDL bằng tiếng Việt — cần đóng khung SELECT-only + cap khi vào bank |
| Google Sheet data agent (1.938 dòng), Zoho agent | ✅ | Kinh nghiệm connector SaaS — chuyển sang connector bank |
| ⚠️ Orchestrator `central_chat_agent.py` 1.367 dòng + intent classifier keyword cứng (239 dòng) + 11 thư mục sub-agent copy tay (20.790 LOC) + prompt 2 nguồn sự thật | ✅ (đã verify) | **Nợ kỹ thuật — KHÔNG di trú sang bank**; thay bằng agent runtime chuẩn (Hermes+MCP) theo quyết định PU-v2 |
| powerup-mcp: 6 tool datahub chuẩn MCP, verify PAT qua internal API, ACL server-side | ✅ round 5 | Cầu chuẩn mở đã chạy thật — mẫu cho kiến trúc hợp nhất |

### 2.4 Engine nghiệp vụ tài chính (bằng chứng khác biệt)

| Năng lực | Trạng thái | Giá trị với bank |
|---|---|---|
| **bank_transaction_matcher.py — 788 dòng**: so khớp giao dịch ngân hàng | ✅ (verify trực tiếp) | **N3: đội đã làm bài toán đối soát giao dịch thật** — không chỉ chat |
| reconciliation_service, compare_service (so sánh 2 kỳ/2 nguồn), statement (ngân khoản), workflow table_generator, execution | ✅ 30 module NestJS | N3/N1: engine tính toán tách LLM — kết quả kiểm chứng được |
| 8 use case VDI khách thật | ✅ | Bằng chứng sản phẩm chạy doanh nghiệp thật |
| n8n webhook integration (workflow) | ✅ | Kinh nghiệm tích hợp workflow engine — tham chiếu cho N3 |

### 2.5 Bề mặt sản phẩm

| Năng lực | Trạng thái | Giá trị với bank |
|---|---|---|
| User web: hội thoại, tìm kiếm tài liệu (document-search), làm việc với bảng dữ liệu (database), hub tổng hợp | ✅ | UX tra cứu dữ liệu/triết khai cho N1 |
| Admin web: 17+ khu quản trị (users, roles, permissions, folder-access, data-hub, data-table, domain-config, external-databases, document-type, prompts, workflows, logs…) | ✅ | Bảng điều khiển quản trị dữ liệu — bề mặt hấp thụ vào nền tảng hợp nhất |
| Mobile Flutter (BLoC): chat, tài liệu, hồ sơ | ✅ | Kênh di động có sẵn |

### 2.6 Khoảng trống PU so với nhu cầu bank

1. Agent layer là nợ kỹ thuật (mục 2.3) — quyết định PU-v2 đã chỉ ra hướng thay, không di trú.
2. Cloud-first/SaaS hiện trạng: model qua API cloud (RunPod…), Qdrant từng phơi Internet (đã ghi nhận trong khảo sát) — vào bank phải on-prem hóa + siết hạ tầng (bind loopback/whitelist/ufw).
3. Không có lớp module on/off theo đơn vị kiểu EA, không có tier theo chức danh — hấp thụ từ EA.
4. Audit còn ở mức Activity log — cần chuẩn audit bank (hash, trace toàn luồng) — hấp thụ từ EA (Langfuse + audit_log).

---

## 3. Ma trận năng lực ↔ nhu cầu bank

| Nhu cầu | Năng lực có sẵn (nền tảng) | Hấp thụ từ nền tảng kia | Phải xây mới |
|---|---|---|---|
| **N1 nội bộ** | EA: agent runtime, fail-closed gateway, tier, gsheet/DuckDB có kiểm soát, leadership workspace (khung), memory, Langfuse | PU: Folder/DataTable/ExternalDatabase + ACL, Qdrant hybrid + reranker, text-to-SQL, engine tài chính | Connector nguồn dữ liệu bank (read-only, đăng ký tường minh); đóng khung text-to-SQL; nạp dữ liệu thật vào leadership |
| **N2 khách hàng** | EA: RAG admin CRUD + OCR ingestion, behavior rules (tone), prompt injects, module toggle, notification, branding | PU: PAT API OpenAI-compatible (kênh public đã chứng minh), header parsing cho tài liệu dạng bảng, multi-tenant config | Public gateway + phiên khách nặc danh; **metadata hiệu lực văn bản + filter tại retrieve + trích dẫn bắt buộc**; guardrail chuyên dụng (OTP/lừa đảo); handoff CSKH/CRM |
| **N3 kiểm soát quy trình** | EA: endpoint MCP hẹp theo domain + key riêng, webhook inbound secret, kill-switch fail-closed, audit + Langfuse, thiết kế ghi ngược 5 điều kiện | PU: bank_transaction_matcher, reconciliation/compare engine, n8n workflow integration | Rule engine AML/SWIFT/tín dụng theo quy định bank; pipeline headless check; shadow mode + dashboard compliance; giao tiếp core banking (phụ thuộc bank mở API) |

---

## 4. Đọc nhanh: 10 năng lực "bán được" ngay với bank

1. Fail-closed tool gateway — AI mặc định không làm gì, chặn cả ở lớp thực thi, tool bị tắt trả lời như không tồn tại.
2. Tier theo chức danh — cùng hệ, mỗi cấp thấy đúng công cụ + dữ liệu + model của mình.
3. Audit log + Langfuse tracing — truy vết từng câu trả lời, từng hành động AI.
4. RAG có admin tự quản + OCR file scan — phòng ban tự nạp tài liệu, không phụ thuộc IT.
5. Hỏi dữ liệu có kiểm soát — SQL đóng khung, cap dòng, allow-list dataset, gắn thời điểm dữ liệu.
6. Engine đối soát giao dịch đã chạy thật (788 dòng bank_transaction_matcher + reconciliation).
7. Endpoint MCP hẹp theo domain với key riêng — mẫu kiến trúc cho AI kiểm soát quy trình.
8. Kill-switch + phương án thủ công dự phòng — tắt AI là quy trình chạy như cũ.
9. Model gateway đa provider — không khóa vendor, chuyển model trong nước/self-host được.
10. On-premise hoàn toàn, 1 bank = 1 triển khai, có sổ tay vận hành đa môi trường.

---

## 5. Phụ lục — tham chiếu trạng thái

- EA: `docs/FEATURES.md` v1.13 (nguồn trạng thái ✅/🟡/📋), `docs/architecture/overview.md` v2.3, `docs/design/super-admin-mcp-gateway-config.md`, `docs/design/mcp-tier-based-tool-provisioning.md` (Implemented rev 2), `docs/design/mcp-coding-endpoint-design.md` (v2 shipped), `docs/datalake/2026-10-05-ea-nen-tang-va-diem-tich-hop-datalake.md` (pattern tích hợp hệ lõi), `docs/architecture/improvements-v2.md` (nợ đã biết).
- PU: khảo sát code 12/10/2026 (7 app, LOC per-app, 50 Prisma models, 30 NestJS modules, 11 thư mục agent, verify central_chat_agent 1.367 dòng / intent_classifier 239 dòng / bank_transaction_matcher 788 dòng), `docs/pu-v2-on-ea-architecture.md` (quyết định PU-v2 D1–D4), khảo sát hạ tầng 08/09/2026 (Qdrant phơi Internet, ufw inactive — đã ghi nhận).
