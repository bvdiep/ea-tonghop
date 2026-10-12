# Đề xuất Giải pháp
# Nền tảng Trí tuệ Nhân tạo cho Ngân hàng

> **Phiên bản:** 1.0 (draft gửi khách hàng)
> **Ngày:** 12/10/2026
> **Phạm vi:** Trợ lý AI nội bộ · Trợ lý AI khách hàng · AI kiểm soát quy trình nghiệp vụ

---

## 1. Tóm tắt điều hành

Chúng tôi đề xuất xây dựng cho Ngân hàng **một nền tảng AI hợp nhất** phục vụ đồng thời ba bài toán:

1. **Trợ lý AI nội bộ** — trả lời câu hỏi độ phức tạp cao từ nhiều nguồn dữ liệu, có suy luận và tính toán, phục vụ cán bộ mọi cấp.
2. **Trợ lý AI khách hàng** — hỏi đáp và hỗ trợ bán hàng trên các kênh tiếp xúc khách hàng, trả lời đúng chính sách hiện hành, có trích dẫn.
3. **AI kiểm soát quy trình** — hỗ trợ kiểm soát, cảnh báo rủi ro trong các quy trình nghiệp vụ hiện có (chuyển tiền quốc tế, tín dụng…). AI **không thay thế** và **không thực hiện** giao dịch — con người luôn ra quyết định cuối cùng.

Điểm khác biệt của đề xuất:

- **Một nền tảng, ba giải pháp.** Cả ba bài toán dùng chung một kiến trúc nền (mô hình AI, agent, cổng kiểm soát, kho dữ liệu–tri thức, vận hành giám sát) — ngân hàng chỉ quản trị một hệ thống, một mô hình an toàn, một nhật ký kiểm toán. Đây là kết quả của việc chúng tôi đã triển khai thật hai nền tảng AI doanh nghiệp và rút ra bài học: ghép nhiều hệ AI rời rạc khiến chi phí quản trị tăng gấp bội so với chi phí phần mềm.
- **An toàn là thiết kế gốc, không phải lớp vá.** AI mặc định không được làm gì trừ khi được cấp phép rõ ràng (fail-closed); mọi truy cập dữ liệu đi qua cổng kiểm soát độc lập với AI; mọi hành động đều audit được; mọi tính năng có kill-switch và phương án thủ công dự phòng.
- **Triển khai hoàn toàn on-premise, mô hình AI không khóa vendor.** Dữ liệu ngân hàng không rời hạ tầng; lớp mô hình trao đổi được (model gateway) cho phép dùng dịch vụ AI trong nước hoặc tự vận hành mô hình mở, thay thế linh hoạt khi công nghệ thay đổi.

Lộ trình đề xuất: POC đầu tiên trong **8 tuần** (Trợ lý AI khách hàng — nhanh chứng minh giá trị, phạm vi rủi ro hẹp nhất), sau đó mở rộng sang trợ lý nội bộ và kiểm soát quy trình trong **khoảng 7 tháng** cho toàn bộ ba giải pháp.

---

## 2. Ba bài toán của Ngân hàng — cách chúng tôi tiếp cận

### 2.1 Trợ lý AI nội bộ — "hỏi được, tính được, đúng phạm vi"

Câu hỏi của cán bộ ngân hàng thường không dừng ở tra cứu văn bản: so sánh số liệu nhiều kỳ, đối chiếu dư liệu nhiều nguồn, tính toán theo công thức nghiệp vụ, tổng hợp quy định liên quan đến một tình huống cụ thể. Điều này đòi hỏi AI phải làm được ba việc cùng lúc:

