# Product Showcase
# Chatbot AI Nội bộ cho Ngân hàng — từ bài toán đến giải pháp

> **Loại:** Pitch / showcase sản phẩm gửi khách hàng
> **Ngày:** 12/10/2026
> **Sản phẩm giới thiệu:** Enterprise Assistant (EA) & PowerUp — hai nền tảng AI doanh nghiệp đã triển khai thật
> **Bài toán trọng tâm:** Trợ lý AI nội bộ — truy vấn, trả lời độ phức tạp cao từ nhiều nguồn, suy luận, tính toán

---

## 1. Bài toán: những câu hỏi "khó" hàng ngày của ngân hàng

Mỗi ngày, hàng nghìn câu hỏi phát sinh bên trong ngân hàng — và phần lớn những câu hỏi có giá trị nhất lại là những câu **khó nhất**:

> *"So sánh dư nợ tín dụng theo ngành của 3 chi nhánh quý này với quý trước, và đối chiếu với trần tăng trưởng tín dụng theo quy định hiện hành."*

> *"Hồ sơ cho vay doanh nghiệp nhỏ cần đủ những chứng từ gì theo quy định mới nhất? Hồ sơ khách hàng X đang thiếu gì?"*

> *"Tổng hợp tỷ lệ nợ xấu theo nhóm ngành 6 tháng gần nhất, lập thành biểu đồ gửi Ban điều hành."*

Đặc điểm chung của những câu hỏi này: **không nằm trong một hệ thống nào cả**. Muốn trả lời, cán bộ phải mở nhiều hệ thống cùng lúc — dữ liệu nằm ở hệ thống nghiệp vụ/DWH, quy định nằm ở kho văn bản, công thức tính nằm trong đầu chuyên gia, rồi tự ghép chúng lại bằng Excel. Mỗi câu hỏi kiểu này tiêu tốn từ vài mươi phút đến vài giờ, và kết quả tùy thuộc người tìm.

Câu hỏi đặt ra: **có thể để AI làm thay phần việc đó — nhanh hơn, nhất quán hơn, và kiểm soát được không?**

---

## 2. Vì sao chatbot "thông thường" không giải được

| Yêu cầu thực tế | Chatbot phổ thông (ChatGPT-style) | Nền tảng AI doanh nghiệp đúng chuẩn |
|---|---|---|
| Trả lời từ **dữ liệu thật** của ngân hàng | Không truy cập được — hoặc phải tự ghép nối | Truy vấn qua cổng dữ liệu có phân quyền |
| Trả lời theo **quy định hiện hành** | Không biết văn bản nội bộ; dễ trả lời theo dữ liệu quá khứ của model | RAG kho tri thức nội bộ, đúng phiên bản hiệu lực, có trích dẫn |
| **Tính toán chính xác** | LLM "đoán" số — sai lặng lẽ | Engine tính toán tách biệt, kết quả kiểm chứng được |
| **Phân quyền** theo vai trò | Không có — ai hỏi cũng nhận cùng câu trả lời | Phân tầng quyền ở cả giao diện và lớp thực thi |
| **Kiểm chứng & audit** | Không truy vết được | Mọi câu trả lời có nguồn, mọi hành động có nhật ký |
| Chạy **on-premise** | Cloud công cộng — không thể chấp nhận với dữ liệu ngân hàng | Triển khai hoàn toàn trong hạ tầng ngân hàng |

Bài toán của ngân hàng không phải "có chatbot", mà là **có một trợ lý biết đọc dữ liệu và quy định của chính ngân hàng, tính toán chính xác, đúng phạm vi được phép — và chứng minh được điều đó**.

---

## 3. Phương án kỹ thuật: bốn năng lực lõi

### 3.0 Tại sao "truy vấn đa nguồn + suy luận" là bài toán thực sự khó

Google tìm kiếm được mọi thứ trên internet — nhưng AI doanh nghiệp lại khó khăn khi tra cứu dữ liệu đa nguồn nội bộ. Không phải vì thiếu mô hình ngôn ngữ, mà vì bài toán khác hoàn toàn bản chất:

