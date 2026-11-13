# Product Showcase
# Chatbot AI nội bộ cho ngân hàng, doanh nghiệp lớn và tổ chức tập đoàn: từ bài toán đến giải pháp

> **Người viết:** Hạ Vy
> **Loại:** Pitch / showcase sản phẩm gửi khách hàng
> **Ngày:** 12/10/2026
> **Sản phẩm giới thiệu:** Enterprise Assistant (EA) & PowerUp — hai nền tảng AI doanh nghiệp đã triển khai thật
> **Bài toán trọng tâm:** Trợ lý AI nội bộ — truy vấn dữ liệu, trả lời câu hỏi phức tạp từ nhiều nguồn, suy luận, tính toán

---

## 1. Bài toán: những câu hỏi "khó" hàng ngày của tổ chức

Mỗi ngày, hàng nghìn câu hỏi phát sinh bên trong ngân hàng, doanh nghiệp lớn và tổ chức tập đoàn. Phần lớn những câu hỏi có giá trị nhất lại là những câu khó nhất:

> *"So sánh dư nợ tín dụng theo ngành của 3 chi nhánh quý này với quý trước, và đối chiếu với trần tăng trưởng tín dụng theo quy định hiện hành."* *(Ngân hàng)*

> *"Hồ sơ cho vay doanh nghiệp nhỏ cần đủ những chứng từ gì theo quy định mới nhất? Hồ sơ khách hàng X đang thiếu gì?"* *(Ngân hàng)*

> *"Tổng hợp tỷ lệ nợ xấu theo nhóm ngành 6 tháng gần nhất, lập thành biểu đồ gửi Ban điều hành."* *(Ngân hàng)*

> *"So sánh doanh thu theo dòng sản phẩm của 3 chi nhánh quý này với quý trước, và đối chiếu với chỉ tiêu được duyệt."* *(Doanh nghiệp lớn)*

> *"Hợp đồng với nhà cung cấp X còn thiếu điều khoản gì so với chính sách mua hàng hiện hành?"* *(Doanh nghiệp lớn)*

> *"Tổng hợp chi phí vận hành theo phòng ban 6 tháng gần nhất, lập biểu đồ gửi Ban điều hành."* *(Tổ chức tập đoàn)*

Đặc điểm chung của những câu hỏi này: không nằm gọn trong một hệ thống nào cả. Muốn trả lời, cán bộ phải mở nhiều hệ thống cùng lúc: dữ liệu nằm ở hệ thống nghiệp vụ, DWH hoặc ERP; quy định nằm ở kho văn bản; công thức tính nằm trong đầu chuyên gia. Rồi họ tự ghép tất cả lại bằng Excel. Mỗi câu hỏi kiểu này tiêu tốn từ vài chục phút đến vài giờ, và kết quả phụ thuộc vào người tìm.

Câu hỏi đặt ra: AI có thể làm thay phần việc đó nhanh hơn, nhất quán hơn, và vẫn nằm trong tầm kiểm soát không?

---

## 2. Vì sao chatbot "thông thường" không giải được

| Yêu cầu thực tế | Chatbot phổ thông (ChatGPT-style) | Nền tảng AI doanh nghiệp đúng chuẩn |
|---|---|---|
| Trả lời từ **dữ liệu thật** của tổ chức | Không truy cập được, hoặc phải tự ghép nối | Truy vấn qua cổng dữ liệu có phân quyền |
| Trả lời theo **quy định hiện hành** | Không biết văn bản nội bộ; dễ trả lời theo dữ liệu quá khứ của model | RAG kho tri thức nội bộ, đúng phiên bản hiệu lực, có trích dẫn |
| **Tính toán chính xác** | LLM "đoán" số, sai lặng lẽ | Engine tính toán tách biệt, kết quả kiểm chứng được |
| **Phân quyền** theo vai trò | Không có, ai hỏi cũng nhận cùng câu trả lời | Phân tầng quyền ở cả giao diện và lớp thực thi |
| **Kiểm chứng & audit** | Không truy vết được | Mọi câu trả lời có nguồn, mọi hành động có nhật ký |
| Chạy **on-premise** | Cloud công cộng — không thể chấp nhận với dữ liệu nhạy cảm của tổ chức | Triển khai hoàn toàn trong hạ tầng tổ chức |

Tóm lại, tổ chức cần một trợ lý biết đọc dữ liệu và quy định của chính mình, tính đúng số, hoạt động đúng phạm vi được phép, và chứng minh được tất cả điều đó.