| Năng lực | Cách thực hiện |
|---|---|
| Hiểu ý định, chọn đúng nguồn | Agent AI tự phân tích câu hỏi, tự quyết định gọi nguồn dữ liệu/công cụ nào — không phải cây menu cứng |
| Tra dữ liệu có kiểm soát | Truy vấn qua **cổng dữ liệu có phân quyền**: tham số hóa, giới hạn kết quả, phân quyền theo vai trò và đơn vị; với nguồn nhạy cảm không cho AI viết SQL tự do |
| Tính toán, suy luận | Các engine nghiệp vụ chạy tách biệt với LLM (kết quả chính xác 100%, có thể kiểm chứng); LLM chỉ điều phối và giải thích kết quả |

Mỗi nhóm người dùng (giao dịch viên, trưởng phòng, lãnh đạo) thấy đúng phạm vi công cụ và dữ liệu của mình — phân tầng quyền được áp dụng ở cả giao diện lẫn lớp thực thi.

### 2.2 Trợ lý AI khách hàng — "đúng chính sách hiện hành, có trích dẫn, biết giới hạn của mình"

Bài toán khó nhất của chatbot khách hàng ngân hàng không phải là kỹ thuật chat — mà là **chính sách thay đổi theo thời gian**: thông tư, nghị định, biểu phí, điều kiện sản phẩm liên tục được ban hành, sửa đổi, thay thế. Một chatbot trả lời theo văn bản đã hết hiệu lực là rủi ro pháp lý trực tiếp.

Giải pháp của chúng tôi đặt **quản lý hiệu lực văn bản** vào trung tâm kho tri thức:

- Mỗi văn bản khi nạp vào hệ thống mang metadata đầy đủ: loại văn bản, số hiệu, ngày ban hành, hiệu lực từ/đến, văn bản thay thế, phạm vi sản phẩm áp dụng.
- Tại thời điểm trả lời, hệ thống **chỉ truy xuất văn bản còn hiệu lực** (hoặc hiệu lực tại một mốc thời gian được hỏi); câu trả lời **bắt buộc kèm trích dẫn** số hiệu văn bản và điều khoản.
- Văn bản chỉ vào kho tri thức sau khi được phòng ban chủ quản duyệt (quy trình ban hành nội bộ của ngân hàng) — AI không tự quyết định hiệu lực, chỉ thực thi metadata do nghiệp vụ kiểm soát.
- Văn bản hết hiệu lực không bị xóa mà chuyển trạng thái — vẫn tra cứu được theo mốc thời gian lịch sử.

Cho phần bán hàng: chatbot thu thập nhu cầu theo kịch bản có cấu trúc, giải thích sản phẩm từ đúng tài liệu đã duyệt, và **tuyệt đối không tự sinh cam kết** (lãi suất, hạn mức, phê duyệt) — các con số chỉ đến từ nguồn đã phê duyệt; khi đủ dữ liệu, luồng được chuyển cho cán bộ/CRM xử lý tiếp.

### 2.3 AI kiểm soát quy trình — "cảnh báo độc lập, con người quyết định"

Chúng tôi đề xuất định vị AI là **lớp kiểm soát độc lập** đứng cạnh quy trình hiện có, không can thiệp vào luồng giao dịch:

```
Quy trình hiện có (core banking / middleware)
        │  gửi dữ liệu kiểm định (event hoặc bản nháp)
        ▼
Cổng kiểm soát AI  ──>  Bộ quy tắc nghiệp vụ (rule engine, chính xác 100%)
        │              ──>  AI phân tích phi cấu trúc (chứng từ scan, mô tả, bất thường)
        ▼
Kết quả kiểm định: PASS / WARN / FAIL + lý do + nguồn quy tắc
        ▼
Cán bộ nghiệp vụ xem cảnh báo, tự ra quyết định trên quy trình cũ
```

Nguyên tắc bắt buộc:

- **AI chỉ đọc, không ghi.** Không tạo, không sửa, không xác nhận giao dịch. Kết quả kiểm định là thông tin đầu vào cho con người.
- **Rule-based trước, ML sau.** Phần lớn kiểm soát (hợp lệ mã ngân hàng, khớp danh sách kiểm soát, thiếu chứng từ, lệch số liệu…) chạy bằng bộ quy tắc thuần — chính xác, kiểm chứng được; AI chỉ xử lý phần phi cấu trúc và giải thích.
- **Shadow mode trước, cảnh báo sau.** Hệ thống chạy song song quy trình thật, chỉ ghi nhận — đo tỉ lệ bắt được rủi ro thật so với nhiễu — rồi mới bật cảnh báo cho cán bộ, bắt đầu từ phạm vi hẹp.
- **Kill-switch từng loại kiểm tra.** Tắt bất kỳ kiểm tra nào, quy trình chạy như cũ — ngân hàng không phụ thuộc vào AI để vận hành.

---

## 3. Nguyên tắc thiết kế

Bảy nguyên tắc áp dụng cho toàn bộ giải pháp (cam kết thiết kế, không phải lời hứa vận hành):

1. **On-premise hoàn toàn.** Toàn bộ phần mềm, dữ liệu, nhật ký chạy trong hạ tầng ngân hàng. Không dữ liệu nghiệp vụ rời hạ tầng.
2. **Mô hình AI không khóa vendor.** Lớp model gateway cho phép hoán đổi mô hình (dịch vụ AI trong nước có hồ sơ pháp lý, hoặc mô hình mở tự vận hành trên GPU của ngân hàng) mà không thay đổi ứng dụng.
3. **Fail-closed.** AI mặc định không có quyền làm gì. Mỗi nhóm năng lực được cấp phép tường minh; cấu hình thiếu/lỗi → hệ từ chối, không mở rộng quyền.
4. **Cổng kiểm soát độc lập.** Giữa AI và dữ liệu/hành động luôn có một lớp trung gian kiểm tra quyền — AI không bao giờ chạm trực tiếp dữ liệu. Lớp này chặn cả khi AI bị thao túng (prompt injection) cố gọi ngoài phạm vi.
5. **Chỉ đọc trước.** Giai đoạn đầu AI chỉ đọc dữ liệu. Ghi ngược (nếu có, giai đoạn sau) phải qua cổng riêng: thỏa thuận phạm vi, xác nhận của con người trước mỗi lần ghi, chống ghi trùng, audit đầy đủ.
6. **Human-in-the-loop.** Mọi quyết định có hệ quả nghiệp vụ (duyệt, cảnh báo chốt, cam kết với khách) do con người quyết định.
7. **Kiểm chứng được.** Mỗi câu trả lời truy vết được nguồn; mỗi hành động của AI có audit log (ai, lúc nào, làm gì, kết quả gì); toàn bộ luồng AI có tracing phục vụ điều tra sự cố.

---

## 4. Kiến trúc giải pháp — một nền tảng hợp nhất

### 4.1 Bốn tầng

```
┌─────────────────────────────────────────────────────────────────┐
│  TẦNG 4 — GIẢI PHÁP & KÊNH                                      │
│  Trợ lý nội bộ (web)  ·  Trợ lý khách hàng (web/app)  ·         │
│  Kiểm soát quy trình (API/middleware tích hợp core banking)     │
├─────────────────────────────────────────────────────────────────┤
│  TẦNG 3 — NỀN TẢNG DỮ LIỆU & TRI THỨC                           │
│  Tri thức phi cấu trúc (RAG)  ·  Tri thức cấu trúc (bảng,       │
│  nguồn dữ liệu ngoài)  ·  Metadata hiệu lực & phân quyền        │
├─────────────────────────────────────────────────────────────────┤
│  TẦNG 2 — AGENT RUNTIME & CỔNG KIỂM SOÁT AI                     │
│  Agent điều phối  ·  MCP gateway fail-closed  ·  tier/role  ·   │
│  audit  ·  observability (trace từng luồng)                     │
├─────────────────────────────────────────────────────────────────┤
│  TẦNG 1 — MÔ HÌNH AI (model gateway)                            │
│  LLM trong nước / mô hình mở self-host  ·  OCR · STT ·          │
│  embedding/rerank — thay thế được từng thành phần               │
└─────────────────────────────────────────────────────────────────┘
```