| | Google / internet | Dữ liệu nội bộ ngân hàng |
|---|---|---|
| **Dữ liệu** | Công khai, đã được crawl và index sẵn | Phân tán trên DWH, CSDL nghiệp vụ, kho văn bản, file scan — chưa từng được tổ chức cho AI |
| **Ngôn ngữ** | Từ khóa đồng nhất | Thuật ngữ nội bộ, viết tắt, tên bảng, mã phòng ban — không ai gán nhãn cho AI |
| **Quyền** | Ai cũng xem được | Phân quyền theo chức danh, theo phòng ban, theo đối tượng khách hàng — AI phải tôn trọng đúng |
| **Thời điểm** | Trang web cũ là trang web cũ | Quy định thay đổi theo thời gian — AI phải biết "hiện hành" là phiên bản nào |
| **Tính toán** | Không có | Số liệu phải tính chính xác tuyệt đối — không được "gần đúng" |
| **Trách nhiệm** | Không ai kiểm tra | Mọi câu trả lời phải truy vết được nguồn, phục vụ kiểm toán |

**Bài toán không phải "tìm kiếm" — mà là "hiểu đúng ngữ cảnh doanh nghiệp, truy xuất đúng nguồn, tính đúng, và chứng minh được."** Đây là lý do hầu hết các thử nghiệm AI trong ngân hàng dừng lại ở demo — vì họ giải quyết phần dễ (chat), không giải quyết phần khó (truy vấn đa nguồn có kiểm soát + suy luận có căn cứ).

Kiến trúc của chúng tôi được thiết kế quanh đúng bốn từ khóa trong yêu cầu: **truy vấn — đa nguồn — suy luận — tính toán**. Mỗi năng lực đều đã được triển khai và vận hành thật — không phải thiết kế trên giấy.

### 3.1 TRUY VẤN — hỏi dữ liệu bằng tiếng Việt, qua cổng có kiểm soát

**Bài toán con:** Cán bộ ngân hàng không biết SQL, không biết tên bảng, không biết nguồn dữ liệu nằm ở đâu. Họ chỉ biết câu hỏi nghiệp vụ. Nhưng cho phép AI tự do viết SQL trên CSDL ngân hàng là không thể chấp nhận — một lỗi logic có thể lộ dữ liệu nhạy cảm hoặc trả về kết quả sai.

**Giải pháp:** Cán bộ hỏi bằng câu tự nhiên: *"Liệt kê các khoản vay SME đến hạn trong 30 ngày tới theo chi nhánh."* Agent AI phân tích câu hỏi, tự chọn nguồn dữ liệu và cách truy vấn — nhưng **không được tự do viết SQL tùy ý** trên nguồn nhạy cảm. Truy vấn đi qua lớp kiểm soát với tham số hóa, chỉ-đọc, giới hạn số dòng, và gắn nhãn **thời điểm dữ liệu** trên kết quả. Mỗi nguồn dữ liệu được **đăng ký tường minh** (đọc được gì, ai được đọc) — như một danh mục, không phải kết nối tự do.

**Đã triển khai thật:** EA đã vận hành module truy vấn dữ liệu có kiểm soát với phân quyền theo chức danh — giao dịch viên chỉ thấy dữ liệu chi nhánh của mình, trưởng phòng thấy được tổng hợp nhiều chi nhánh. PowerUp cung cấp lớp đăng ký nguồn dữ liệu với phân quyền chi tiết tới từng bảng, từng thư mục.

### 3.2 ĐA NGUỒN — dữ liệu, văn bản, hệ thống trong cùng một câu trả lời

**Bài toán con:** Câu hỏi của ngân hàng hiếm khi chỉ cần một nguồn. *"So sánh dư nợ theo ngành 3 chi nhánh Q3 với Q2, đối chiếu trần tăng trưởng tín dụng hiện hành"* — cần số liệu từ DWH (cấu trúc) VÀ văn bản quy định (phi cấu trúc) CÙNG LÚC. Hầu hết các giải pháp RAG chỉ giải quyết được một loại dữ liệu — hoặc vector search trên văn bản, hoặc SQL trên bảng. Không có giải pháp nào ghép chúng lại một cách có kiểm soát.

