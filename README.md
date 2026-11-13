# Tổng hợp (ea-tonghop)

Repo tổng hợp các script, tài liệu và spike của anh Điệp — không phải một sản phẩm đơn lẻ.
Mỗi thư mục con tương ứng một mảng công việc.

## Cấu trúc

- `docs/`
  - `adr/` — Architecture Decision Records (0001 openclaw extraction, 0001 3DGS default strategy & checkpoint)
  - `plans/` — kế hoạch tổng thể (3DGS production, thiết kế high-level sa bàn 5 cụm)
  - `reports/` — báo cáo/đề xuất (AI ngân hàng, OpenDesign→SPP, nang lực EA-PowerUp)
  - `traces/` — trace litellm mẫu (timeline CSV + markdown)
  - `pitfalls.md` — anti-pattern đã ghi nhận
- `openclaw/`
  - `scripts/` — extractor v10/v11, group conversations, clean export (assistant + personal agent)
  - `docs/README.md`
  - `output_v10/` — output đã generate (gitignored)
- `spikes/`
  - `3dgs-modal/` — spike huấn luyện 3DGS trên Modal (gsplat, colmap loader, debug)
  - `ssog/` — converter PLY → Streamed SOG (.ssog) trên Modal L4
- `tools/`
  - `aios/` — backfill/check/probe/survey cho AIOS usage rollup (JS)
  - `modal/` — modal_app, modal_convert*
  - `misc/` — spawn_gtq, style-pptx
- `showcase/` — artifact trình diễn (chatbot nội bộ ngân hàng docx/md, slides pptx/qmd, dms-design.html, ảnh)
- `data/` — PowerUp_V2 (mô hình high-level), test logs v10
- `shared/` — thư mục chia sẻ file/ảnh với user (gitignored nội dung lớn)

## Quy ước

- Thay đổi code đi qua branch + PR, review 3 góc (Correctness/Security/Convention).
- Chat tự do (brainstorm, đọc, phân tích) không tạo PR.
- Quyết định/khám phá mới đề xuất ghi vào `docs/adr/` hoặc `docs/pitfalls.md`.
- Output lớn (PLY, output_v10, shared) không commit — giữ ở volume Modal / shared/.

## Branch chính

- `develop` — nhánh làm việc chính, luôn ở trạng thái mới nhất.
- `main` — mirror của develop (fast-forward).