- **Tầng 1 — Mô hình AI:** mọi thành phần AI (ngôn ngữ, OCR, embedding) trao đổi qua một điểm gateway chuẩn; có thể bắt đầu bằng dịch vụ trong nước và chuyển dần sang self-host khi sẵn GPU, hoặc ngược lại, không phải sửa ứng dụng.
- **Tầng 2 — Agent runtime & cổng kiểm soát:** agent nhận câu hỏi/ngữ cảnh, tự chọn công cụ; nhưng **quyền làm gì** không do agent tự quyết — cổng MCP fail-closed kiểm tra (module được bật? đúng vai trò? đúng phạm vi user?) trước khi thực thi, và trả kết quả "không tồn tại" với công cụ bị cấm (không tiết lộ sự tồn tại). Mọi luồng có tracing phục vụ giám sát.
- **Tầng 3 — Nền tảng Dữ liệu & Tri thức:** xem §4.2 — đây là tầng đầu tư nhiều nhất và là tài sản dài hạn của ngân hàng.
- **Tầng 4 — Giải pháp & kênh:** ba gói giải pháp dùng chung ba tầng dưới; thêm giải pháp mới về sau = thêm module trên nền có sẵn.

### 4.2 Nền tảng Dữ liệu & Tri thức — tầng lõi của đề xuất

Kinh nghiệm triển khai cho thấy: giá trị bền vững của AI doanh nghiệp không nằm ở chatbot, mà ở **kho tri thức có quản trị** mà chatbot đọc được. Vì vậy chúng tôi đặt trung tâm đề xuất vào một nền tảng dữ liệu–tri thức hợp nhất, gồm hai loại tài sản:

**a) Tri thức phi cấu trúc** — văn bản, chính sách, quy trình, biểu mẫu, công văn, hợp đồng:

- Nạp tài liệu đa định dạng (PDF, Word, file scan/ảnh) với OCR tự động; pipeline xử lý bất đồng bộ.
- Truy xuất lai (hybrid search) + xếp hạng lại (reranker) — độ chính xác truy xuất cao hơn search từ khóa đơn thuần, đã vận hành thật với kho tài liệu doanh nghiệp lớn.
- **Metadata hiệu lực theo thời gian** (đặc thù chính sách ngân hàng — xem §2.2).
- Phân quyền truy cập theo đơn vị/vai trò: cùng một câu hỏi, mỗi người chỉ nhận câu trả lời từ phần tri thức mình được phép thấy.

**b) Tri thức cấu trúc** — bảng dữ liệu nghiệp vụ, số liệu từ hệ thống nguồn (DWH, các hệ ứng dụng):

- Quản lý như những **bộ dữ liệu có danh mục**: mỗi nguồn dữ liệu đăng ký tường minh (được phép đọc gì, ai được đọc, schema gì), không phải kết nối tự do.
- Truy vấn qua lớp kiểm soát: SELECT-only, tham số hóa cho nguồn nhạy cảm, giới hạn số dòng, gắn nhãn thời điểm dữ liệu.
- Khả năng phân tích (SQL trên kho dữ liệu hợp nhất) phục vụ câu hỏi tổng hợp, so sánh, báo cáo ad-hoc của trợ lý nội bộ.

**c) Liên kết hai loại tri thức** — điểm mạnh khác biệt: một câu trả lời có thể đồng thời trích dẫn điều khoản văn bản và kéo số liệu thực tế ("phí chuyển tiền hiện hành là bao nhiêu?" → điều khoản quy định + biểu phí từ bảng, cùng nguồn truy vết).