**Giải pháp:** Tri thức cấu trúc (bảng số liệu, CSDL nghiệp vụ, DWH) và tri thức phi cấu trúc (thông tư, quy định, quy trình, biểu phí, file scan) nằm chung một nền tảng dữ liệu–tri thức. Một câu trả lời có thể **đồng thời** kéo số liệu thực tế và trích dẫn điều khoản văn bản — cùng truy vết được nguồn. Nạp tài liệu đa định dạng (PDF, Word, **ảnh scan**) với OCR tự động; nhận diện cấu trúc bảng biểu trong tài liệu — đúng đặc thù văn bản ngân hàng (biểu phí, bảng điều kiện). Truy xuất lai (hybrid search) + xếp hạng lại (reranker): tìm đúng đoạn văn bản cần thiết trong kho hàng nghìn trang.

**Đã triển khai thật:** PowerUp đã xây dựng và vận hành pipeline tri thức sâu với hybrid search (vector + keyword) + reranker model + OCR GPU — xử lý được văn bản ngân hàng đặc thù như biểu phí dạng bảng, thông tư dạng scan. EA tích hợp pipeline này qua cổng MCP, cho phép agent truy xuất cả dữ liệu cấu trúc và phi cấu trúc trong cùng một luồng hội thoại.

### 3.3 SUY LUẬN — agent tự lập kế hoạch, kết luận luôn có căn cứ

**Bài toán con:** Câu hỏi phức tạp không có câu trả lời sẵn trong một tài liệu. *"Hồ sơ vay của khách hàng X còn thiếu chứng từ gì so với quy định cho vay trung dài hạn?"* — cần truy vấn hệ thống hồ sơ, truy xuất danh mục chứng từ bắt buộc, rồi đối chiếu và lập kế hoạch hành động. Không phải cây luồng cứng định nghĩa trước — mà là suy luận động dựa trên ngữ cảnh câu hỏi.

**Giải pháp:** Mỗi câu hỏi được agent **phân tích và lập kế hoạch**: cần nguồn nào, gọi công cụ nào theo thứ tự nào, thiếu dữ liệu thì hỏi lại hay báo thiếu. Kết luận trong câu trả lời **bắt buộc gắn căn cứ**: số liệu từ nguồn nào, văn bản số hiệu nào điều khoản nào. Không có căn cứ → câu trả lời từ chối có kiểm soát, không bịa. Bộ nhớ hội thoại theo từng cán bộ: trợ lý nhớ ngữ cảnh làm việc lâu dài, hỗ trợ câu hỏi nối tiếp tự nhiên.

**Đã triển khai thật:** EA đã vận hành agent runtime tự điều phối với 13 nhóm năng lực / 43 công cụ — agent tự nhận diện ý định, tự chọn công cụ phù hợp, tự lập kế hoạch truy vấn nhiều nguồn. Hệ thống audit ghi nhận toàn bộ chuỗi suy luận: từ câu hỏi → kế hoạch → công cụ gọi → kết quả trung gian → câu trả lời cuối. Đây là điều kiện tiên quyết để ngân hàng chấp nhận AI trong môi trường có kiểm toán.

### 3.4 TÍNH TOÁN — engine nghiệp vụ tách biệt LLM

**Bài toán con:** LLM "đoán" số — đôi khi đúng, đôi khi sai lặng lẩ. Trong ngân hàng, một con số sai trong báo cáo dư nợ có thể dẫn đến quyết định tín dụng sai. Không thể chấp nhận "gần đúng" khi nói về tiền.

**Giải pháp:** Mọi phép tính nghiệp vụ (so sánh kỳ, tỷ lệ, ngưỡng, quy đổi) chạy ở **engine tách biệt với mô hình ngôn ngữ** — chính xác tuyệt đối, không "ảo giác số liệu". LLM chỉ điều phối và giải thích kết quả. Đây là nguyên tắc thiết kế, không phải tùy chọn cấu hình.

**Đã triển khai thật:** PowerUp đã xây dựng engine đối soát và so khớp giao dịch ngân hàng (788 dòng mã đối soát đã chạy thật với khách hàng) — đây là bài toán "tiền bạc" thật, không chỉ chat. Engine tính toán tách biệt đảm bảo mọi con số trong câu trả lời đều kiểm chứng được bằng cách tái tính từ dữ liệu gốc.

### 3.5 An toàn xuyên suốt — nền móng, không phải lớp vá

**Bài toán con:** Ngân hàng không thể chấp nhận AI "tự do" — mọi hành động phải có kiểm soát, mọi câu trả lời phải truy vết được, mọi quyền truy cập phải phân tầng. Đây không phải tính năng thêm vào sau — mà là điều kiện tiên quyết để AI được phép chạy trong ngân hàng.

