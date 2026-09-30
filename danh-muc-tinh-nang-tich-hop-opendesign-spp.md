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
| **P** | Tính năng cần PoC | Chưa xác minh được, phụ thuộc kết quả kiểm thử giai đoạn PoC mục 8 |

Cột "Nguồn bằng chứng" trỏ về phần phụ lục của báo cáo khả thi đã ban hành kèm theo.

---

## 1. Nhóm A — Truy cập và điều hướng trong SPP

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| A-01 | Mục "Thiết kế" (Design) trong workspace | I | Bổ sung một mục chức năng mới trên thanh điều hướng chính của SPP, cho phép người dùng truy cập màn hình thiết kế mà không rời khỏi hệ thống, giữ nguyên bố cục khung làm việc chung (điều hướng trái + thanh tiêu đề). | §4.4, §6.5 |
| A-02 | Truy cập theo workspace đang mở | I | Màn hình thiết kế gắn với đúng workspace mà người dùng đang làm việc; đổi workspace sẽ đổi nội dung thiết kế tương ứng, không trộn lẫn dữ liệu giữa các workspace. | §4.1, §2 |
| A-03 | Kiểm soát phân quyền theo vai trò thành viên | I | Chỉ thành viên có quyền trong workspace được truy cập màn hình thiết kế; người không phải thành viên bị từ chối ở tầng ứng dụng, không phát sinh truy cập trái phép. | §4.3, §6.4 |
| A-04 | Nhúng giao diện thiết kế trong khung SPP | I | Giao diện làm việc của OpenDesign được hiển thị trọn vẹn trong vùng nội dung của SPP, phản hồi theo kích thước màn hình, có trạng thái tải và trạng thái lỗi hiển thị rõ ràng. | §6.5, §4.4 |

## 2. Nhóm B — Gắn kết và cô lập phạm vi làm việc (điểm cốt lõi của yêu cầu)

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| B-01 | Ghim dự án thiết kế vào workspace | I | Khi người dùng mở màn hình thiết kế lần đầu, hệ thống tự động liên kết dự án thiết kế với đúng thư mục dữ liệu của workspace, không yêu cầu người dùng tự chọn đường dẫn. | §6.3 |
| B-02 | Cấu hình hợp đồng workspace theo chuẩn dành cho bên điều phối | F | Sử dụng cơ chế hợp đồng workspace chính thức của OpenDesign (loại "scratch", quyền ghi dữ liệu do bên ngoài quản lý) để SPP giữ quyền kiểm soát vòng đời mã nguồn. | §3.2 |
| B-03 | Chặn truy cập thư mục ngoài workspace | F | Thiết kế chỉ được thao tác trên thư mục của workspace. Mọi yêu cầu chỉ tới thư mục khác bị hệ thống từ chối tự động kèm thông báo lỗi rõ ràng; cơ chế này kiểm tra cả đường dẫn gián tiếp qua liên kết (symlink). | §3.3, §5 |
| B-04 | Chống truy cập vùng dữ liệu nhạy cảm của hệ thống | F | Hệ thống chủ động từ chối việc gắn dự án vào các thư mục hệ thống, thư mục cấu hình và thư mục chứa thông tin đăng nhập/định danh, kể cả khi được mở bằng đường dẫn liên kết. | §3.2, §3.3 |
| B-05 | Cố định thư mục làm việc sau khi liên kết | F | Sau khi dự án được liên kết, thư mục làm việc không thể bị thay đổi ngầm bởi thao tác khác trong giao diện. | §3.2 |
| B-06 | Tách biệt cấu hình và dữ liệu tạm của tiến trình thiết kế | F | Khi chạy trong chế độ cô lập, toàn bộ cấu hình, bộ nhớ đệm, thư mục tạm và thư mục dữ liệu của tiến trình trợ giúp chỉ nằm trong vùng dữ liệu riêng đã cấp; không đọc hoặc ghi vào cấu hình hệ thống bên ngoài. | §3.3, §6.8 |