**d) Vòng đời & nguồn gốc:** trạng thái văn bản/bộ dữ liệu (nháp → công bố → nghỉ hưu), người duyệt, lịch sử thay đổi — phục vụ kiểm toán nội bộ và kiểm tra của Ngân hàng Nhà nước.

### 4.3 Các phương án kiến trúc đã cân nhắc

| Phương án | Mô tả | Đánh giá |
|---|---|---|
| **A. Một nền tảng hợp nhất (khuyến nghị)** | Ba giải pháp dùng chung một nền tảng; kho dữ liệu–tri thức là tầng lõi dùng chung | Quản trị đơn giản nhất cho ngân hàng; một mô hình an toàn, một audit, một đội vận hành; chi phí sở hữu thấp nhất dài hạn |
| B. Tích hợp nhiều hệ AI có sẵn | Mỗi bài toán một hệ, nối qua API chuẩn | Nhanh cho từng mảnh nhưng nhân đôi chi phí quản trị, an ninh, audit; trải nghiệm không đồng nhất; phù hợp chỉ khi có ràng buộc đặc biệt |
| C. Xây mới hoàn toàn theo từng dự án | Không dùng nền tảng có sẵn | Rủi ro cao nhất về chất lượng, thời gian; không tận dụng được thành phần đã kiểm chứng |

Chúng tôi khuyến nghị phương án A. Nếu ngân hàng có ràng buộc đặc thù đòi hỏi phương án khác, kiến trúc tầng của chúng tôi vẫn cho phép linh hoạt tổ hợp (ví dụ dùng riêng tầng 3 với hệ chatbot có sẵn của ngân hàng).

---

## 5. Ba gói giải pháp

### Gói 1 — Trợ lý AI nội bộ

**Đối tượng:** cán bộ, quản lý các phòng ban; lãnh đạo.

**Tính năng chính:**

- Hỏi đáp tri thức nội bộ (quy trình, quy định, sản phẩm) với trích dẫn nguồn và phân quyền theo vai trò.
- Truy vấn dữ liệu nghiệp vụ: hỏi bằng câu tự nhiên, hệ truy vấn qua cổng dữ liệu có kiểm soát, trả kết quả dạng bảng/biểu đồ kèm thời điểm dữ liệu.
- Tính toán & tổng hợp: so sánh nhiều kỳ, nhiều nguồn; công thức nghiệp vụ chạy ở engine tách biệt (chính xác tuyệt đối, không "ảo giác số liệu").
- Suy luận tình huống: ghép nhiều nguồn (quy định + số liệu + hồ sơ) để trả lời câu hỏi phức tạp, mỗi kết luận đều chỉ ra căn cứ.
- Bộ nhớ hội thoại theo từng cán bộ (hệ nhớ ngữ cảnh làm việc lâu dài), phiên chat riêng tư giữa các user.
- Làm được việc: soạn nháp văn bản theo mẫu, tạo việc/nhắc việc, tổng hợp biên bản họp (từ ghi âm — STT) — mở rộng theo từng đợt.

**An toàn:** phân tầng quyền theo chức danh ở cả giao diện và lớp thực thi; nguồn dữ liệu đăng ký tường minh; audit toàn bộ; không AI nào thấy dữ liệu ngoài phạm vi của mình.

### Gói 2 — Trợ lý AI khách hàng (hỏi đáp – bán hàng)

**Đối tượng:** khách hàng cá nhân/doanh nghiệp trên kênh web/app của ngân hàng.

**Tính năng chính:**