**Giải pháp:** **Fail-closed:** AI mặc định không được làm gì; từng nhóm năng lực được cấp phép tường minh; công cụ bị tắt trả lời y như "không tồn tại". **Cổng kiểm soát độc lập** đứng giữa AI và dữ liệu — chặn cả khi AI bị thao túng cố gồng ngoài phạm vi. **Phân tầng theo chức danh:** giao dịch viên, trưởng phòng, lãnh đạo — mỗi cấp thấy đúng công cụ và dữ liệu của mình, kiểm tra ở lớp thực thi chứ không chỉ ẩn giao diện. **Audit + tracing toàn luồng:** truy vết được từng câu trả lời về đúng nguồn dữ liệu và văn bản; phục vụ kiểm toán nội bộ và cơ quan quản lý. **On-premise hoàn toàn; model không khóa vendor** — mô hình AI trong nước hoặc tự vận hành, thay thế được mà không sửa ứng dụng.

**Đã triển khai thật:** EA đã vận hành cổng kiểm soát fail-closed trong production — mặc định đóng, cấp phép từng nhóm năng lực, chặn ở lớp thực thi. Hệ thống audit log + tracing toàn luồng đã chạy qua nhiều chu kỳ release với khách hàng doanh nghiệp thật. Đây là điểm ngân hàng kiểm tra kỹ nhất — và là điểm chúng tôi mạnh nhất.

---

## 4. Output: hai sản phẩm đã có thật, đang chạy thật

Đề xuất này không khởi động từ trang giấy trắng. Hai nền tảng dưới đây đã được xây dựng, vận hành qua nhiều chu kỳ release thật với khách hàng doanh nghiệp — và đã **nối thông với nhau** qua cổng tích hợp chuẩn mở (MCP) với xác thực từng người dùng.

### 4.1 Enterprise Assistant (EA) — "bộ não" trợ lý

*Trợ lý AI cho mỗi cán bộ — mặt tiền mà người dùng tiếp xúc hàng ngày.*

| Điểm nổi bật | Chi tiết |
|---|---|
| Agent runtime tự điều phối | AI tự nhận diện ý định, tự chọn công cụ — đã vận hành 13 nhóm năng lực / 43 công cụ |
| Cổng kiểm soát fail-closed | Mặc định đóng; cấp phép từng nhóm; chặn ở lớp thực thi — không phụ thuộc "AI tự giác" |
| Kho tri thức tự quản | Phòng ban tự thêm/sửa/xóa tài liệu ngay trên web; OCR file scan tự động; không cần IT can thiệp |
| Hỏi dữ liệu có kiểm soát | Truy vấn dataset/DWH bằng tiếng Việt, chỉ-đọc, giới hạn cứng, gắn thời điểm dữ liệu |
| Phân tầng quyền theo chức danh | Gói năng lực theo từng nhóm người dùng — kiểm tra thật ở lớp thực thi |
| Trợ lý làm việc thay người | Soạn nháp theo mẫu, quản lý việc, biên bản họp từ ghi âm (STT), transcript trực tiếp |
| Quản trị & tuân thủ | Audit log, tracing từng luồng AI, quy tắc hành vi AI, prompt phòng vệ — cấu hình trên web |
| On-premise | 1 triển khai = 1 tổ chức, dữ liệu không rời hạ tầng; model hoán đổi được |

### 4.2 PowerUp — "kho dữ liệu & tri thức + engine"

*Nền tảng quản trị dữ liệu và phân tích AI — nơi giữ tài sản dữ liệu của tổ chức.*

| Điểm nổi bật | Chi tiết |
|---|---|
| Quản trị dữ liệu phân quyền chi tiết | Phân quyền tới từng thư mục, từng bảng dữ liệu; danh mục nguồn CSDL ngoài; nhật ký thao tác đầy đủ |
| Pipeline tri thức sâu | Vector database + hybrid search + reranker + OCR (hỗ trợ GPU); nhận diện header bảng biểu trong tài liệu |
| Engine nghiệp vụ tài chính | Đối soát và so khớp giao dịch ngân hàng (788 dòng mã đối soát đã chạy thật), so sánh kỳ, sinh báo cáo từ bảng dữ liệu |
| API chuẩn ngành | Endpoint tương thích OpenAI cho hệ thống ngoài — kênh tích hợp đã chứng minh |
| Multi-tenant | Cách ly cấu hình và dữ liệu theo đơn vị — sẵn sàng nếu ngân hàng tách theo khối/công ty con |
| Đa kênh | Web người dùng, web quản trị, ứng dụng di động |