## 3. Nhóm C — Giao diện và quy trình thiết kế

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| C-01 | Trò chuyện với trợ lý thiết kế theo dự án | F | Người dùng trao đổi yêu cầu thiết kế bằng ngôn ngữ tự nhiên trong phạm vi dự án đang mở; phản hồi được trả về liên tục (streaming) thay vì chờ toàn bộ kết quả. | §3.1, §3.5 |
| C-02 | Xem trước kết quả thiết kế trực tiếp | F | Xem kết quả thiết kế ngay trong giao diện, không cần tải về máy. | §6.7 |
| C-03 | Quản lý tập tin thiết kế trong dự án | F | Danh sách và mở tập tin thiết kế thuộc dự án, xem nội dung, theo dõi các tệp trung gian phát sinh trong quá trình thiết kế. | §3.2, §6.7 |
| C-04 | Tái sử dụng bộ kỹ năng thiết kế (Skill) | F | Áp dụng các bộ kỹ năng thiết kế dựng sẵn cho dự án để đạt chất lượng đầu ra theo từng loại sản phẩm. | §3.2 |
| C-05 | Áp dụng hệ thống thiết kế (Design System) | F | Gắn bộ quy chuẩn thiết kế vào dự án để sản phẩm đầu ra tuân thủ hệ thống màu sắc, typography và thành phần. | §3.2 |
| C-06 | Lịch sử phiên làm việc thiết kế | F | Ghi nhận mỗi lần chạy: nhận diện phiên, trạng thái kết thúc, danh sách tệp và kết quả phát sinh, vị trí nhật ký sự kiện, lỗi/mã thoát — phục vụ tra cứu và đối chiếu. | §3.2 |
| C-07 | Xuất bản sản phẩm thiết kế | F | Xuất kết quả ra nhiều định dạng phục vụ trình bày (bản web, tài liệu PDF, trình chiếu, video). | §6.7 |

## 4. Nhóm D — Tích hợp dữ liệu với hệ thống SPP

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| D-01 | Dùng chung kho dữ liệu với trợ lý trò chuyện của SPP | I | Tệp thiết kế tạo ra nằm trực tiếp trong thư mục workspace; trợ lý trò chuyện (OpenCode / Claude Code) của SPP đọc được ngay, và ngược lại sản phẩm thiết kế tạo ra cũng xuất hiện ngay trong danh sách tệp của workspace mà không cần đồng bộ thủ công. | §4.1, §6.7 |
| D-02 | Quản lý phiên bản do SPP thực hiện | I | SPP giữ quyền commit, đẩy nhánh và phát hành; OpenDesign không tự thực hiện thao tác này (đúng ranh giới trách nhiệm hợp đồng workspace). | §3.2, §6.7 |
| D-03 | Cung cấp sản phẩm thiết kế qua dịch vụ tệp của SPP | I | Các tệp xuất bản (bản web/PDF/trình chiếu/video) được đưa vào danh mục tệp của workspace để thành viên tải về theo quyền hiện có. | §6.7 |
| D-04 | Cung cấp khóa xác thực theo từng workspace | I | Mỗi workspace có một khóa truy cập riêng do SPP sinh ra, có thời hạn, thu hồi khi container được tạo lại; khóa này không truyền xuống trình duyệt. | §6.4, §6.8 |

## 5. Nhóm E — Trợ lý AI thực thi thiết kế

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| E-01 | Trợ lý AI tạo nội dung thiết kế | I | Bộ trợ lý AI chạy trong môi trường riêng của workspace, thao tác trực tiếp trên thư mục dữ liệu workspace; tích hợp sẵn runtime OpenCode đang dùng cho SPP. | §3.5, §6.6, §6.2b |
| E-02 | Cấp khóa truy cập mô hình AI | I | Cấu hình khóa nhà cung cấp theo từng workspace/container; khóa không bị ghi ra ngoài vùng dữ liệu của container. | §3.3, §3.5, §6.6 |
| E-03 | Cơ chế dự phòng khi không dựng được trợ lý CLI | F | Có phương án dự phòng chạy trực tiếp qua lớp trung gian của OpenDesign khi không cài được trợ lý CLI; giới hạn rõ: chỉ sinh nội dung văn bản, chưa thao tác được trực tiếp trên thư mục workspace. | §3.5, §6.6 |
| E-04 | Tương thích nhiều loại trợ lý AI | F | OpenDesign hỗ trợ nhiều bộ trợ lý (Claude Code, Codex, OpenCode, Gemini…) qua cơ chế phát hiện theo PATH, giúp chủ đầu tư không bị khóa vào một nhà cung cấp. | §3.5 |

## 6. Nhóm F — Vận hành, giám sát và bảo mật