- Hỏi đáp sản phẩm, biểu phí, điều kiện, thủ tục — **luôn theo văn bản còn hiệu lực, có trích dẫn số hiệu**.
- Cơ chế hiệu lực theo thời gian: hỗ trợ cả câu hỏi lịch sử ("quy định phí chuyển tiền năm 2025?") — trả đúng văn bản hiệu lực tại mốc đó.
- Hỗ trợ bán hàng: giới thiệu sản phẩm phù hợp nhu cầu, thu thập thông tin theo kịch bản có cấu trúc, tạo lead chuyển cán bộ/CRM; không tự sinh cam kết lãi suất/hạn mức/phê duyệt.
- Nhận diện và từ chối đúng cách các nội dung ngoài phạm vi; cảnh báo chống lừa đảo (AI không bao giờ hỏi lại OTP/mật khẩu — đây là nội dung cài cứng ở lớp kiểm soát).
- Chuyển tiếp có kiểm soát sang CSKH khi vượt khả năng hoặc khách yêu cầu.
- Quản trị kênh: guardrail giọng điệu/thương hiệu cấu hình được; dashboard giám sát chất lượng, chủ đề được hỏi, tỉ lệ chuyển tiếp.

**An toàn:** phiên khách hàng tách biệt hoàn toàn với dữ liệu nội bộ; rate-limit; lọc dữ liệu cá nhân trước khi vào mô hình; mọi hội thoại lưu trữ audit phục vụ xử lý khiếu nại.

### Gói 3 — AI kiểm soát quy trình nghiệp vụ

**Đối tượng:** các quy trình có sẵn — POC khuyến nghị bắt đầu với **chuyển tiền quốc tế** (phạm vi hẹp, quy tắc rõ, giá trị an toàn cao), mở rộng sang tín dụng.

**Tính năng chính (theo từng quy trình):**

- Kiểm tra tính hợp lệ dữ liệu giao dịch/hồ sơ: mã ngân hàng (BIC/IBAN), định dạng trường, khớp biểu phí và quy tắc tính.
- Đối chiếu danh sách kiểm soát nội bộ (sanction/watchlist theo quy định của ngân hàng) và red-flag theo bộ quy tắc AML do ngân hàng định nghĩa.
- Kiểm tra hồ sơ tín dụng: đủ/không đủ chứng từ theo loại sản phẩm, so khớp điều kiện sản phẩm, tóm tắt hồ sơ cho cán bộ thẩm định, đọc chứng từ scan (OCR) trích xuất dữ liệu có cấu trúc.
- Giải thích cảnh báo bằng ngôn ngữ tự nhiên cho cán bộ: vì sao WARN/FAIL, căn cứ quy tắc/văn bản nào.
- Dashboard tuân thủ: thống kê cảnh báo theo loại, xu hướng, tỉ lệ phát hiện/nhiễu — đầu vào cho compliance.

**An toàn:** AI chỉ đọc; shadow mode 2–4 tuần trước khi bật cảnh báo thật; kill-switch từng loại kiểm tra; audit từng lần kiểm định (input hash, kết quả, phiên bản bộ quy tắc); người ra quyết định cuối cùng.

---

## 6. An toàn, bảo mật & tuân thủ

| Lĩnh vực | Cam kết thiết kế |
|---|---|
| Hạ tầng | On-premise/private cloud của ngân hàng; không phụ thuộc dịch vụ nước ngoài cho dữ liệu nghiệp vụ |
| Dữ liệu cá nhân | Thiết kế tuân thủ Luật Bảo vệ dữ liệu cá nhân (91/2025/QH15) và các nghị định hướng dẫn; ánh xạ dữ liệu cá nhân vào danh mục quản lý; khử định danh khi bắt buộc |
| Model | Ưu tiên dịch vụ AI trong nước có hồ sơ pháp lý; phương án mô hình mở self-host trên GPU ngân hàng; chuyển đổi không khóa vendor |
| Phân quyền | Fail-closed, phân tầng theo vai trò & đơn vị, enforce ở lớp thực thi (không chỉ ẩn giao diện) |
| Kiểm toán | Audit log mọi hành động AI + tracing toàn luồng; truy vết được từng câu trả lời về nguồn dữ liệu |
| Khả dụng | Kill-switch từng tính năng; phương án thủ công dự phòng; AI ngoài luồng nghiệp vụ |
| Thao túng AI | Phòng chống prompt injection ở lớp cổng kiểm soát (chặn thực thi, không chỉ khuyên bảo); kiểm thử bảo mật trước go-live |