---

## 3. Phương án kỹ thuật: bốn năng lực lõi

### 3.0 Tại sao "truy vấn đa nguồn + suy luận" là bài toán thực sự khó

Google tìm được mọi thứ trên internet, nhưng AI doanh nghiệp lại khó khăn khi tra cứu dữ liệu đa nguồn nội bộ. Không phải vì thiếu mô hình ngôn ngữ, mà vì hai bài toán khác nhau về bản chất:

| | Google / internet | Dữ liệu nội bộ tổ chức |
|---|---|---|
| **Dữ liệu** | Công khai, đã được crawl và index sẵn | Phân tán trên DWH, CSDL nghiệp vụ, kho văn bản, file scan, chưa từng được tổ chức cho AI |
| **Ngôn ngữ** | Từ khóa đồng nhất | Thuật ngữ nội bộ, viết tắt, tên bảng, mã phòng ban, không ai gán nhãn cho AI |
| **Quyền** | Ai cũng xem được | Phân quyền theo chức danh, phòng ban, đối tượng khách hàng — AI phải tôn trọng đúng |
| **Thời điểm** | Trang web cũ là trang web cũ | Quy định thay đổi theo thời gian, AI phải biết "hiện hành" là phiên bản nào |
| **Tính toán** | Không có | Số liệu phải tính chính xác tuyệt đối, không được "gần đúng" |
| **Trách nhiệm** | Không ai kiểm tra | Mọi câu trả lời phải truy vết được nguồn, phục vụ kiểm toán |

**Bài toán không phải "tìm kiếm", mà là "hiểu đúng ngữ cảnh doanh nghiệp, truy xuất đúng nguồn, tính đúng, và chứng minh được".** Đây là lý do phần lớn các thử nghiệm AI trong doanh nghiệp dừng lại ở demo: họ giải quyết phần dễ (chat) và bỏ qua phần khó (truy vấn đa nguồn có kiểm soát, suy luận có căn cứ).

Kiến trúc của chúng tôi được thiết kế quanh đúng bốn từ khóa trong yêu cầu: truy vấn, đa nguồn, suy luận, tính toán. Mỗi năng lực dưới đây đều đã được triển khai và vận hành thật.

### 3.1 TRUY VẤN: hỏi dữ liệu bằng tiếng Việt, qua cổng có kiểm soát

**Bài toán con:** Cán bộ không biết SQL, không biết tên bảng, không biết dữ liệu nằm ở đâu; họ chỉ có câu hỏi nghiệp vụ. Ngược lại, để AI tự do viết SQL trên CSDL của tổ chức là điều không thể chấp nhận: một lỗi logic là đủ để lộ dữ liệu nhạy cảm hoặc trả kết quả sai.

**Giải pháp:** Cán bộ hỏi bằng câu tự nhiên: *"Liệt kê các khoản vay SME đến hạn trong 30 ngày tới theo chi nhánh."* Agent phân tích câu hỏi, tự chọn nguồn và cách truy vấn, nhưng không được tự do viết SQL tùy ý trên nguồn nhạy cảm. Mọi truy vấn đi qua lớp kiểm soát: tham số hóa, chỉ-đọc, giới hạn số dòng, gắn nhãn thời điểm dữ liệu lên kết quả. Mỗi nguồn dữ liệu được đăng ký tường minh (đọc được gì, ai được đọc), như một danh mục chứ không phải kết nối tự do.

**Đã triển khai thật:** EA đã chạy module truy vấn dữ liệu có kiểm soát với phân quyền theo chức danh: nhân viên chỉ thấy dữ liệu chi nhánh của mình, quản lý thấy được tổng hợp nhiều chi nhánh. PowerUp cung cấp lớp đăng ký nguồn dữ liệu với phân quyền tới từng bảng, từng thư mục.

### 3.2 ĐA NGUỒN: dữ liệu, văn bản, hệ thống trong cùng một câu trả lời

**Bài toán con:** Câu hỏi của tổ chức hiếm khi chỉ cần một nguồn. "So sánh dư nợ theo ngành 3 chi nhánh Q3 với Q2, đối chiếu trần tăng trưởng tín dụng hiện hành" cần số liệu từ DWH và văn bản quy định cùng lúc. Phần lớn giải pháp RAG chỉ làm được một trong hai: hoặc tìm kiếm trên văn bản, hoặc truy vấn SQL trên bảng. Ghép cả hai lại một cách có kiểm soát là phần ít hệ thống làm được.