| Mã | Tính năng | Mức | Mô tả nghiệp vụ | Nguồn |
|---|---|---|---|---|
| F-01 | Tự động khởi tạo môi trường thiết kế theo workspace | I | Môi trường thiết kế được tạo tự động, theo mô hình mỗi workspace một môi trường cô lập đang vận hành cho trợ lý trò chuyện; có thể khởi tạo theo nhu cầu khi người dùng mở màn hình thiết kế. | §4.2, §6.2b |
| F-02 | Giám sát tình trạng hoạt động | I | Có điểm kiểm tra sức khoẻ dịch vụ thiết kế; trường hợp tiến trình dừng bất thường được phát hiện và khởi động lại tự động. | §3.1, §6.2b |
| F-03 | Quản lý tài nguyên môi trường thiết kế | I | Giới hạn bộ nhớ, số tiến trình và phân bổ tài nguyên theo thông số đã kiểm chứng; giám sát mức sử dụng thực tế. | §3.6, §6.2b |
| F-04 | Đóng gói và phát hành phiên bản môi trường thiết kế | I | Hình ảnh chạy được tạo sẵn từ mã nguồn OpenDesign đã ghim phiên bản, kèm trợ lý AI cần thiết, đảm bảo tính tái lập của môi trường. | §6.2, §6.2b, §7 (R4, R6) |
| F-05 | Quy trình nâng cấp phiên bản có kiểm soát | I | Chính sách ghim phiên bản OpenDesign, lịch nâng cấp được duyệt, kèm kiểm thử hồi quy trước khi áp dụng (do nhịp phát hành thay đổi rất nhanh từ nhà cung cấp nền tảng). | §3.6, §7 (R4) |
| F-06 | Xác thực người dùng khi truy cập màn hình thiết kế | I | Yêu cầu truy cập được kiểm tra bằng phiên đăng nhập hợp lệ của SPP kèm quyền thành viên workspace; lớp trung gian xác thực chuyển tiếp quyền truy cập sang OpenDesign mà không lộ khóa. | §6.4 |
| F-07 | Hạn chế nguồn gốc truy cập API | F | Danh sách nguồn gốc được phép gọi API của môi trường thiết kế chỉ gồm địa chỉ hệ thống SPP. | §3.4, §6.4 |
| F-08 | Môi trường thiết kế không mở ra Internet | I | Dịch vụ thiết kế chỉ hoạt động trong mạng nội bộ, không tiếp xúc trực tiếp với Internet công cộng; mọi truy cập qua SPP. | §6.8 |
| F-09 | Xử lý đồng thời và giới hạn phiên | I | Môi trường thiết kế phục vụ phiên làm việc theo giới hạn số phiên mở, không ảnh hưởng phiên trợ lý trò chuyện. | §4.2, §6.2b |
| F-10 | Nhật ký và truy vết hoạt động | I | Ghi nhận nhật ký thao tác thiết kế và lỗi phát sinh phục vụ chẩn đoán, đối chiếu khi có sự cố. | §3.2, §6.2b |

## 7. Nhóm G — Tương thích và yêu cầu phi chức năng

| Mã | Yêu cầu | Mức | Mô tả | Nguồn |
|---|---|---|---|---|
| G-01 | Không phụ thuộc dịch vụ trung gian mới | I | Hệ thống chạy được một OpenDesign cho mỗi workspace, không yêu cầu thêm hạ tầng proxy công khai cho giao diện. | §3.1, §6.5 |
| G-02 | Mức sử dụng tài nguyên thấp khi không hoạt động | F | Môi trường thiết kế tiêu thụ rất ít tài nguyên ở trạng thái rảnh (đã đo ở nhà cung cấp: khoảng 18–22 MB). | §3.6 |
| G-03 | Tương thích nền tảng chạy | F | Yêu cầu Node.js ~24, tương thích với nền tảng đang dùng của SPP. | §3.6, §6.2b |
| G-04 | Tuân thủ giấy phép mã nguồn mở | I | OpenDesign phát hành theo Apache-2.0; gói bàn giao giữ nguyên phần khai báo giấy phép và ghi công. | §7 (R7) |
| G-05 | Bàn giao tài liệu | I | Hồ sơ bàn giao gồm: tài liệu kiến trúc, quy trình cài đặt/nâng cấp, cấu hình tham số môi trường, kịch bản kiểm thử, quy trình xử lý sự cố. | §8 |

---

## 8. Các hạng mục chưa cam kết (cần PoC trước khi chốt hồ sơ thầu)

