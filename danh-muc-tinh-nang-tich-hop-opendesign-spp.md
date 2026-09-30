# Danh mục tính năng — Tích hợp OpenDesign vào BSM Superpower (SPP)

**Tài liệu phục vụ:** Hồ sơ thầu / Hồ sơ năng lực
**Hệ thống:** BSM Superpower (SPP) — Mã dự án: Tổng hợp
**Ngày:** 30/09/2026
**Nguồn:** Báo cáo đánh giá khả thi "Tích hợp OpenDesign (nexu-io/open-design) vào SPP", phiên bản 3, 24/09/2026

---

## 0. Chú thích cách đọc danh mục

Danh mục được chia theo **3 mức độ cam kết**, dùng để đối chiếu khi lập Hồ sơ thầu:

| Mã | Ký hiệu | Ý nghĩa |
|---|---|---|
| **F** | Tính năng có sẵn | OpenDesign đã có và đã được đối chiếu mã nguồn/tài liệu; tích hợp không cần phát triển lại |
| **I** | Tính năng tích hợp | SPP phải xây dựng/nối mới (phần lớn công việc thuộc gói thầu này) |
| **P** | Tính năng cần PoC | Chưa xác minh được, phụ thuộc kết quả kiểm thử giai đoạn PoC (mục 8) |

Cột "Nguồn" trỏ về mục tương ứng của báo cáo đánh giá khả thi đã ban hành kèm theo.

---

## 1. Nhóm A — Truy cập và điều hướng trong SPP

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| A-01 | Mục "Thiết kế" trong workspace | I | Bổ sung một mục chức năng mới trên thanh điều hướng chính của SPP, cho phép người dùng truy cập màn hình thiết kế mà không rời khỏi hệ thống, giữ nguyên bố cục khung làm việc chung. | §4.4, §6.5 |
| A-02 | Truy cập theo workspace đang mở | I | Màn hình thiết kế gắn với đúng workspace mà người dùng đang làm việc; đổi workspace sẽ đổi nội dung thiết kế tương ứng, không trộn lẫn dữ liệu giữa các workspace. | §4.1, §2 |
| A-03 | Kiểm soát phân quyền theo vai trò thành viên | I | Chỉ thành viên có quyền trong workspace được truy cập màn hình thiết kế; người không phải thành viên bị từ chối ở tầng ứng dụng, không phát sinh truy cập trái phép. | §4.3, §6.4 |
| A-04 | Nhúng giao diện thiết kế trong khung SPP | I | Giao diện làm việc của OpenDesign hiển thị trọn vẹn trong vùng nội dung của SPP, phản hồi theo kích thước màn hình, có trạng thái tải và trạng thái lỗi hiển thị rõ ràng. | §6.5, §4.4 |

## 2. Nhóm B — Gắn kết và cô lập phạm vi làm việc (điểm cốt lõi của yêu cầu)

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| B-01 | Ghim dự án thiết kế vào workspace | I | Khi người dùng mở màn hình thiết kế lần đầu, hệ thống tự động liên kết dự án thiết kế với đúng thư mục dữ liệu của workspace, không yêu cầu người dùng tự chọn đường dẫn. | §6.3 |
| B-02 | Hợp đồng workspace theo chuẩn dành cho bên điều phối | F | Sử dụng cơ chế hợp đồng workspace chính thức của OpenDesign (loại scratch, quyền ghi dữ liệu do bên ngoài quản lý) để SPP giữ quyền kiểm soát vòng đời mã nguồn. | §3.2 |
| B-03 | Chặn truy cập thư mục ngoài workspace | F | Thiết kế chỉ được thao tác trên thư mục của workspace. Mọi yêu cầu chỉ tới thư mục khác bị từ chối tự động kèm thông báo lỗi rõ ràng; cơ chế này kiểm tra cả đường dẫn gián tiếp qua liên kết. | §3.3, §5 |
| B-04 | Chống truy cập vùng dữ liệu nhạy cảm của hệ thống | F | Hệ thống chủ động từ chối việc gắn dự án vào các thư mục hệ thống, thư mục cấu hình và thư mục chứa thông tin đăng nhập, kể cả khi được mở bằng đường dẫn liên kết. | §3.2, §3.3 |
| B-05 | Cố định thư mục làm việc sau khi liên kết | F | Sau khi dự án được liên kết, thư mục làm việc không thể bị thay đổi ngầm bởi thao tác khác trong giao diện. | §3.2 |
| B-06 | Tách biệt cấu hình và dữ liệu tạm của tiến trình thiết kế | F | Khi chạy trong chế độ cô lập, toàn bộ cấu hình, bộ nhớ đệm, thư mục tạm và thư mục dữ liệu của tiến trình trợ giúp chỉ nằm trong vùng dữ liệu riêng đã cấp; không đọc hoặc ghi vào cấu hình hệ thống bên ngoài. | §3.3, §6.8 |