### 4.3 Hai sản phẩm — một nền tảng

```
        Cán bộ ngân hàng
              │ hỏi bằng tiếng Việt
              ▼
   ┌─────────────────────┐
   │  Enterprise         │  agent điều phối · cổng kiểm soát fail-closed
   │  Assistant          │  phân quyền theo chức danh · audit + tracing
   └─────────┬───────────┘
             │ cổng tích hợp chuẩn MCP (đã chạy thật)
             ▼
   ┌─────────────────────┐
   │  PowerUp            │  kho dữ liệu phân quyền · tri thức RAG sâu
   │                     │  engine tính toán & đối soát · API chuẩn
   └─────────┬───────────┘
             ▼
   Dữ liệu nghiệp vụ / DWH · Kho văn bản & quy định · Hệ thống ngân hàng
```

- **EA là não và mặt tiền:** nơi cán bộ hỏi, nơi kiểm soát quyền, nơi audit.
- **PowerUp là kho và tay:** nơi giữ dữ liệu có quản trị, nơi tri thức được nạp và truy xuất chính xác, nơi tính toán diễn ra.
- Cầu nối hai hệ đã vận hành thật — không phải thiết kế trên giấy.

---

## 5. Showcase — bốn kịch bản trực tiếp trên bài toán của ngân hàng

*Kịch bản minh họa theo năng lực đang có của hệ thống; dữ liệu trong demo POC sẽ là dữ liệu thật (đã ẩn danh) do ngân hàng cung cấp.*

### Kịch bản 1 — Truy vấn đa nguồn + đối chiếu quy định
**Hỏi:** *"So sánh dư nợ theo ngành 3 chi nhánh Q3 với Q2, đối chiếu trần tăng trưởng tín dụng hiện hành."*
**Hệ thống làm gì:** (1) truy vấn DWH lấy số liệu 2 kỳ → (2) truy xuất văn bản quy định trần tăng trưởng, đúng phiên bản còn hiệu lực → (3) engine tính chênh lệch và so ngưỡng → (4) tổng hợp thành bảng + nhận xét.
**Nhận được:** bảng số liệu 2 kỳ có thời điểm dữ liệu, trích dẫn văn bản (số hiệu + điều khoản), kết luận so ngưỡng có căn cứ.
**Trước đây:** mở 2–3 hệ thống + tìm văn bản + Excel — hàng chục phút đến vài giờ.

### Kịch bản 2 — Tri thức quy trình có trích dẫn
**Hỏi:** *"Thủ tục cho vay doanh nghiệp nhỏ cần những chứng từ gì theo quy định mới nhất?"*
**Hệ thống làm gì:** truy xuất kho tri thức, lọc theo văn bản còn hiệu lực, xếp hạng lại đoạn liên quan nhất.
**Nhận được:** danh sách chứng từ kèm trích dẫn số hiệu văn bản + điều khoản; nếu câu hỏi chỉ định thời gian ("năm 2025"), trả đúng phiên bản hiệu lực tại mốc đó.

### Kịch bản 3 — Suy luận tình huống trên hồ sơ
**Hỏi:** *"Hồ sơ vay của khách hàng X còn thiếu chứng từ gì so với quy định cho vay trung dài hạn?"*
**Hệ thống làm gì:** (1) truy vấn hệ thống hồ sơ/dữ liệu khoản vay → (2) truy xuất danh mục chứng từ bắt buộc theo quy định → (3) đối chiếu, liệt kê thiếu sót.
**Nhận được:** danh sách thiếu cụ thể + căn cứ từng mục — cán bộ thẩm định không phải tự dò quy trình.

### Kịch bản 4 — Báo cáo ad-hoc cho lãnh đạo
**Hỏi:** *"Tổng hợp tỷ lệ nợ xấu theo nhóm ngành 6 tháng gần nhất, vẽ biểu đồ."*
**Hệ thống làm gì:** truy vấn dữ liệu nhiều kỳ → engine tính tỷ lệ → dựng biểu đồ dạng artifact bên cạnh chat, có thể kéo giãn, xuất dùng ngay.
**Nhận được:** biểu đồ + bảng số liệu gốc có nguồn — báo cáo ban điều hành trong vài phút thay vì vài ngày chờ lập.