**Giải pháp:** Tri thức cấu trúc (bảng số liệu, CSDL nghiệp vụ, DWH) và tri thức phi cấu trúc (thông tư, quy định, quy trình, biểu phí, file scan) nằm chung một nền tảng dữ liệu–tri thức. Một câu trả lời có thể kéo số liệu thực tế và trích dẫn điều khoản văn bản cùng lúc, và cả hai đều truy vết được nguồn. Hệ thống nạp tài liệu đa định dạng (PDF, Word, ảnh scan) với OCR tự động, nhận diện cấu trúc bảng biểu trong tài liệu, đúng đặc thù văn bản tài chính như biểu phí, bảng điều kiện. Truy xuất lai (hybrid search) kết hợp xếp hạng lại (reranker) giúp tìm đúng đoạn cần thiết trong kho hàng nghìn trang.

**Đã triển khai thật:** PowerUp đã xây dựng và vận hành pipeline tri thức với hybrid search (vector + keyword), reranker và OCR chạy GPU, xử lý tốt văn bản đặc thù như biểu phí dạng bảng, thông tư dạng scan. EA nối vào pipeline này qua cổng MCP, để agent truy xuất cả dữ liệu cấu trúc và phi cấu trúc trong cùng một luồng hội thoại.

### 3.3 SUY LUẬN: ba tầng, và tầng khó nhất không phải tìm kiếm

**Bài toán con:** Câu hỏi phức tạp không có câu trả lời sẵn trong một tài liệu. "Hồ sơ vay của khách hàng X còn thiếu chứng từ gì so với quy định cho vay trung dài hạn?" cần truy vấn hệ thống hồ sơ, truy xuất danh mục chứng từ bắt buộc, rồi đối chiếu và lập kế hoạch hành động. Không có cây luồng cứng nào định nghĩa trước được; phải suy luận động dựa trên ngữ cảnh câu hỏi.

**Ba tầng của bài toán — và tầng nào mới là tầng khó:**

| Tầng | Bản chất | Thực trạng phổ biến |
|---|---|---|
| **1. TÌM** | Khớp từ khóa hoặc khớp ngữ nghĩa (semantic), trả về đoạn văn bản liên quan | Phần lớn giải pháp RAG dừng ở đây |
| **2. TỔNG HỢP** | Gom nhiều nguồn, nhiều phiên bản văn bản, viết lại thành một câu trả lời mạch lạc | Khó hơn, nhưng vẫn là "đọc và gom" |
| **3. LÝ LUẬN / ÁP DỤNG** | Từ quy định chung + dữ kiện cụ thể → kết luận cho **tình huống này** | Tầng quyết định, và không phải bài toán tìm kiếm |

Tầng 1 và 2 trả lời câu hỏi "quy định nói gì?". Tầng 3 trả lời câu hỏi "tình huống của tôi thì thế nào?". Hai câu hỏi này khác nhau về bản chất.

**Ví dụ: "Khách hàng X có vi phạm điều khoản vay hay không?"**

Câu hỏi này không thể trả lời bằng tra cứu, dù tra cứu giỏi đến đâu. Muốn trả lời phải đi qua một chuỗi lý luận:

1. **Xác định điều khoản nào áp dụng** — hợp đồng nào, phiên bản điều khoản nào, tại thời điểm nào còn hiệu lực. Đây chính là lớp "chọn luật", tương tự bài toán pháp luật có nghị định thay đổi theo thời gian.
2. **Phân rã điều khoản thành các điều kiện cấu thành** — nghĩa vụ trả nợ đúng hạn, duy trì tỷ lệ tài sản bảo đảm, mục đích sử dụng vốn đúng cam kết, nghĩa vụ cung cấp thông tin.
3. **Gắn dữ kiện thực tế của khách hàng X vào từng điều kiện** — lịch sử thanh toán, dư nợ, giá trị tài sản bảo đảm hiện tại, mục đích giải ngân thực tế.
4. **Kiểm tra từng điều kiện**, kể cả các khái niệm mở trong văn bản như "bất khả kháng", "trọng yếu", "hợp lý"; nêu rõ chỗ nào còn phải phán đoán.
5. **Kết luận kèm chuỗi lập luận** — điều kiện nào thoả, điều kiện nào không, điều kiện nào chưa đủ dữ kiện để kết luận.

Không có tầng 3, hệ thống chỉ trả về một đoạn điều khoản và để cán bộ tự làm nốt phần khó nhất. Đó là lý do nhiều giải pháp RAG trông rất thông minh nhưng không gánh được việc thật của tổ chức.