## 3. Nhóm C — Giao diện và quy trình thiết kế

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| C-01 | Trò chuyện với trợ lý thiết kế theo dự án | F | Người dùng trao đổi yêu cầu thiết kế bằng ngôn ngữ tự nhiên trong phạm vi dự án đang mở; phản hồi được trả về liên tục thay vì chờ toàn bộ kết quả. | §3.1, §3.5 |
| C-02 | Xem trước kết quả thiết kế trực tiếp | F | Xem kết quả thiết kế ngay trong giao diện, không cần tải về máy. | §6.7 |
| C-03 | Quản lý tập tin thiết kế trong dự án | F | Danh sách và mở tập tin thiết kế thuộc dự án, xem nội dung, theo dõi các tệp trung gian phát sinh trong quá trình thiết kế. | §3.2, §6.7 |
| C-04 | Tái sử dụng bộ kỹ năng thiết kế | F | Áp dụng các bộ kỹ năng thiết kế dựng sẵn cho dự án để đạt chất lượng đầu ra theo từng loại sản phẩm. | §3.2 |
| C-05 | Áp dụng hệ thống thiết kế | F | Gắn bộ quy chuẩn thiết kế vào dự án để sản phẩm đầu ra tuân thủ hệ thống màu sắc, typography và thành phần. | §3.2 |
| C-06 | Lịch sử phiên làm việc thiết kế | F | Ghi nhận mỗi lần chạy: nhận diện phiên, trạng thái kết thúc, danh sách tệp và kết quả phát sinh, vị trí nhật ký sự kiện, lỗi, phục vụ tra cứu và đối chiếu. | §3.2 |
| C-07 | Xuất bản sản phẩm thiết kế | F | Xuất kết quả ra nhiều định dạng phục vụ trình bày: bản web, tài liệu PDF, trình chiếu, video. | §6.7 |

## 4. Nhóm D — Tích hợp dữ liệu với hệ thống SPP

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| D-01 | Dùng chung kho dữ liệu với trợ lý trò chuyện của SPP | I | Tệp thiết kế tạo ra nằm trực tiếp trong thư mục workspace; trợ lý trò chuyện của SPP đọc được ngay, và ngược lại sản phẩm thiết kế tạo ra cũng xuất hiện ngay trong danh sách tệp của workspace mà không cần đồng bộ thủ công. | §4.1, §6.7 |
| D-02 | Quản lý phiên bản do SPP thực hiện | I | SPP giữ quyền commit, đẩy nhánh và phát hành; OpenDesign không tự thực hiện thao tác này, đúng theo ranh giới trách nhiệm hợp đồng workspace. | §3.2, §6.7 |
| D-03 | Cung cấp sản phẩm thiết kế qua dịch vụ tệp của SPP | I | Các tệp xuất bản được đưa vào danh mục tệp của workspace để thành viên tải về theo quyền hiện có. | §6.7 |
| D-04 | Cung cấp khóa xác thực theo từng workspace | I | Mỗi workspace có một khóa truy cập riêng do SPP sinh ra, có thời hạn, thu hồi khi môi trường được tạo lại; khóa này không truyền xuống trình duyệt. | §6.4, §6.8 |

## 5. Nhóm E — Trợ lý AI thực thi thiết kế

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| E-01 | Trợ lý AI tạo nội dung thiết kế | I | Bộ trợ lý AI chạy trong môi trường riêng của workspace, thao tác trực tiếp trên thư mục dữ liệu workspace; tích hợp sẵn trợ lý AI đang dùng cho SPP. | §3.5, §6.6, §6.2b |
| E-02 | Cấp khóa truy cập mô hình AI | I | Cấu hình khóa nhà cung cấp theo từng workspace; khóa không bị ghi ra ngoài vùng dữ liệu đã cấp. | §3.3, §3.5, §6.6 |
| E-03 | Cơ chế dự phòng khi không dựng được trợ lý AI | F | Có phương án dự phòng chạy qua lớp trung gian của OpenDesign khi không cài được trợ lý AI; giới hạn rõ: chỉ sinh nội dung văn bản, chưa thao tác được trực tiếp trên thư mục workspace. | §3.5, §6.6 |
| E-04 | Tương thích nhiều loại trợ lý AI | F | OpenDesign hỗ trợ nhiều bộ trợ lý AI qua cơ chế phát hiện theo PATH, giúp chủ đầu tư không bị khóa vào một nhà cung cấp. | §3.5 |