---

## 6. Vì sao là chúng tôi

1. **Đã chạy thật, không demo PowerPoint.** Hai nền tảng trên đang vận hành production với khách hàng doanh nghiệp thật — hàng trăm thay đổi qua chu kỳ release, hệ thống audit nội bộ đầy đủ. Engine đối soát giao dịch ngân hàng của PowerUp là bằng chứng chúng tôi đã làm bài toán "tiền bạc" thật, không chỉ chat.
2. **An toàn là thiết kế gốc.** Fail-closed, cổng kiểm soát độc lập, phân tầng quyền ở lớp thực thi, audit + tracing — đã enforce thật, không phải cam kết tương lai. Đây là những điểm ngân hàng kiểm tra kỹ nhất — và là điểm chúng tôi mạnh nhất.
3. **Không khóa vendor ở bất kỳ tầng nào.** Dữ liệu xuất được, mô hình thay được (dịch vụ AI trong nước hoặc self-host), thành phần chuẩn mở (MCP) — ngân hàng giữ quyền chủ động dài hạn.
4. **On-premise đúng chuẩn ngân hàng.** Một triển khai một ngân hàng, dữ liệu không rời hạ tầng, có sổ tay triển khai–vận hành–backup đã chuẩn hóa qua nhiều môi trường thật.
5. **Con đường tăng trưởng rõ.** Sau chatbot nội bộ, cùng nền tảng mở rộng sang trợ lý AI khách hàng (kho tri thức có quản lý hiệu lực văn bản) và AI kiểm soát quy trình (kiểm soát–cảnh báo, không chạm giao dịch) — không phải xây lại từ đầu.

---

## 7. Kết luận & đề xuất

**Bài toán chatbot AI nội bộ của ngân hàng — trả lời câu hỏi độ phức tạp cao từ nhiều nguồn, có suy luận và tính toán — đòi hỏi một nền tảng AI doanh nghiệp, không phải một chatbot.** Nền tảng đó phải truy vấn được dữ liệu thật qua cổng có kiểm soát, đọc đúng quy định hiện hành có trích dẫn, tính toán bằng engine tách biệt, phân quyền theo chức danh và chứng minh được mọi câu trả lời qua audit.

**Chúng tôi đề xuất: triển khai Chatbot AI nội bộ trên nền tảng EA + PowerUp** — hai sản phẩm đã có thật, đã chạy thật, đã nối thông với nhau, với toàn bộ cơ chế an toàn mà ngân hàng yêu cầu.

**Đề xuất bước tiếp theo — POC 8–10 tuần:**

| Giai đoạn | Nội dung | Kết quả nghiệm thu |
|---|---|---|
| Tuần 1–2 | Chốt phạm vi: 2–3 nguồn dữ liệu + nhóm tài liệu quy định ưu tiên; benchmark model tiếng Việt tài chính; dựng hạ tầng on-prem pilot | Ký xác nhận phạm vi + tiêu chí nghiệm thu |
| Tuần 3–6 | Triển khai nền tảng: nạp kho quy định (OCR scan chạy thật), kết nối nguồn dữ liệu read-only, phân quyền theo chức danh, audit + tracing | Trợ lý trả lời được kịch bản thực tế do ngân hàng đặt ra |
| Tuần 7–8 | UAT với 1 phòng ban đầu tiên, đo chất lượng trên bộ câu hỏi vàng | ≥95% câu trả lời có nguồn đúng; nghiệm thu POC |
| Sau POC | Đánh giá mở rộng: thêm nguồn dữ liệu, thêm nhóm người dùng, lộ trình 3–6 tháng cho toàn lực lượng | Kế hoạch triển khai chính thức |

Chúng tôi sẵn sàng trình diễn trực tiếp (live demo) bốn kịch bản showcase tại buổi làm việc — trên dữ liệu mẫu chuẩn bị trước, và cam kết chuyển sang dữ liệu thật (ẩn danh) của ngân hàng ngay trong POC.

---

*Phụ lục theo yêu cầu: đặc tả kỹ thuật kiến trúc, tài liệu an toàn thông tin, hồ sơ năng lực và các triển khai tham chiếu — cung cấp trong buổi làm việc trực tiếp.*