Các nội dung sau **không nên ghi vào danh mục tính năng cam kết** cho đến khi có kết quả kiểm thử; đề xuất đưa vào phụ lục "Phạm vi dự kiến giai đoạn PoC" và nêu rõ trong Hồ sơ thầu.

| Mã | Nội dung chưa xác minh | Ảnh hưởng | Câu hỏi cần trả lời | Thời lượng POC |
|---|---|---|---|---|
| P-01 | Cơ chế xác thực người dùng khi truy cập giao diện nhúng (không truyền khóa qua trình duyệt) | Trung bình — quyết định kiến trúc nhúng | OpenDesign có nhận khóa qua tham số truy vấn/cookie không? | 1 ngày |
| P-02 | Khả năng chạy giao diện dưới đường dẫn tiền tố của SPP (cùng origin) | Trung bình — quyết định phương án nhúng A hay B | Giao diện có hỗ trợ base-path không? | 0,5 ngày |
| P-03 | Kiểm tra nguồn gốc (Origin) khi nhúng chéo origin và luồng dữ liệu thời gian thực | Trung bình | Danh sách origin có đủ cho mọi API và luồng SSE không? | 0,5 ngày |
| P-04 | Mức ảnh hưởng khi OpenDesign dùng chung môi trường với trợ lý trò chuyện | Trung bình | OpenDesign dừng bất thường có làm gián đoạn phiên trò chuyện không? | 0,5–1 ngày |
| P-05 | Hình thức nâng cấp phiên bản (có phải dừng khởi động lại môi trường thiết kế hay không) | Trung bình | Nâng phiên bản có làm mất phiên trợ lý đang chạy dở không? | 0,5 ngày |
| P-06 | Chặn tạo dự án ngoài workspace ngay trên giao diện | Thấp — dự án ngoài nằm trong vùng dữ liệu riêng, không chạm dữ liệu SPP | Có cần giới hạn ở giao diện ngay phiên bản đầu không? | thuộc POC-1 |

---

## 9. Bảng đối chiếu yêu cầu nghiệp vụ → tính năng

| Yêu cầu nghiệp vụ đã đặt ra | Tính năng đáp ứng | Kết luận khả thi |
|---|---|---|
| Có giao diện và nằm trong SPP | A-01, A-02, A-04, G-01 | Khả thi |
| Chỉ làm việc ở workspace SPP đang mở | B-01, B-02, B-05, D-01 | Khả thi (gần đủ có sẵn) |
| Không cho phép chuyển workspace/project tự do | B-03, B-04, B-06, P-06 | Khả thi |
| Dữ liệu thống nhất với trợ lý trò chuyện của SPP | D-01, D-02, D-03 | Khả thi |
| Quản lý bảo mật khi nhiều người dùng | D-04, F-06, F-07, F-08, B-03 | Khả thi (cô lập theo workspace) |
| Vận hành dài hạn, cập nhật được | F-01 đến F-05, G-03, G-04 | Khả thi, có điều kiện (phải ghim phiên bản) |

---

## 10. Đề xuất cấu trúc Hồ sơ thầu sử dụng danh mục này

1. **Mục yêu cầu kỹ thuật** — dùng bảng mục 9 làm khung nghiệp vụ.
2. **Mục phạm vi công việc (Scope of Work)** — chỉ đưa vào cam kết các mã **I** và **F** đã xác minh; các mã **P** nêu riêng là "phạm vi dự kiến giai đoạn PoC / khả năng mở rộng".
3. **Mục tiêu chấp nhận (Acceptance Criteria)** — ánh xạ từng mã tính năng sang kịch bản kiểm thử tương ứng ở mục 8 báo cáo khả thi.
4. **Mục giả định và ràng buộc** — ghi rõ: giả định môi trường thiết kế dùng chung với môi trường trợ lý trò chuyện; phiên bản OpenDesign được ghim; quyền commit/phát hành thuộc SPP.
5. **Phụ lục PoC** — bảng mục 8, kèm thời lượng ước tính và tiêu chí đạt.

---

*Tài liệu này được lập từ Báo cáo đánh giá khả thi phiên bản 3 (24/09/2026) và sử dụng cùng bộ bằng chứng mã nguồn. Khi có kết quả PoC, cập nhật lại mục 8 và chuyển các mã P sang cam kết hoặc loại bỏ khỏi phạm vi.*