## 6. Nhóm F — Vận hành, giám sát và bảo mật

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| F-01 | Tự động khởi tạo môi trường thiết kế theo workspace | I | Môi trường thiết kế được tạo tự động theo mô hình mỗi workspace một môi trường cô lập đang vận hành cho trợ lý trò chuyện; có thể khởi tạo theo nhu cầu khi người dùng mở màn hình thiết kế. | §4.2, §6.2b |
| F-02 | Giám sát tình trạng hoạt động | I | Có điểm kiểm tra sức khoẻ dịch vụ thiết kế; trường hợp tiến trình dừng bất thường được phát hiện và khởi động lại tự động. | §3.1, §6.2b |
| F-03 | Quản lý tài nguyên môi trường thiết kế | I | Giới hạn bộ nhớ, số tiến trình và phân bổ tài nguyên theo thông số đã kiểm chứng; giám sát mức sử dụng thực tế. | §3.6, §6.2b |
| F-04 | Đóng gói và phát hành phiên bản môi trường thiết kế | I | Hình ảnh chạy được tạo sẵn từ mã nguồn OpenDesign đã ghim phiên bản, kèm trợ lý AI cần thiết, đảm bảo tính tái lập của môi trường. | §6.2, §6.2b, R4, R6 |
| F-05 | Quy trình nâng cấp phiên bản có kiểm soát | I | Chính sách ghim phiên bản OpenDesign, lịch nâng cấp được duyệt, kèm kiểm thử hồi quy trước khi áp dụng, do nhịp phát hành thay đổi rất nhanh từ nhà cung cấp nền tảng. | §3.6, R4 |
| F-06 | Xác thực người dùng khi truy cập màn hình thiết kế | I | Yêu cầu truy cập được kiểm tra bằng phiên đăng nhập hợp lệ của SPP kèm quyền thành viên workspace; lớp trung gian xác thực chuyển tiếp quyền truy cập sang OpenDesign mà không lộ khóa. | §6.4 |
| F-07 | Hạn chế nguồn gốc truy cập API | F | Danh sách nguồn gốc được phép gọi API của môi trường thiết kế chỉ gồm địa chỉ hệ thống SPP. | §3.4, §6.4 |
| F-08 | Môi trường thiết kế không mở ra Internet | I | Dịch vụ thiết kế chỉ hoạt động trong mạng nội bộ, không tiếp xúc trực tiếp với Internet công cộng; mọi truy cập qua SPP. | §6.8 |
| F-09 | Xử lý đồng thời và giới hạn phiên | I | Môi trường thiết kế phục vụ phiên làm việc theo giới hạn số phiên mở, không ảnh hưởng phiên trợ lý trò chuyện. | §4.2, §6.2b |
| F-10 | Nhật ký và truy vết hoạt động | I | Ghi nhận nhật ký thao tác thiết kế và lỗi phát sinh phục vụ chẩn đoán, đối chiếu khi có sự cố. | §3.2, §6.2b |

## 7. Nhóm G — Tương thích và yêu cầu phi chức năng

| Mã | Yêu cầu | Mức | Mô tả | Nguồn |
|---|---|---|---|---|
| G-01 | Không phụ thuộc dịch vụ trung gian mới | I | Hệ thống chạy được một OpenDesign cho mỗi workspace, không yêu cầu thêm hạ tầng proxy công khai cho giao diện. | §3.1, §6.5 |
| G-02 | Mức sử dụng tài nguyên thấp khi không hoạt động | F | Môi trường thiết kế tiêu thụ rất ít tài nguyên ở trạng thái rảnh, khoảng 18 đến 22 MB theo đo của nhà cung cấp. | §3.6 |
| G-03 | Tương thích nền tảng chạy | F | Yêu cầu Node.js phiên bản 24, tương thích với nền tảng đang dùng của SPP. | §3.6, §6.2b |
| G-04 | Tuân thủ giấy phép mã nguồn mở | I | OpenDesign phát hành theo giấy phép Apache-2.0; gói bàn giao giữ nguyên phần khai báo giấy phép và ghi công. | R7 |
| G-05 | Bàn giao tài liệu | I | Hồ sơ bàn giao gồm tài liệu kiến trúc, quy trình cài đặt và nâng cấp, cấu hình tham số môi trường, kịch bản kiểm thử, quy trình xử lý sự cố. | §8 |