**Giải pháp:** Mỗi câu hỏi được agent phân tích và lập kế hoạch: cần nguồn nào, gọi công cụ nào theo thứ tự nào, thiếu dữ liệu thì hỏi lại hay báo thiếu. Kết luận trong câu trả lời bắt buộc gắn căn cứ: số liệu từ nguồn nào, văn bản số hiệu nào, điều khoản nào. Không có căn cứ thì câu trả lời từ chối có kiểm soát, không bịa. Bộ nhớ hội thoại theo từng cán bộ giúp trợ lý nhớ ngữ cảnh làm việc lâu dài và xử lý câu hỏi nối tiếp tự nhiên.

Nói thẳng: đây là tầng rủi ro cao nhất, vì một kết luận sai ở đây có hệ quả pháp lý và tài chính. Vì vậy chúng tôi thiết kế tầng này có kiểm soát, chứ không để AI "phán":

- **Lý luận theo cấu trúc**, không sinh văn xuôi tự do: điều kiện, dữ kiện, kết luận, để kiểm chứng lại được từng bước.
- **Thiếu dữ kiện thì nêu rõ là thiếu**, không suy diễn lấp chỗ trống.
- **AI đưa ra đánh giá và chuỗi lập luận; con người quyết định.** Hệ thống không thay phán quyết của cán bộ, nó rút ngắn thời gian tìm và lập luận, và làm phần đó minh bạch.
- **Toàn bộ chuỗi lập luận được audit**, kiểm toán lại được vì sao hệ thống đi đến kết luận đó.

**Đã triển khai thật:** EA đã vận hành agent runtime tự điều phối với 13 nhóm năng lực và 43 công cụ: agent tự nhận diện ý định, tự chọn công cụ, tự lập kế hoạch truy vấn nhiều nguồn. Hệ thống audit ghi nhận toàn bộ chuỗi suy luận, từ câu hỏi, kế hoạch, công cụ gọi, kết quả trung gian đến câu trả lời cuối. Đây là điều kiện tiên quyết để một tổ chức chấp nhận AI trong môi trường có kiểm toán. Phần kiến trúc của tầng lý luận (lập kế hoạch, gắn căn cứ, từ chối có kiểm soát) đã có sẵn; phần hiệu chỉnh theo nghiệp vụ cụ thể sẽ làm cùng chuyên gia của tổ chức trong POC. Chúng tôi nói rõ điều này thay vì hứa một hệ thống tự phán quyết.

### 3.4 TÍNH TOÁN: engine nghiệp vụ tách biệt LLM

**Bài toán con:** LLM "đoán" số, đôi khi đúng, đôi khi sai mà không ai nhận ra. Trong tổ chức, một con số sai trong báo cáo tài chính có thể dẫn tới quyết định sai. Không thể chấp nhận "gần đúng" khi nói về tiền.

**Giải pháp:** Mọi phép tính nghiệp vụ (so sánh kỳ, tỷ lệ, ngưỡng, quy đổi) chạy ở engine tách biệt với mô hình ngôn ngữ, chính xác tuyệt đối, không "ảo giác số liệu". LLM chỉ điều phối và giải thích kết quả. Đây là nguyên tắc thiết kế, không phải tùy chọn cấu hình.

**Đã triển khai thật:** PowerUp đã xây dựng engine đối soát và so khớp giao dịch tài chính (788 dòng mã đối soát đã chạy thật với khách hàng), đây là bài toán "tiền bạc" thật chứ không chỉ chat. Engine tính toán tách biệt đảm bảo mọi con số trong câu trả lời đều kiểm chứng được bằng cách tái tính từ dữ liệu gốc.

### 3.5 An toàn xuyên suốt: nền móng, không phải lớp vá

**Bài toán con:** Tổ chức không thể chấp nhận AI "tự do". Mọi hành động phải có kiểm soát, mọi câu trả lời phải truy vết được, mọi quyền truy cập phải phân tầng. Đây không phải tính năng thêm vào sau, mà là điều kiện để AI được phép chạy trong tổ chức.