---

## 7. Kinh nghiệm & năng lực thực tế

Chúng tôi không đề xuất trên giấy trắng mực đen. Các thành phần cốt lõi của kiến trúc này **đã được xây dựng và vận hành thật** trong hai nền tảng AI doanh nghiệp của chúng tôi (đại diện ẩn danh theo thỏa thuận):

- **Nền tảng trợ lý AI doanh nghiệp** — chạy production cho khách hàng doanh nghiệp từ 2026; đã chứng minh: agent runtime tự điều phối công cụ, cổng kiểm soát MCP fail-closed (13 nhóm năng lực/43 công cụ vận hành), phân tầng quyền theo vai trò, kho tri thức RAG với admin tự quản tài liệu + OCR, bộ nhớ hội thoại dài hạn per-user, tracing/observability toàn luồng. Tích hợp hệ thống lõi doanh nghiệp qua cổng dữ liệu có kiểm soát đã được thiết kế chi tiết cho một khách hàng y tế quy mô lớn (nguyên tắc chỉ-đọc-trước, ghi có cổng kiểm soát 5 điều kiện).
- **Nền tảng phân tích dữ liệu & RAG** — vận hành với khách hàng doanh nghiệp (đa khách theo mô hình SaaS): quản trị dữ liệu phân quyền chi tiết tới từng thư mục/bảng, pipeline RAG sâu (vector database + hybrid search + reranker + OCR GPU), engine đối chiếu/sánh kỳ giao dịch ngân hàng, quy trình đối soát và tạo báo cáo — đang phục vụ bộ use case thực tế của khách hàng.
- Hai nền tảng đã **nối thông với nhau** qua cổng MCP chuẩn mở với xác thực từng người dùng — tiền lệ kỹ thuật cho kiến trúc hợp nhất chúng tôi đề xuất.

Đội ngũ: kiến trúc sư + kỹ sư AI/ML + backend + frontend + BA, đã vận hành các hệ thống trên qua nhiều chu kỳ release thật (hàng trăm thay đổi, hệ thống audit nội bộ đầy đủ).

---

## 8. Lộ trình triển khai đề xuất

> Ước tính cho đội 4–6 người phối hợp với ngân hàng (1 bên phụ trách nghiệp vụ + 1 bên IT hạ tầng). Thời gian thực tế điều chỉnh theo kết quả workshop phạm vi.

### Giai đoạn 0 — Chốt phạm vi & hạ tầng (tuần 1–4)

- Workshop 3 bài toán với các phòng ban; chốt POC đầu tiên + tiêu chí nghiệm thu.
- Chọn mô hình AI: benchmark model tiếng Việt tài chính (dịch vụ trong nước và/hoặc self-host); dựng model gateway.
- Ngân hàng xác nhận: nguồn dữ liệu AI được đọc (vai trò read-only), kênh khách hàng triển khai đầu tiên, quy trình duyệt văn bản nội bộ.
- Dựng hạ tầng pilot on-premise (app server, CSDL, Redis, vector DB, model gateway, tracing).

### Giai đoạn 1 — POC Trợ lý AI khách hàng (tuần 5–12)

- Tuần 5–6: nền tảng on-prem + quy trình nạp chính sách (OCR chạy thật) + metadata hiệu lực v1.
- Tuần 7–9: kênh khách hàng đầu tiên (widget web/app) + filter hiệu lực tại truy xuất + trích dẫn bắt buộc + guardrail.
- Tuần 10–12: chuyển tiếp CSKH + dashboard + UAT với phòng nghiệp vụ. **Nghiệm thu POC: bộ câu hỏi vàng do ngân hàng duyệt, ≥95% trả lời có nguồn đúng và đúng hiệu lực.**