---

## 7b. Bối cảnh bổ sung: yêu cầu thiết kế cho màn hình di động và thiết bị TV

> Mục này bổ sung theo bối cảnh khách hàng đang kỳ vọng sản phẩm thiết kế phục vụ được cả **màn hình di động** lẫn **thiết bị TV (TV box)**. Phần lớn nội dung ở đây là **sản phẩm do SPP phát triển**, không phải mô tả năng lực sẵn có của OpenDesign. Cần nói thẳng với khách hàng: nền tảng có sẵn xử lý rất tốt màn hình di động, nhưng **chưa có gì cho thiết bị TV** — đây là phần công việc phát sinh, không phải phần cấu hình.

### 7b.1 Đánh giá năng lực hiện có theo từng nền tảng

| Nền tảng | Đánh giá | Bằng chứng, đã đọc mã nguồn tag main ngày 24/09/2026 |
|---|---|---|
| Màn hình di động | **Khá mạnh, dùng được ngay** | Có hợp đồng responsive chi tiết: bắt buộc không cuộn ngang ở 360, 390, 430, 600, 768, 820, 1024, 1366, 1440, 1920 px; dùng `clamp()` và container query; vùng chạm tối thiểu 44px; phải thiết kế lại chứ không thu nhỏ bản desktop. Tại `apps/daemon/src/prompts/system.ts:1778-1780` và `prompts/core-slim.ts:338,340,416`. |
| Máy tính bảng | **Có, dùng được** | Có hợp đồng riêng, yêu cầu tạo tệp màn hình riêng, không thu phóng bản mobile. Tại `prompts/discovery.ts:230`. |
| Máy tính desktop và web | **Khá mạnh, dùng được ngay** | Tại `prompts/system.ts:301-302` và `prompts/discovery.ts:227`. |
| **Thiết bị TV** | **Chưa có năng lực nào** | Xem bảng 7b.2 bên dưới. |

### 7b.2 Khoảng trống cụ thể của OpenDesign với thiết bị TV

| Nội dung cần có | Trạng thái trong OpenDesign | Bằng chứng |
|---|---|---|
| Khái niệm nền tảng TV trong hệ thống | **Không tồn tại.** Danh sách nền tảng được công nhận chỉ gồm: ios, iphone, ipad, android, tablet, responsive, mobile app, native app, desktop app, cross-platform, multi-platform. Không có tv, không có set-top box. | `apps/daemon/src/prompts/system.ts:301-302` |
| Toàn bộ từ khóa liên quan TV: giao diện 10-foot, phím điều hướng, điều khiển từ xa, vùng quét hình, vùng an toàn, bàn phím ảo | **Không có nội dung nào.** Tìm trong toàn bộ mã nguồn `apps/daemon/src`, tài liệu `docs/`, và thư viện craft `craft/` với các từ: 10-foot, tv box, set-top, dpad, d-pad, remote control, television, overscan, safe-area, on-screen keyboard. | Không có kết quả nào |
| Con trỏ | **Chỉ có quy tắc cho chuột và bàn phím** | `craft/color.md:32` nói về hover và focus ring; `prompts/core-slim.ts:333` nói về focus ring. Không có quy tắc về vị trí con trỏ khi dùng điều khiển từ xa, không có quy tắc về việc con trỏ không cần hiển thị. |
| Bàn phím ảo | **Không có hướng dẫn nào** | `craft/form-validation.md:101` chỉ nói thuộc tính inputmode là gợi ý bàn phím ảo cho thiết bị di động, không phải cho TV. |
| Thư viện craft hiện có | 12 tệp craft dùng chung, **không có tệp nào dành cho TV** | `craft/`: accessibility-baseline, animation-discipline, anti-ai-slop, color, form-validation, laws-of-ux, rtl-and-bidi, state-coverage, typography, typography-hierarchy, typography-hierarchy-editorial |
| Khoảng cách vùng an toàn màn hình TV | **Không có** | Tìm từ khóa safe-area và overscan: không có kết quả |

