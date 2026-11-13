# Đề xuất giải pháp & lộ trình triển khai AI cho Ngân hàng

> **Ngày:** 12/10/2026
> **Trạng thái:** Draft đề xuất — dựa trên khảo sát code thật của 2 nền tảng (EA, PowerUp), chưa chốt với khách
> **Bằng chứng nền:** Báo cáo khảo sát EA (repo `hermes-web`, commit fd15bba1 2026-10-11) và PowerUp (workspace `power-up-dev`) kèm tài liệu `pu-v2-on-ea-architecture.md` (07/09/2026) và `docs/datalake/` của EA (pattern tích hợp hệ thống lõi đã thiết kế cho bệnh viện)

---

## 1. Nhu cầu khách hàng (bank) — 3 bài toán

| # | Nhu cầu | Bản chất kỹ thuật | Độ phức tạp |
|---|---|---|---|
| N1 | **Chatbot nội bộ**: truy vấn, trả lời độ phức tạp cao từ nhiều nguồn, suy luận, tính toán | Agent đa tool + RAG sâu + truy vấn dữ liệu có kiểm soát (text-to-SQL/DuckDB) + tính toán | Cao nhất về dữ liệu |
| N2 | **Chatbot AI cho khách hàng**: hỏi đáp + bán hàng | RAG chính sách có hiệu lực theo thời gian + guardrail tone + kênh public + handoff CSKH | Cao về governance, hẹp về dữ liệu |
| N3 | **AI nhúng quy trình có sẵn** (chuyển tiền quốc tế, tín dụng…): kiểm soát, cảnh báo — **không chạm giao dịch tiền** | Headless check pipeline + rule-based trước, ML sau + audit + kill-switch | Cao về tuân thủ, vừa về kỹ thuật |

Định hướng của chủ dự án (đã ghi nhận): N1 phức tạp tiệm cận PowerUp; N2 phức tạp như bài toán tra cứu luật có hiệu lực theo thời gian; N3 ưu tiên thấp, AI không chạm tiền.

---

## 2. Hai nền tảng sẵn có — kết quả khảo sát (bằng chứng từ code)

### 2.1 EA (Enterprise Assistant — `enterprise-assistant-dev` / hermes-web)

**Kiến trúc đã chạy thật (as-built, docs/architecture/overview.md v2.3):**