### Giai đoạn 2 — Trợ lý AI nội bộ (tuần 9–22, song song từ giữa giai đoạn 1)

- Tuần 9–14: nền tảng nội bộ + phân quyền theo chức danh + kết nối 2–3 nguồn dữ liệu ưu tiên nhất (ngân hàng chọn).
- Tuần 15–18: kho tri thức nội bộ (RAG + OCR) + audit + tracing.
- Tuần 19–22: phân tích số liệu có kiểm soát (SQL trên kho hợp nhất) + engine tính toán + UAT với phòng ban đầu tiên.

### Giai đoạn 3 — AI kiểm soát quy trình (tuần 20–30)

- Điều kiện tiên quyết: ngân hàng xác nhận giao diện tích hợp với core banking/middleware (API hoặc luồng dữ liệu kiểm định) — khuyến nghị chốt trong Giai đoạn 0.
- Tuần 20–23: thiết kế chi tiết quy trình POC (khuyến nghị: chuyển tiền quốc tế) + bộ quy tắc v1 cùng đơn vị nghiệp vụ.
- Tuần 24–27: triển khai cổng kiểm soát + rule engine + dashboard; **shadow mode** 2–4 tuần.
- Tuần 28–30: bật cảnh báo thật cho phạm vi hẹp (1 chi nhánh/đội POC); đo tỉ lệ phát hiện/nhiễu; quyết định mở rộng.

### Giai đoạn 4 — Mở rộng (từ tháng 8)

- Thêm nguồn dữ liệu, thêm quy trình kiểm soát (tín dụng), thêm kênh khách hàng — mỗi mở rộng 2–4 tuần trên nền có sẵn.
- Nâng cấp định danh (SSO/IAM của ngân hàng) và mở rộng quy mô hạ tầng khi phục vụ toàn lực lượng.

---

## 9. Mô hình hợp tác đề xuất

1. **POC 8 tuần** cho Trợ lý AI khách hàng — tiêu chí nghiệm thu định lượng (chất lượng trả lời, độ đúng hiệu lực văn bản, độ trễ), chi phí cố định.
2. **Hợp đồng triển khai giai đoạn chính** theo lộ trình §8, nghiệm thu theo từng giai đoạn, thanh toán theo milestone.
3. **Hợp đồng vận hành & phát triển** (optional): SLA vận hành, nâng cấp model/kỹ thuật định kỳ, phát triển module mới theo nhu cầu.

Mọi mã nguồn triển khai cho ngân hàng thuộc quyền sở hữu/sử dụng theo thỏa thuận; không khóa vendor ở mọi tầng (dữ liệu xuất được, mô hình thay được, thành phần mã nguồn mở theo chuẩn mở MCP).

---

## 10. Thông tin chúng tôi cần từ Ngân hàng

1. Ưu tiên POC đầu tiên: Trợ lý AI khách hàng (khuyến nghị) hay Trợ lý nội bộ?
2. Danh sách nguồn dữ liệu nội bộ dự kiến cho trợ lý AI (hệ thống, CSDL, DWH) và khả năng cấp vai trò read-only.
3. Kênh tiếp xúc khách hàng triển khai đầu tiên (web / mobile app / khác) và cơ chế duyệt nội dung.
4. Định hướng mô hình AI: dịch vụ trong nước, self-host (GPU sẵn có?), hay kết hợp.
5. Với AI kiểm soát quy trình: quy trình làm POC và khả năng cung cấp giao diện dữ liệu từ core banking/middleware.
6. Các ràng buộc pháp lý/bảo mật riêng (vùng dữ liệu, chuẩn mã hóa, chuẩn IAM) để đưa vào thiết kế từ đầu.

---

*Phụ lục (theo yêu cầu): đặc tả kỹ thuật chi tiết từng tầng, tài liệu an toàn thông tin, hồ sơ năng lực các nền tảng đã triển khai — cung cấp trong buổi làm việc trực tiếp.*