### 7b.3 Ba rào cản kỹ thuật cần xử lý ngoài phạm vi gói tích hợp cơ bản

Đây là ba điểm khiến cách tiếp cận chỉ thêm bộ kỹ năng là chưa đủ. Cần nêu rõ trong hồ sơ thầu để tránh cam kết quá mức:

| Mã | Rào cản | Vì sao | Hướng xử lý đề xuất |
|---|---|---|---|
| R-TV-1 | **Danh sách nền tảng không có tv** | Hệ thống chỉ kích hoạt hợp đồng thiết kế theo nền tảng, và tv không nằm trong danh sách được công nhận. Viết một bộ kỹ năng có tên TV sẽ không tự kích hoạt được hợp đồng nền tảng. | SPP bổ sung một hợp đồng nền tảng riêng ở lớp của SPP, không sửa mã OpenDesign, rồi ánh xạ tv vào đó khi người dùng chọn nền tảng TV. |
| R-TV-2 | **Không có cơ chế kiểm chứng kết quả theo kích thước màn hình** | OpenDesign **không có** công cụ chụp màn hình hay kiểm tra hiển thị theo kích thước thật. Trường `responsive_check` trong nhật ký được ghi rõ là `not_reported`, tức là hệ thống tự nhận chưa đo được, chỉ dựa vào phần tự kiểm của trợ lý AI trong lời giải thích. | Xây bước kiểm chứng hiển thị riêng của SPP: chụp ảnh sản phẩm ở các kích thước mục tiêu gồm mobile, tablet, và TV 1920x1080 ở khoảng cách xem 3 mét; đưa kết quả trở lại làm ngữ cảnh cho lượt tiếp theo. Đây là hạng mục phát triển riêng. |
| R-TV-3 | **Quy tắc craft sẵn có xung đột với thực tế TV** | Quy tắc mặc định của nền tảng viết cho chuột và bàn phím, ví dụ quy tắc hover, quy tắc di chuột, quy tắc con trỏ. Với TV, con trỏ không tồn tại, không có hover, và khoảng cách xem xa đòi hỏi cỡ chữ và khoảng cách lớn hơn nhiều so với 44px. | Dùng chính cơ chế miễn trừ của OpenDesign: một hệ quy chuẩn thiết kế riêng cho TV có thể khai báo loại trừ các quy tắc craft không phù hợp. Xem mục 7b.4. |

### 7b.4 Đánh giá phương án dùng bộ kỹ năng, mẫu thiết kế và tài liệu tham chiếu của riêng SPP

Đây là câu hỏi trực tiếp của khách hàng. Câu trả lời: **khả thi, và là hướng đúng, nhưng cần kết hợp với hai hạng mục bổ sung bên cạnh.**

#### Những gì làm được bằng cơ chế sẵn có của OpenDesign, không cần sửa mã nền tảng

| Hạng mục | Cơ chế sẵn có | Mức khả thi |
|---|---|---|
| **Bộ kỹ năng thiết kế riêng cho TV** | OpenDesign hỗ trợ cài đặt bộ kỹ năng từ thư mục cục bộ. Cổng cài đặt là `POST /api/skills/install` với nguồn local. Bộ kỹ năng là một thư mục có tệp SKILL.md cùng các thư mục references và assets. Tại `apps/daemon/src/routes/static-resource.ts:1098-1123` và `docs/skills-protocol.md` mục 1. | **Khả thi** |
| **Tài liệu tham chiếu về đặc thù TV** | Bộ kỹ năng hỗ trợ thư mục references, là các tệp tri thức mà trợ lý AI đọc khi lập kế hoạch. Đây là chỗ đúng để đặt quy tắc về điều khiển từ xa, bàn phím ảo, con trỏ, vùng an toàn, khoảng cách xem. Tại `docs/skills-protocol.md` mục 1 và `apps/daemon/src/skills.ts:605`. | **Khả thi** |
| **Mẫu thiết kế riêng cho từng loại sản phẩm TV** | OpenDesign có sẵn danh mục 115 mẫu thiết kế và hỗ trợ thư mục mẫu riêng trong vùng dữ liệu. Tại `apps/daemon/src/server.ts:1326-1330, 1436, 1444`. | **Khả thi** |
| **Hệ quy chuẩn thiết kế riêng cho sản phẩm TV** | Hệ quy chuẩn thiết kế là một gói gồm manifest.json, DESIGN.md và tokens.css, cài được từ thư mục cục bộ qua `POST /api/design-systems/install`. Tại `docs/design-systems.md` mục 1 và `apps/daemon/src/routes/static-resource.ts:1231-1253`. | **Khả thi** |
| **Loại trừ quy tắc craft không phù hợp với TV** | Hệ quy chuẩn thiết kế khai báo được trường `craft.exemptions`, là danh sách quy tắc craft cần loại trừ. Đây là đường chính thức để thoát khỏi quy tắc viết cho chuột và bàn phím mà không cần can thiệp mã nền tảng. Tại `apps/daemon/src/design-systems/index.ts:580-615, 822-823`. Lược đồ cho phép đúng ba khoá là applies, suggested, exemptions, tại `design-systems/_schema/manifest.schema.ts:173, 298-308`. | **Khả thi** |
| **Kiểm chứng chất lượng đầu ra theo bộ quy chuẩn** | OpenDesign có cơ chế tự phê bình nhiều vòng theo bộ quy chuẩn thiết kế và quy tắc craft, chấm điểm và so sánh với ngưỡng đạt, cấu hình được bằng tham số môi trường. Tại `apps/daemon/src/critique/config.ts:19-45`. | **Khả thi** |