**Giải pháp:** Fail-closed: AI mặc định không được làm gì, từng nhóm năng lực được cấp phép tường minh, công cụ bị tắt thì trả lời y như "không tồn tại". Cổng kiểm soát độc lập đứng giữa AI và dữ liệu, chặn cả khi AI bị thao túng cố đi ra ngoài phạm vi. Phân tầng theo chức danh: nhân viên, quản lý, lãnh đạo, mỗi cấp thấy đúng công cụ và dữ liệu của mình, kiểm tra ở lớp thực thi chứ không chỉ ẩn giao diện. Audit và tracing toàn luồng: truy vết được từng câu trả lời về đúng nguồn dữ liệu và văn bản, phục vụ kiểm toán nội bộ và cơ quan quản lý. On-premise hoàn toàn, model không khóa vendor: mô hình AI trong nước hoặc tự vận hành, thay thế được mà không sửa ứng dụng.

**Đã triển khai thật:** EA đã chạy cổng kiểm soát fail-closed trong production: mặc định đóng, cấp phép từng nhóm năng lực, chặn ở lớp thực thi. Hệ thống audit log và tracing toàn luồng đã trải qua nhiều chu kỳ release với khách hàng doanh nghiệp thật. Đây là điểm khách hàng kiểm tra kỹ nhất, và cũng là điểm mạnh nhất của chúng tôi.

---

## 4. Nền tảng: hai sản phẩm đã có thật, đang chạy thật

Đề xuất này không khởi động từ trang giấy trắng. Hai nền tảng dưới đây đã được xây dựng và vận hành qua nhiều chu kỳ release thật với khách hàng doanh nghiệp, và đã nối thông với nhau qua cổng tích hợp chuẩn mở (MCP) với xác thực từng người dùng.

### 4.1 Enterprise Assistant (EA) — "bộ não" trợ lý

*Trợ lý AI cho mỗi cán bộ — mặt tiền mà người dùng tiếp xúc hàng ngày.*

| Điểm nổi bật | Chi tiết |
|---|---|
| Agent runtime tự điều phối | AI tự nhận diện ý định, tự chọn công cụ — đã vận hành 13 nhóm năng lực / 43 công cụ |
| Cổng kiểm soát fail-closed | Mặc định đóng; cấp phép từng nhóm; chặn ở lớp thực thi, không dựa vào "AI tự giác" |
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
| Engine nghiệp vụ tài chính | Đối soát và so khớp giao dịch tài chính (788 dòng mã đối soát đã chạy thật), so sánh kỳ, sinh báo cáo từ bảng dữ liệu |
| API chuẩn ngành | Endpoint tương thích OpenAI cho hệ thống ngoài — kênh tích hợp đã chứng minh |
| Multi-tenant | Cách ly cấu hình và dữ liệu theo đơn vị — sẵn sàng nếu tổ chức tách theo khối/công ty con |
| Đa kênh | Web người dùng, web quản trị, ứng dụng di động |

### 4.3 Hai sản phẩm — một nền tảng

```
        Cán bộ tổ chức
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
   Dữ liệu nghiệp vụ / DWH / ERP · Kho văn bản & quy định · Hệ thống tổ chức
```

- **EA là bộ não và mặt tiền:** nơi cán bộ hỏi, nơi kiểm soát quyền, nơi ghi audit.
- **PowerUp là kho và đôi tay:** nơi giữ dữ liệu có quản trị, nơi tri thức được nạp và truy xuất chính xác, nơi tính toán diễn ra.
- Cầu nối giữa hai hệ đã vận hành thật.

---

## 5. Showcase — bốn kịch bản trực tiếp trên bài toán của tổ chức

*Kịch bản minh họa theo năng lực đang có của hệ thống; dữ liệu trong demo POC sẽ là dữ liệu thật (đã ẩn danh) do tổ chức cung cấp.*

### Kịch bản 1 — Truy vấn đa nguồn + đối chiếu quy định
**Hỏi:** *"So sánh dư nợ theo ngành 3 chi nhánh Q3 với Q2, đối chiếu trần tăng trưởng tín dụng hiện hành."*
**Hệ thống làm gì:** (1) truy vấn DWH lấy số liệu 2 kỳ → (2) truy xuất văn bản quy định trần tăng trưởng, đúng phiên bản còn hiệu lực → (3) engine tính chênh lệch và so ngưỡng → (4) tổng hợp thành bảng + nhận xét.
**Nhận được:** bảng số liệu 2 kỳ có thời điểm dữ liệu, trích dẫn văn bản (số hiệu + điều khoản), kết luận so ngưỡng có căn cứ.
**Trước đây:** mở 2–3 hệ thống, tìm văn bản, ghép Excel — hàng chục phút đến vài giờ.

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
**Hệ thống làm gì:** truy vấn dữ liệu nhiều kỳ → engine tính tỷ lệ → dựng biểu đồ dạng khung tương tác bên cạnh chat, kéo giãn và xuất dùng ngay.
**Nhận được:** biểu đồ + bảng số liệu gốc có nguồn — báo cáo ban điều hành trong vài phút thay vì vài ngày chờ lập.