- Next.js monolith (App Router) + **Hermes Agent** làm AI runtime (blackbox, model/skills cấu hình ngoài repo) + **MCP gateway in-app** (`/api/mcp`, JSON-RPC) — **13 module / 43 tool** đang vận hành (task, project, document, template, attendance, meeting_minutes, transcription, knowledge, gsheet, leadership, powerup, search, memory).
- **Governance nhiều lớp, fail-closed**: module-exposure gate (super admin bật/tắt từng nhóm tool, thiếu config = không expose gì), per-user tool scope (chỉ thu hẹp), tier addon theo cấp bậc nhân viên (đã enforce thật ở `tools/call`), RBAC 4 vai trò (Staff/Manager/Admin/Super Admin).
- **RAG**: LightRAG/AnythingLLM (provider abstraction), Admin tự CRUD kho tri thức ngay trong hệ thống (#875), pipeline ingestion bất đồng bộ cho PDF/DOCX/PPTX/XLSX/ảnh scan qua BullMQ worker gọi Hermes `/v1/runs` (OCR-headless).
- **Memory dài hạn per-user** (Honcho self-host), **observability** Langfuse tracing mọi luồng, DuckDB cho analytics (leadership + Google Sheets SELECT-only in-memory).
- **Model routing**: qua Hermes + LiteLLM proxy (đã vận hành nhiều host), hỗ trợ nhiều provider.
- **Data layer**: MySQL 8 + Redis 7 (BullMQ, Socket.io pub/sub), 58 model Prisma (runtime dùng raw mysql2).
- **Quy mô**: ~96.500 dòng TypeScript trong `src/` (857 file TS), 105 migration.

**Pattern tích hợp hệ thống lõi doanh nghiệp — đã THIẾT KẾ chi tiết (docs/datalake/, bối cảnh bệnh viện):**

- Cổng truy cập phân loại: `realtime` (hệ lõi, tức thời) vs `warehouse/datalake_query` (tổng hợp, lịch sử) — AI tự chọn theo mô tả tool, user không chọn.
- Nguyên tắc "chỉ đọc trước, ghi ngược chỉ mở theo thoả thuận + cổng kiểm soát": ghi ngược (`his_write`) có 5 điều kiện bắt buộc — thoả thuận văn bản, xác nhận của người thật trước khi ghi, idempotency key, kill-switch (tắt trong ≤10s gồm cả tier addon), audit đầy đủ (người xác nhận, thời điểm, hash nội dung, mã trả về).
- Endpoint MCP hẹp theo domain (`/api/mcp-coding` pattern — v2 shipped): 1 domain = 1 endpoint + 1 key riêng, tool registry ∩ enabled_groups, view chỉ thu hẹp không mở rộng — **đây chính là pattern cho N3**.
- Identity/token: phương án A (EA ký JWT ngắn hạn, code sẵn `mcp-jwt.ts` chưa wire) → B (Keycloak token exchange, đích đề xuất); đang đo #1326.
- Webhook inbound đã có tiền lệ thật (Telegram group bridge — per-bot secret, không session auth).

**Giới hạn đã biết (tự nhận trong docs):** không có public/OpenAI-compatible API cho hệ thống ngoài gọi chat (`/api/chat` chỉ nhận cookie nội bộ); không có multi-tenant khách-cuối (1 triển khai = 1 khách, 1 DB riêng); schema chẻ đôi (Prisma migration-only vs raw SQL); RBAC inline phân tán; userId do model sinh là điểm yếu trust model (đang đo, có kế hoạch khắc phục).

### 2.2 PowerUp (`power-up-dev` — 7 app con)

**Quy mô:** ~78.400 dòng TypeScript + ~60.400 dòng Python + ~13.800 dòng Dart (mobile). Tổng ~135k dòng code thật.

| App | Vai trò | Stack |
|---|---|---|
| power-up-api | Backend nghiệp vụ + data governance | NestJS + Prisma + PostgreSQL + Redis/Bull + Bun, port 3000, **30 feature modules**, **50 Prisma models** |
| power-up-ai | AI runtime | FastAPI + Qdrant + LiteLLM + Langfuse + Celery, port 5008 |
| power-up-ai-ingestion | Pipeline nạp tài liệu | Python, ~25.300 dòng (OCR, chunking) |
| powerup-mcp | MCP server (stdio) cho datahub | Python — verify PAT qua API `/internal/*`, resolve ACL server-side, truy Qdrant trực tiếp |
| power-up-user-web / admin-web / mobile | Bề mặt sản phẩm | Next.js 15 / React + Vite admin / Flutter BLoC |

**Giá trị cốt lõi (giữ lại cho PU-v2):**

- **Data governance sâu**: Folder + FolderPermission (ACL tới từng folder), DataTable + permission + relationship, ExternalDatabase (kết nối DB ngoài), DocumentType, DomainConfig/AppDomain (multi-tenant theo domain, 24 tham chiếu), PersonalAccessToken (tokenHash, scope, revoke), Activity audit.
- **RAG sâu hơn EA**: Qdrant hybrid search (weighted) + reranker + OCR (GPU offload) + header detection — pipeline ingestion ~25k dòng Python riêng.
- **Engine nghiệp vụ tài chính đã chứng minh với khách thật**: `bank_transaction_matcher.py` (788 dòng — đã verify), reconciliation_service, compare_service, statement, workflow table_generator; 8 use case VDI đang chạy.
- **API OpenAI-compatible** cho bên ngoài (PAT per-user) — kênh tích hợp đã chứng minh.
- Multi-tenant SaaS theo domain (AppDomain 77) — ngược với EA nhưng đúng nhu cầu "một bank nhiều đơn vị".

**Nợ kỹ thuật (đã verify):** `central_chat_agent.py` đúng **1.367 dòng** (orchestrator trộn tool+routing+streaming+timeout+tracing+cost+quyền), `intent_classifier.py` 239 dòng keyword cứng tiếng Việt, 11 thư mục sub-agent copy tay (tổng 20.790 LOC agent layer), prompt 2 nguồn sự thật (cứng trong Python + bảng Prompt DB sync tay), phân quyền trùng lặp NestJS RBAC ↔ tool Python. → Thêm 1 nguồn dữ liệu = copy thư mục agent + sửa 3+ file intent + redeploy.

### 2.3 Kết luận khảo sát — hai nền tảng bù nhau trọn vẹn

Tài liệu `pu-v2-on-ea-architecture.md` (07/09/2026, đã chốt D1–D4) đã đưa ra hướng đúng và khảo sát code xác nhận nó khả thi:

> **PU-v2 = thân PowerUp (data governance + RAG sâu + engine tài chính) + não EA (Hermes agent runtime + MCP gateway + admin governance).**
> Cầu PU↔EA đã vận hành thật từ 07/2026 (`powerup_chat` MCP qua PAT per-user, mã hoá AES-256-GCM).

Bảng bổ sung — mỗi nhu cầu bank dùng gì:

| Nhu cầu | Lấy từ EA | Lấy từ PowerUp | Xây mới |
|---|---|---|---|
| N1 nội bộ | Hermes+MCP runtime, fail-closed gateway, tier/scope, Honcho memory, Langfuse, admin portal | DataTable/ExternalDatabase + ACL, Qdrant hybrid+reranker, DuckDB SQL pattern, engine tính toán | Connector dữ liệu bank (core DB read-only/warehouse), text-to-SQL guard (SELECT-only, cap dòng) |
| N2 khách hàng | RAG ingestion + admin CRUD + OCR, module toggle, behavior rules, notification | PAT OpenAI-compatible API (chứng minh kênh ngoài), multi-tenant config theo domain | Kênh public (web/app/Zalo), **lớp hiệu lực văn bản theo thời gian**, guardrail tone/thương hiệu, handoff CSKH |
| N3 quy trình | **Toàn bộ pattern**: mcp endpoint hẹp theo domain + key riêng, headless `/v1/runs`, kill-switch, idempotency, audit, webhook inbound | bank_transaction_matcher (tiền lệ engine kiểm soát giao dịch) | Rule checks nghiệp vụ Swift/ tín dụng, giao tiếp core banking |

---

## 3. Đề xuất giải pháp

### 3.1 Nguyên tắc chung (thương lượng với bank ngay từ đầu)

1. **On-prem hoàn toàn** — một triển khai = một bank = một instance + DB riêng (EA đã đúng mô hình này; không cần multi-tenant SaaS cho giai đoạn đầu).
2. **Model AI trong nước hoặc self-host** (LiteLLM proxy là điểm chuyển đổi) — dữ liệu ngân hàng không ra biên giới; ràng buộc tương tự đã lập hồ sơ ở dự án bệnh viện (PDPD 91/2025 + NĐ 356/2025, Điều 18 chuyển dữ liệu xuyên biên giới).
3. **Fail-closed + kill-switch mọi nơi**: AI mặc định không được làm gì, trừ khi được cấp phép (EA đã có sẵn cơ chế, đây là điểm bán hàng an toàn số 1 với bank).
4. **Chỉ đọc trước** — AI không ghi vào core banking; ghi ngược (nếu có, giai đoạn sau) chỉ theo cổng kiểm soát 5 điều kiện (pattern `his_write`).
5. **Rule-based trước, ML sau** — mọi tính năng có quy trình thủ công dự phòng.

### 3.2 N1 — Chatbot nội bộ (nền tảng chính, làm trước)

**Kiến trúc đề xuất: PU-v2 theo kiến trúc EA.**

```
Nhân viên bank ──> Web EA-kernel (Next.js, SSO nội bộ bank)
                     │ /api/chat
                     ▼
                  Hermes Agent runtime  (model: LiteLLM → model trong nước/self-host)
                     │ MCP (JSON-RPC, fail-closed, tier theo chức danh)
                     ▼
        ┌────────────┼─────────────────┬──────────────────┐
   [datahub tools]  [policy RAG]     [mem/audit]      [action tools]
   DataTable +      Qdrant hybrid    Honcho memory    task/document/
   ExternalDatabase + reranker +    + audit_log +    attendance (quy trình nội bộ)
   (DB bank,        OCR ingestion    Langfuse trace
   read-only role)
```

- **Thân PU giữ nguyên**: data governance (ACL folder/DataTable tới từng nhóm), RAG pipeline (Qdrant + reranker + OCR), engine tính toán.
- **Thay agent layer PU bằng EA-kernel**: bỏ `central_chat_agent.py` 1.367 dòng + intent keyword; Hermes tự chọn tool; tool định nghĩa 1 lần trong MCP registry; prompt/behavior quản qua admin portal (hết 2 nguồn sự thật).
- **Truy vấn dữ liệu bank**: mỗi nguồn dữ liệu = 1 dataset descriptor (pattern `gsheet` của EA: allow-list, SELECT-only DuckDB in-memory, cap 1.000 dòng) hoặc ExternalDatabase của PU với role read-only của Postgres/Oracle core. **Không nhận SQL tự do từ model** cho nguồn nhạy cảm — pattern `datalake_query` của EA: tham số có kiểu rõ, JSON chuẩn hoá, giới hạn dòng, kèm thời điểm dữ liệu.
- **Phân quyền nội bank**: tier theo chức danh (giao dịch viên / trưởng phòng / lãnh đạo) — EA tier addon đã enforce thật; audit log từng câu hỏi–tool gọi–kết quả.

### 3.3 N2 — Chatbot AI cho khách hàng (hỏi đáp + bán hàng)

**Kiến trúc: EA-kernel + lớp kênh public mới + RAG chính sách có hiệu lực theo thời gian.**

- **Kênh public**: xây 1 public API gateway OpenAI-compatible (nguyên mẫu đã có: PAT API của PU) + widget/tích hợp kênh bank (web, app, sau này Zalo/OA). Gateway ký phiên khách nặc danh hoá (visitor token), rate-limit, chặn PII vào prompt.
- **RAG chính sách — lớp "hiệu lực văn bản" (xây mới, nhỏ nhưng quan trọng)**:
  - Mỗi tài liệu chính sách nạp kèm metadata: `{loại văn bản, số hiệu, ngày ban hành, hiệu lực từ, hiệu lực đến/bị thay thế bởi, phạm vi sản phẩm}`.
  - Ingestion PU (OCR + chunking) + Qdrant payload filter: **chỉ retrieve văn bản còn hiệu lực tại thời điểm hỏi**; khi câu hỏi chỉ định thời gian ("quy định phí chuyển tiền từ 2025") filter theo thời điểm đó.
  - Trả lời bắt buộc trích dẫn số hiệu văn bản + mục; không có nguồn → câu trả lời từ chối có kiểm soát.
  - Quy trình ban hành: văn bản chỉ vào kho sau khi phòng ban chủ quản duyệt (admin CRUD của EA + trạng thái draft/published/retired) — RAG không tự quyết định hiệu lực, nó thực thi metadata do nghiệp vụ duyệt.
- **Bán hàng**: chatbot dẫn dắt nhu cầu → thu thập thông tin form có cấu trúc (sản phẩm quan tâm, thu nhập, mục đích vay…) → **không bao giờ** cam kết lãi suất/hạn mức do AI tự sinh — chỉ đọc từ kho tri thức đã duyệt; khi đủ dữ liệu → handoff sang CRM/CSKH (webhook) hoặc tạo lead. Mọi luồng bán hàng có behavioral rules riêng theo kênh (tone guardrail quản qua admin, giống behavior rules EA).
- **Guardrail thêm cho kênh public**: pre-call classifier (EA ADR 0008 có sẵn pattern) + từ điển nhạy cảm bank (không tư vấn đầu tư cá nhân ngoài phạm vi, không nhận OTP/mật khẩu — chặn và chuyển cảnh báo lừa đảo).

### 3.4 N3 — AI nhúng quy trình (chuyển tiền quốc tế, tín dụng) — kiểm soát, cảnh báo

**Kiến trúc: pattern `his_write` + endpoint MCP hẹp theo domain của EA — KHÔNG cho AI đứng trong luồng giao dịch.**

- **Vị trí AI**: side-checker/cảnh báo — nhận event hoặc dữ liệu bản nháp giao dịch/hồ sơ từ quy trình hiện có (qua webhook/API do core banking hoặc middle-ware gọi), trả về **kết quả kiểm định cấu trúc** (pass/warn/fail + lý do + nguồn quy tắc), con người quyết định cuối. AI không tạo, không sửa, không xác nhận giao dịch.
- **Tool hẹp theo domain** (pattern `/api/mcp-coding`): `/api/mcp-swift` (check thông tin chuyển tiền quốc tế: hợp lệ BIC/IBAN, khớp danh sách kiểm soát/sanction list nội bộ, red-flag ML/TF theo quy tắc bank, charge rule, mô tả có từ khoá nhạy cảm), `/api/mcp-credit` (kiểm tra hồ sơ tín dụng thiếu chứng từ, so khớp điều kiện sản phẩm, tóm tắt hồ sơ, đối chiếu hạn mức). Mỗi endpoint 1 key riêng, tool chỉ đọc + tính, fail-closed.
- **Rule-based trước**: 80% kiểm soát là rule engine thuần (không cần LLM); LLM chỉ ở lớp giải thích kết quả cho cán bộ + xử lý ngoại lệ phi cấu trúc (đọc chứng từ scan — dùng OCR pipeline có sẵn). Mỗi check có kill-switch riêng, tắt là quy trình chạy như cũ (không phụ thuộc AI).
- **Audit & vận hành**: mỗi lần check ghi audit (ai, lúc nào, input hash, kết quả, phiên bản bộ quy tắc); Langfuse trace; dashboard cảnh báo cho compliance.
- **Tích hợp thực tế phụ thuộc việc bank có mở API của core/không** — đây là rủi ro số 1 (tương tự bài học "quyền API HIS với Nanosoft" ở dự án bệnh viện: phải xác nhận chính thức trước khi hẹn lịch). Nếu chưa có API: bắt đầu với luồng "cán bộ kéo dữ liệu/bản nháp vào công cụ kiểm tra" trước, tự động hoá sau.

### 3.5 Vì sao đề xuất này chứng minh được với bank

- Cùng một kiến trúc nền đã chạy production thật trên 2 hệ (EA nhiều khách, PU khách VDI 8 use case), có sẵn: fail-closed gateway, tier theo chức danh, audit, Langfuse, SSO/DB on-prem.
- Pattern tích hợp hệ thống lõi + ghi có kiểm soát đã thiết kế đầy đủ ở dự án bệnh viện (Cổng 1/2/3, his_realtime/datalake_query/his_write, Keycloak) — chuyển bối cảnh sang bank là đổi domain, không phải phát minh lại.
- Engine tài chính thật (bank_transaction_matcher 788 dòng, reconciliation) là bằng chứng đội đã làm bài toán giao dịch/ngân khoản, không chỉ chat.

---

## 4. Lộ trình thực hiện (đề xuất, cần chốt với bank)

> Ước tính cho 1 team 4–6 người (2 BE, 1 AI/ML, 1 FE, 1 BA/QA), bank hỗ trợ một bên phụ trách nghiệp vụ + IT hạ tầng.

### Giai đoạn 0 — Chốt phạm vi & hạ tầng (tuần 1–4)

| Việc | Kết quả |
|---|---|
| Workshop yêu cầu 3 nhu cầu với bank; chốt POC đầu tiên | Tài liệu phạm vi + Acceptance Criteria từng nhu cầu |
| Chốt model AI: catalog LiteLLM với model trong nước/self-host (Viettel AI, VNPT, Qwen/Pho GSM self-host…); sizing GPU nếu self-host | Môi trường model chạy on-prem, benchmark tiếng Việt tài chính |
| Xác nhận với bank: nguồn dữ liệu AI được đọc (DB nào, role read-only), có API core banking hay không, kênh khách hàng nào (web/app/Zalo), quy trình duyệt văn bản nội bộ | Danh sách nguồn + người duyệt + cam kết API (nếu có) |
| Dựng hạ tầng on-prem pilot: app server, MySQL/Postgres, Redis, Qdrant, LightRAG/Honcho, LiteLLM, Langfuse | Sổ tay triển khai (tái dùng Update_Workflow_EA) |

### Giai đoạn 1 — N2 hỏi đáp khách hàng (tuần 5–12) — làm trước vì nhanh chứng minh, rủi ro hẹp

- Tuần 5–6: EA-kernel on-prem + admin nạp chính sách (ingestion OCR chạy thật) + metadata hiệu lực v1 (draft/published/retired).
- Tuần 7–9: public API gateway + widget kênh đầu tiên; filter hiệu lực tại retrieve; trích dẫn số hiệu văn bản bắt buộc; guardrail + pre-call classifier.
- Tuần 10–12: handoff CSKH + dashboard + UAT với phòng nghiệp vụ; đo chất lượng (bộ câu hỏi vàng do bank duyệt, ≥95% có nguồn đúng) → nghiệm thu POC.

### Giai đoạn 2 — N1 chatbot nội bộ PU-v2 (tuần 9–22, chạy song song từ giữa G1)

- Tuần 9–14: dựng EA-kernel + thay agent layer: admin portal quản tool/prompt; migrate data governance PU (Folder/DataTable/ExternalDatabase) vào; connector nguồn dữ liệu đầu tiên (2–3 nguồn nổi đau nhất bank chọn).
- Tuần 15–18: RAG nội bộ (Qdrant + reranker + OCR) cho quy trình/tài liệu nội bộ; tier theo chức danh; audit + Langfuse.
- Tuần 19–22: text-to-SQL/DuckDB có kiểm soát cho phân tích số liệu; tính toán engine; UAT nội bộ với 1 phòng ban đầu tiên, mở rộng dần.

### Giai đoạn 3 — N3 AI nhúng quy trình (tuần 20–30, sau khi N2 chạy ổn và bank đã xác nhận API)

- Tuần 20–23: thiết kế chi tiết 1 quy trình POC (khuyến nghị: kiểm soát chuyển tiền quốc tế — phạm vi hẹp, quy tắc rõ, giá trị an toàn cao) + chốt giao diện tích hợp với core/middleware + thoả thuận "chỉ cảnh báo".
- Tuần 24–27: rule engine + `/api/mcp-swift` + headless check pipeline + dashboard compliance; shadow mode (chạy song song, chỉ ghi nhận, không can thiệp) 2–4 tuần.
- Tuần 28–30: bật warn mode (cảnh báo trên UI quy trình) cho 1 chi nhánh/đội POC; đánh giá tỉ lệ bắt được cảnh báo thật vs nhiễu; quyết định mở rộng.

### Giai đoạn 4 — Mở rộng (tháng 8+)

- Thêm nguồn dữ liệu N1 (mỗi nguồn ≈ 1–2 tuần sau khi pattern chốt — trước đây là copy cả thư mục agent).
- Thêm quy trình N3 thứ hai (tín dụng) tái dùng nền rule + MCP endpoint pattern.
- Nâng cấp identity: Keycloak token exchange (phương án B) khi bank có IAM chuẩn; hardening schema/RBAC của EA (improvements-v2) trước khi scale.

---

## 5. Rủi ro chính & cách xử lý

| Rủi ro | Mức | Xử lý |
|---|---|---|
| Bank không mở được API core banking | Cao với N3 | Bắt đầu shadow/side-check bằng dữ liệu cán bộ nạp; N3 không cam kết tự động hoá trước khi có API ký tên |
| Model tiếng Việt tài chính chưa đạt / không self-host được | Trung bình | Catalog LiteLLM nhiều model; benchmark trước khi cam kết; fallback model trong nước qua API có hồ sơ pháp lý |
| RAG trả văn bản hết hiệu lực | Cao với N2 (rủi ro pháp lý) | Metadata hiệu lực bắt buộc + filter tại retrieve + quy trình ban hành của bank + audit truy vết được |
| userId trust model (model sinh userId) | Trung bình | Với bank: chốt phương án B (Keycloak/SSO token) hoặc A (EA ký JWT — code sẵn) trước khi mở dữ liệu nhạy cảm; giới hạn N2 dùng visitor token không phân quyền dữ liệu |
| Nợ kỹ thuật EA (schema chẻ đôi, RBAC inline) | Trung bình | Hardening trong G2 (đã có kế hoạch improvements-v2); không chặn POC |
| Nợ kỹ thuật PU (agent layer) | Đã loại bỏ bằng PU-v2 | Không migrate agent layer cũ — thay bằng Hermes+MCP |
| Security infra PU (Qdrant từng phơi Internet, ufw inactive) | Cao nếu tái dùng | Checklist hạ tầng bank: bind loopback/whitelist, ufw bắt buộc, audit trước go-live |
| Expectation "AI làm thay giao dịch" từ khách hàng | Cao | Cam kết biên giới rõ từ G0: AI kiểm soát–cảnh báo, người quyết định; kill-switch + thủ công dự phòng là tính năng, không phải hạn chế |

---

## 6. Việc cần chốt ngay (đầu vào để tinh chỉnh đề xuất)

1. Bank chọn POC đầu tiên: N2 (khuyến nghị) hay N1?
2. Danh sách nguồn dữ liệu nội bộ ưu tiên cho N1 (và role read-only có được không).
3. Kênh khách hàng triển khai đầu tiên cho N2 (widget web/app/Zalo) + quy trình duyệt văn bản.
4. Model AI: self-host (GPU sẵn không?) hay dịch vụ trong nước; ai chịu trách nhiệm pháp lý dữ liệu.
5. Với N3: quy trình nào làm POC + có API core banking hay không (quyết định tuần 20 có chạy được G3 hay không).

---

*Phụ lục bằng chứng chi tiết: báo cáo khảo sát EA & PowerUp (transcript khảo sát 12/10/2026), `docs/pu-v2-on-ea-architecture.md`, `docs/datalake/2026-10-05-ea-nen-tang-va-diem-tich-hop-datalake.md`, `docs/architecture/overview.md` v2.3, `docs/architecture/mcp-coding-endpoint-design.md`.*