#### Ba giới hạn cần nói thẳng

1. **Cơ chế thêm quy tắc không tạo ra hợp đồng nền tảng mới.** Bộ kỹ năng và tài liệu tham chiếu giúp trợ lý AI tuân thủ đặc thù TV, nhưng hệ thống vẫn không có khái niệm dự án này nhắm vào TV để kích hoạt đúng nhánh xử lý. Cần hạng mục H-01.
2. **Không có gì kiểm chứng kết quả thực tế trên màn hình.** Quy tắc viết trong tài liệu là quy tắc trình thành lời, không phải quy tắc được đo. Cần hạng mục H-02.
3. **Thư viện craft không mở rộng được từ bên ngoài.** Craft chỉ đọc từ một thư mục cố định trong hình ảnh chạy, tại `apps/daemon/src/server.ts:1331-1335`, và chỉ có cổng đọc `GET /api/craft`, không có cổng ghi từ bên ngoài. Vì vậy quy tắc TV mới phải đặt vào thư mục references của bộ kỹ năng, không đặt được vào thư mục craft. Đây là lựa chọn kỹ thuật bắt buộc, cần ghi vào hồ sơ để tránh hiểu lầm khi bàn giá.

### 7b.5 Danh mục tính năng bổ sung cho nền tảng di động và TV

Các mã dưới đây là phần công việc phát sinh do bối cảnh nêu trên.

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| H-01 | Khai báo nền tảng đích cho dự án thiết kế | I | Bổ sung lựa chọn nền tảng đích trong SPP gồm màn hình di động, máy tính bảng, desktop, và TV. Hệ thống truyền nền tảng này xuống trợ lý thiết kế để kích hoạt đúng bộ quy tắc tương ứng. | R-TV-1 |
| H-02 | Kiểm chứng hiển thị theo kích thước màn hình mục tiêu | I | Sau khi sinh sản phẩm, hệ thống tự chụp và kiểm tra hiển thị ở các kích thước mục tiêu gồm mobile 390px, tablet 768px, TV 1920x1080; phát hiện lỗi tràn khung, chữ quá nhỏ, vùng bị cắt; kết quả đưa lại để trợ lý thiết kế tự sửa. | R-TV-2 |
| H-03 | Bộ kỹ năng thiết kế cho thiết bị TV | I | Xây dựng bộ kỹ năng riêng gồm mô tả quy trình thiết kế sản phẩm trên TV, kèm tài liệu tham chiếu về đặc thù điều khiển từ xa, bàn phím ảo, cách thể hiện và định vị con trỏ, khoảng cách xem, luồng chuyển màn hình, cỡ chữ và khoảng cách tối thiểu. | 7b.4 |
| H-04 | Hệ quy chuẩn thiết kế riêng cho sản phẩm TV | I | Xây dựng hệ quy chuẩn thiết kế riêng cho TV gồm màu sắc, cỡ chữ, khoảng cách, thành phần, kèm khai báo loại trừ các quy tắc thiết kế dành cho chuột và bàn phím không áp dụng. | 7b.4, R-TV-3 |
| H-05 | Mẫu thiết kế riêng cho từng dạng sản phẩm TV | I | Chuẩn hóa một bộ mẫu thiết kế cho các dạng sản phẩm TV thường gặp gồm màn hình chính, danh sách nội dung, trang chi tiết, tìm kiếm, cài đặt, để đầu ra nhất quán. | 7b.4 |
| H-06 | Tự phê bình đầu ra theo bộ quy chuẩn TV | F | Kích hoạt cơ chế tự phê bình nhiều vòng của nền tảng, chấm điểm đầu ra theo bộ quy chuẩn TV, đạt ngưỡng mới chốt. | 7b.4 |
| H-07 | Thiết kế màn hình di động chất lượng cao | F | Áp dụng bộ quy tắc responsive có sẵn của nền tảng gồm thiết kế lại chứ không thu nhỏ, không cuộn ngang, vùng chạm 44px, cho sản phẩm màn hình di động. | 7b.1 |
| H-08 | Tài liệu tham chiếu cho thiết bị di động | I | Bổ sung tài liệu tham chiếu về đặc thù riêng của màn hình di động gồm bàn phím ảo hệ thống, thao tác cảm ứng, vùng cắt camera, hành vi cuộn, vào bộ tài liệu tham chiếu dùng chung. | 7b.2 |