---

## 6. Vì sao là chúng tôi

1. **Đã chạy thật, không phải demo PowerPoint.** Hai nền tảng đang vận hành production với khách hàng doanh nghiệp thật, qua hàng trăm thay đổi trong các chu kỳ release, với hệ thống audit nội bộ đầy đủ. Engine đối soát giao dịch ngân hàng của PowerUp là bằng chứng chúng tôi đã làm bài toán "tiền bạc" thật, không chỉ chat.
2. **An toàn là thiết kế gốc.** Fail-closed, cổng kiểm soát độc lập, phân tầng quyền ở lớp thực thi, audit và tracing — tất cả đã chạy thật chứ không phải cam kết tương lai. Đây là những điểm khách hàng kiểm tra kỹ nhất, và là điểm mạnh nhất của chúng tôi.
3. **Không khóa vendor ở bất kỳ tầng nào.** Dữ liệu xuất được, mô hình thay được (dịch vụ AI trong nước hoặc tự vận hành), thành phần chuẩn mở (MCP). Tổ chức giữ quyền chủ động dài hạn.
4. **On-premise đúng chuẩn tổ chức.** Một triển khai cho một tổ chức, dữ liệu không rời hạ tầng, có sổ tay triển khai – vận hành – backup đã chuẩn hóa qua nhiều môi trường thật.
5. **Con đường tăng trưởng rõ.** Sau chatbot nội bộ, cùng nền tảng mở rộng sang trợ lý AI khách hàng (kho tri thức có quản lý hiệu lực văn bản) và AI kiểm soát quy trình (kiểm soát, cảnh báo, không chạm giao dịch), không phải xây lại từ đầu.

---

## 7. Kết luận & đề xuất

Bài toán chatbot AI nội bộ của tổ chức — trả lời câu hỏi độ phức tạp cao từ nhiều nguồn, có suy luận và tính toán — đòi hỏi một nền tảng AI doanh nghiệp, không phải một chatbot. Nền tảng đó phải truy vấn được dữ liệu thật qua cổng có kiểm soát, đọc đúng quy định hiện hành có trích dẫn, tính toán bằng engine tách biệt, phân quyền theo chức danh và chứng minh được mọi câu trả lời qua audit.

Chúng tôi đề xuất triển khai Chatbot AI nội bộ trên nền tảng EA + PowerUp: hai sản phẩm đã có thật, đã chạy thật, đã nối thông với nhau, với đầy đủ cơ chế an toàn mà tổ chức yêu cầu.

**Đề xuất bước tiếp theo — POC 8–10 tuần:**

| Giai đoạn | Nội dung | Kết quả nghiệm thu |
|---|---|---|
| Tuần 1–2 | Chốt phạm vi: 2–3 nguồn dữ liệu + nhóm tài liệu quy định ưu tiên; benchmark model tiếng Việt tài chính; dựng hạ tầng on-prem pilot | Ký xác nhận phạm vi + tiêu chí nghiệm thu |
| Tuần 3–6 | Triển khai nền tảng: nạp kho quy định (OCR scan chạy thật), kết nối nguồn dữ liệu read-only, phân quyền theo chức danh, audit + tracing | Trợ lý trả lời được kịch bản thực tế do tổ chức đặt ra |
| Tuần 7–8 | UAT với 1 phòng ban đầu tiên, đo chất lượng trên bộ câu hỏi vàng | ≥95% câu trả lời có nguồn đúng; nghiệm thu POC |
| Sau POC | Đánh giá mở rộng: thêm nguồn dữ liệu, thêm nhóm người dùng, lộ trình 3–6 tháng cho toàn lực lượng | Kế hoạch triển khai chính thức |

Chúng tôi sẵn sàng demo trực tiếp bốn kịch bản showcase tại buổi làm việc, trên dữ liệu mẫu chuẩn bị trước, và cam kết chuyển sang dữ liệu thật (ẩn danh) của tổ chức ngay trong POC.

---

*Phụ lục theo yêu cầu: đặc tả kỹ thuật kiến trúc, tài liệu an toàn thông tin, hồ sơ năng lực và các triển khai tham chiếu — cung cấp trong buổi làm việc trực tiếp.*