### 7b.6 Khuyến nghị khi viết hồ sơ thầu cho phần di động và TV

| Nội dung | Khuyến nghị |
|---|---|
| Mức độ cam kết cho nền tảng di động | **Cam kết được** theo H-07, dựa trên năng lực có sẵn đã được kiểm chứng trong mã nguồn. |
| Mức độ cam kết cho thiết bị TV | **Cam kết có điều kiện**: cam kết các hạng mục H-01 đến H-06 sau khi PoC-7 xác nhận. Chưa có nền tảng nào hỗ trợ sẵn cho TV, nên toàn bộ nội dung này là công việc phát triển của SPP. |
| Rủi ro kỳ vọng | Nếu khách hàng hiểu là tích hợp xong là có thiết kế TV tốt, sẽ có rủi ro tranh chấp hợp đồng. Nên ghi rõ trong hồ sơ: **OpenDesign không có hỗ trợ TV sẵn, phần TV là hạng mục phát triển riêng do SPP thực hiện.** |
| Rủi ro phụ thuộc nhà cung cấp nền tảng | Ba hạng mục H-01, H-02, H-04 phụ thuộc cơ chế bên trong OpenDesign gồm danh sách nền tảng, cơ chế loại trừ craft, cơ chế tự phê bình. Vì nhà cung cấp phát hành rất nhanh, cần ghi điều khoản bảo trì: mỗi lần nâng phiên bản nền tảng phải kiểm thử lại nhóm H. |

---

## 8. Các hạng mục chưa cam kết, cần PoC trước khi chốt hồ sơ thầu

Các nội dung sau không nên ghi vào danh mục tính năng cam kết cho đến khi có kết quả kiểm thử; đề xuất đưa vào phụ lục phạm vi dự kiến giai đoạn PoC.

| Mã | Nội dung chưa xác minh | Ảnh hưởng | Câu hỏi cần trả lời | Thời lượng POC |
|---|---|---|---|---|
| P-01 | Cơ chế xác thực người dùng khi truy cập giao diện nhúng, không truyền khóa qua trình duyệt | Trung bình, quyết định kiến trúc nhúng | OpenDesign có nhận khóa qua tham số truy vấn hoặc cookie không? | 1 ngày |
| P-02 | Khả năng chạy giao diện dưới đường dẫn tiền tố của SPP, cùng origin | Trung bình, quyết định phương án nhúng A hay B | Giao diện có hỗ trợ base-path không? | 0,5 ngày |
| P-03 | Kiểm tra nguồn gốc khi nhúng chéo origin và luồng dữ liệu thời gian thực | Trung bình | Danh sách origin có đủ cho mọi API và luồng dữ liệu thời gian thực không? | 0,5 ngày |
| P-04 | Mức ảnh hưởng khi OpenDesign dùng chung môi trường với trợ lý trò chuyện | Trung bình | OpenDesign dừng bất thường có làm gián đoạn phiên trò chuyện không? | 0,5 đến 1 ngày |
| P-05 | Hình thức nâng cấp phiên bản, có phải dừng khởi động lại môi trường thiết kế hay không | Trung bình | Nâng phiên bản có làm mất phiên trợ lý đang chạy dở không? | 0,5 ngày |
| P-06 | Chặn tạo dự án ngoài workspace ngay trên giao diện | Thấp, dự án ngoài nằm trong vùng dữ liệu riêng, không chạm dữ liệu SPP | Có cần giới hạn ở giao diện ngay phiên bản đầu không? | Thuộc POC-1 |
| P-07 | Chất lượng thiết kế cho thiết bị TV | Cao, quyết định có cam kết được phần TV hay không | Chạy thử một bản thiết kế TV với bộ kỹ năng, hệ quy chuẩn và mẫu dự kiến ở mục 7b.4: trợ lý AI có thực sự tuân thủ quy tắc điều khiển từ xa, hay vẫn xuất hiện thành phần dành cho chuột? Cơ chế loại trừ craft có thực sự loại bỏ được quy tắc không phù hợp? | 2 đến 3 ngày |
| P-08 | Bước kiểm chứng hiển thị theo kích thước, mục H-02 | Trung bình, ảnh hưởng độ tin cậy của đầu ra | Có thực hiện kiểm chứng bằng công cụ chụp màn hình tự động trong môi trường thiết kế không, hay phải xây dịch vụ riêng? | 1 đến 2 ngày |

---

## 9. Bảng đối chiếu yêu cầu nghiệp vụ với tính năng

| Yêu cầu nghiệp vụ đã đặt ra | Tính năng đáp ứng | Kết luận khả thi |
|---|---|---|
| Có giao diện và nằm trong SPP | A-01, A-02, A-04, G-01 | Khả thi |
| Chỉ làm việc ở workspace SPP đang mở | B-01, B-02, B-05, D-01 | Khả thi, gần đủ có sẵn |
| Không cho phép chuyển workspace hoặc dự án tự do | B-03, B-04, B-06, P-06 | Khả thi |
| Dữ liệu thống nhất với trợ lý trò chuyện của SPP | D-01, D-02, D-03 | Khả thi |
| Quản lý bảo mật khi nhiều người dùng | D-04, F-06, F-07, F-08, B-03 | Khả thi, cô lập theo workspace |
| Vận hành dài hạn và cập nhật được | F-01 đến F-05, G-03, G-04 | Khả thi có điều kiện, phải ghim phiên bản |
| **Thiết kế tốt cho màn hình di động** | H-07, H-08, kèm C-01 đến C-05 | **Khả thi, cam kết được**, dựa trên năng lực có sẵn |
| **Thiết kế tốt cho thiết bị TV** | H-01 đến H-06, P-07 | **Khả thi có điều kiện**, nền tảng không có sẵn gì cho TV, toàn bộ là công việc phát triển của SPP, cam kết sau PoC-7 |

---

## 10. Đề xuất cấu trúc Hồ sơ thầu sử dụng danh mục này

1. **Mục yêu cầu kỹ thuật** — dùng bảng mục 9 làm khung nghiệp vụ.
2. **Mục phạm vi công việc** — chỉ đưa vào cam kết các mã I và F đã xác minh; các mã P nêu riêng là phạm vi dự kiến giai đoạn PoC hoặc khả năng mở rộng.
3. **Mục tiêu chấp nhận** — ánh xạ từng mã tính năng sang kịch bản kiểm thử tương ứng ở mục 8 báo cáo khả thi.
4. **Mục giả định và ràng buộc** — ghi rõ: giả định môi trường thiết kế dùng chung với môi trường trợ lý trò chuyện; phiên bản OpenDesign được ghim; quyền commit và phát hành thuộc SPP.
5. **Phụ lục PoC** — bảng mục 8, kèm thời lượng ước tính và tiêu chí đạt.
6. **Mục năng lực theo nền tảng** — dùng mục 7b.1 và 7b.2 làm cơ sở trả lời rõ đặc thù từng nền tảng; mục 7b.6 là phần nên nhấn mạnh khi bàn giá để tránh hiểu lầm về phạm vi cam kết.

---

*Tài liệu này được lập từ Báo cáo đánh giá khả thi phiên bản 3 ngày 24/09/2026 và sử dụng cùng bộ bằng chứng mã nguồn. Mục 7b được đối chiếu trực tiếp với mã nguồn OpenDesign tag main ngày 24/09/2026. Khi có kết quả PoC, cập nhật lại mục 8 và chuyển các mã P sang cam kết hoặc loại bỏ khỏi phạm vi.*
