# Báo cáo đánh giá khả thi: Tích hợp OpenDesign (nexu-io/open-design) vào BSM Superpower (SPP)

- **Ngày viết:** 24/09/2026
- **Phạm vi:** nghiên cứu khả thi (feasibility study) — chưa thay đổi bất kỳ code nào
- **Yêu cầu đặt ra:**
  1. OpenDesign (OD) có giao diện và phải nằm trong SPP (không phải app standalone rời).
  2. OD chỉ làm việc ở **một workspace cụ thể** — đúng workspace SPP đang mở.
  3. Không cho phép user chuyển workspace/project tự do như khi chạy standalone.

- **Phương pháp & nguồn căn cứ:**
  - (N1) Docs chính thức của repo `nexu-io/open-design` (README, QUICKSTART, docs/architecture.md, docs/orchestrator-workspaces.md, deploy/README.md).
  - (N2) **Source code OD** — clone sparse tag main (~v0.24.x, 24/09/2026) tại `/tmp/od-research/od-repo`, đã đọc trực tiếp các file daemon liên quan (mọi trích dẫn `apps/daemon/...` dưới đây là đã verify trong code, không phải lời khai doc).
  - (N3) Khảo sát codebase SPP `~/work/codes/bsm-superpower` (đọc thuần, kèm file:line).

---

## 1. Kết luận tóm tắt

**KHẢ THI — mức độ cao**, với phương án chính **(B) OD chạy trực tiếp bên trong ACP sandbox container hiện có của workspace** (mục 6.2b), và phương án dự phòng (A) container OD riêng biệt (mục 6.2) chỉ khi blast radius không chấp nhận được. Cả hai đều không phải Docker-in-Docker — OD luôn chạy như process thường. Vì:

1. OD có sẵn **contract chính thức cho orchestrator bên ngoài** chuẩn bị workspace (`orchestratorWorkspace: {kind: "scratch", writeback: "external"}`) — đã implement thật trong daemon, không phải ý tưởng trên giấy (N2: `workspace-contract.ts`).
2. OD có sẵn cơ chế **khóa phạm vi thư mục làm việc**: `OD_SANDBOX_MODE=1` + `OD_SANDBOX_IMPORT_ALLOWED_ROOTS` — mọi project import-folder ngoài allowed roots bị từ chối; toàn bộ agent home/config/tmp bị cô lập vào data dir (N2: `sandbox-mode.ts`).
3. OD chạy được dạng **1 container duy nhất** (daemon Express tự serve cả API + web UI static export), footprint nhỏ (mem limit 384m, idle ~20MB) — khớp mô hình per-workspace container mà SPP đã vận hành cho ACP sandbox (N1: `deploy/docker-compose.yml`, `deploy/README.md`).
4. Bên SPP, workspace đã ánh xạ 1-1 ra **thư mục trên đĩa** và đã có sẵn đầy đủ pattern cần dùng: membership gate, SSE streaming, catch-all API proxy, iframe component, container lifecycle (N3).

**Các gap bắt buộc phải giải** (chi tiết mục 6–7): auth cho browser trong iframe (OD chỉ có single-tenant token), OD không có "single-project lock" ở UI, OD image không bundle agent CLI (cần build image `od + opencode`), và OD đuổi release rất nhanh (cần pin version).

---

## 2. Dịch yêu cầu nghiệp vụ → yêu cầu kỹ thuật

| Yêu cầu user | Yêu cầu kỹ thuật tương ứng |
|---|---|
| "Có giao diện, nằm trong SPP" | OD web UI được truy cập từ bên trong shell SPP (iframe/embed), có mục nav riêng trong workspace, cảm giác là 1 section của SPP |
| "Chỉ làm việc ở workspace SPP đang mở" | OD project duy nhất bị ghim (bind) vào đúng thư mục đĩa của workspace SPP đó; agent chạy trên đúng thư mục đó |
| "Không cho chuyển workspace tự do" | Không thể import/trỏ project vào thư mục ngoài workspace; UI không khuyến khích tạo project tự do; container OD có phạm vi filesystem giới hạn |
| (ngầm định) Dữ liệu thống nhất | File thiết kế OD sinh ra nằm trong workspace dir → ACP agent và Files API của SPP thấy ngay |

---

## 3. Căn cứ từ phía OpenDesign

### 3.1 Chế độ chạy & Docker deployment

OD có 3 chế độ: desktop Electron, from-source (`pnpm tools-dev`), và **Docker**. Chế độ Docker là nền tảng tích hợp:

- Image công khai **`ghcr.io/nexu-io/od:latest`**, Alpine-based, single runtime image — `deploy/docker-compose.yml:6` (N1).
- **Daemon tự serve cả API lẫn web UI** (static Next.js export từ `apps/web/out`) trên cùng một origin/port: "The daemon serves both the API and the built Next.js static export, so there is no separate nginx container" — `deploy/README.md:3-5`; `docs/architecture.md` §"Container and daemon-served production" (N1). → Không cần hạ tầng proxy riêng cho UI.
- Compose mặc định an toàn sẵn: `ports: 127.0.0.1:7456:7456`, `read_only: true` (rootfs), `tmpfs /tmp`, `no-new-privileges`, `mem_limit: 384m`, `pids_limit: 256`, healthcheck `/api/health` — `deploy/docker-compose.yml:21-43` (N1).
- Web UI **tách rời được** khỏi daemon: `apps/web/next.config.ts` có 3 output mode — static export (mặc định), `OD_WEB_OUTPUT_MODE=server` (Next SSR chạy riêng, proxy `/api/*`, `/artifacts/*`, `/frames/*` về daemon), `standalone` (N1/N2). → Có lối reverse-proxy nếu cần, nhưng không bắt buộc.

### 3.2 Contract "Externally Prepared Workspaces" — đúng kịch bản tích hợp

`docs/orchestrator-workspaces.md` (N1) định nghĩa chính thức:

- **Storage**: `od-owned` (file do OD quản dưới data dir) vs `folder-backed` (file nằm ở filesystem root bên ngoài do caller cấp).
- **Provenance**: `user-local` (user tự chọn folder, OD sửa in-place) vs **`orchestrator-scratch`** — "a disposable folder prepared by an external orchestrator. OD may read and write the scratch workspace, but source authority and writeback stay outside OD."
- Ranh giới trách nhiệm được cố tình hẹp: "OD may read and write the workspace it is given... Source checkout state, pull-request creation, deployment, publishing, and writeback policy remain outside OD." → OD không tự ý đụng source control/deploy; SPP giữ quyền quản lý vòng đời.
- Đầu ra chuẩn là **result package** (run identity, terminal status, project files + artifact manifests, event-log location, errors/exit code) — có thể dùng làm hợp đồng trao đổi giữa OD và SPP backend.

**Đã implement trong code** (N2, `apps/daemon/src/workspace-contract.ts`, 128 dòng):

- `normalizeOrchestratorWorkspace`: chỉ chấp nhận `kind: "scratch"` (L53), `writeback: "external"` (L59), whitelist đúng 5 field `kind/sourceLabel/sourceRef/baseRevision/writeback` (L8-14).
- `projectWorkspaceProvenance` (L92-128): phân loại 3 trạng thái — `od-owned`, `folder-backed + user-local`, `folder-backed + orchestrator-scratch`.

**API gán workspace** (N2, `apps/daemon/src/import-export-routes.ts`):

- `POST /api/import/folder` (L344) là **endpoint duy nhất** được phép gán `baseDir` cho project; body nhận `{baseDir, name, skillId, designSystemId, orchestratorWorkspace}`.
- Generic `POST /api/projects` **chủ động chặn** client tự gán: `'baseDir can only be set via POST /api/import/folder'`, `'orchestratorWorkspace can only be set via POST /api/import/folder or POST /api/projects/:id/working-dir'` — `apps/daemon/src/routes/project/index.ts:3876-3902` (N2). Đây là design chống走私 đúng hướng bảo mật.
- **`baseDir` bất biến sau import**: "baseDir is immutable after import; use a new import to change it" — `routes/project/index.ts:5274` (N2). → Một project import rồi không bị "trôi" sang thư mục khác.
- Validate chặt khi import (N2, `import-export-routes.ts`): `realpath()` + `lstat` phải là directory thật (L283-296), chặn filesystem root (L300), chặn trỏ vào chính `RUNTIME_DATA_DIR` **kể cả qua symlink** (L295-300, L437-443), `blockedProjectRootReason` chặn system/credential dirs (`.ssh`, `.aws`, `.gnupg`, `.kube`, `.docker`, `$HOME`, `/etc`...).

### 3.3 Cơ chế khóa workspace: `OD_SANDBOX_MODE` — rào chắn built-in

`apps/daemon/src/sandbox-mode.ts` (N2, đọc toàn bộ 195 dòng):

- `OD_SANDBOX_MODE=1` bật sandbox mode (L6, L37-49).
- `OD_SANDBOX_IMPORT_ALLOWED_ROOTS` — danh sách absolute path (phân tách bằng `:`), **mọi folder-import project bị từ chối nếu root nằm ngoài các roots này** (`sandboxImportedProjectRootUnavailableReason` L96-104; containment check qua `realpath` L67-93, chống symlink escape). Thông báo lỗi rõ ràng: "Imported-folder projects are not available in OD_SANDBOX_MODE unless their root is under OD_SANDBOX_IMPORT_ALLOWED_ROOTS."
- Khi bật sandbox, toàn bộ runtime của agent bị **cô lập vào data dir** (`resolveSandboxRuntimeConfig` L106-128): agent-home, cache, config, tmp, tool-config đều nằm dưới `OD_DATA_DIR/sandbox/...`.
- `applySandboxRuntimeEnv` (L162-195) ghi đè env của agent process khi spawn: `HOME`, `USERPROFILE`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, `TMPDIR/TEMP/TMP`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `OPENCODE_TEST_HOME`, `OD_AGENT_HOME` → agent CLI chạy trong OD container không thể đụng cấu hình/credentials ngoài phạm vi.
- Bật sandbox mode **bắt buộc** khai `OD_DATA_DIR` tường minh (`daemon-paths.ts:125-133`, `requireExplicit`) — an toàn hơn, không fallback âm thầm.

> Đánh giá: đây chính là cơ chế đáp ứng yêu cầu "không cho làm việc tự do" ở tầng data — SPP chỉ cần set 2 env khi tạo container.

### 3.4 Auth & origin

- `OD_API_TOKEN`: single shared token, chấp nhận `Authorization: Bearer` (CLI/proxy) hoặc Basic auth (username cố định `open-design`) cho browser; loopback được bypass; **bind non-loopback mà không có token thì daemon từ chối startup** (`apps/daemon/src/server.ts:3152-3176`; `api-token-auth.ts`; `deploy/README.md:60-64`) (N1/N2).
- `OD_DISABLE_API_AUTH=1`: tắt auth khi đặt sau reverse proxy **đã auth mọi request** (`deploy/README.md`, compose env L19) — lối tích hợp hợp lệ được docs khuyến nghị.
- `OD_ALLOWED_ORIGINS`: allowlist origin browser được phép gọi `/api` (`origin-validation.ts:15-29`; check tại `server.ts:3475-3476`) (N2).
- **Không có concept user/tenant**: "The shared API token is single-tenant authentication, not user-level access control" (`deploy/README.md:61-62`). Không tìm thấy multi-tenant user model trong codebase (N2 — đã grep). → Isolation đa user phải đến từ kiến trúc bên ngoài (1 container/workspace + token riêng), không thể dùng 1 OD daemon chung.

### 3.5 Agent runtime

- Daemon **spawn agent CLI trên cùng máy** qua PATH scan (27 runtime defs: claude, codex, opencode, hermes, kimi...; opencode thuộc nhóm `json-event-stream` — `docs/agent-adapters.md` §3) (N1). Agent chạy như process con của daemon — trong mô hình Docker, agent chạy **bên trong OD container**.
- **Image OD không bundle CLI nào**: "The image intentionally does not bundle Claude/Codex/Gemini CLI binaries. Keep those outside the image" (`deploy/README.md:91-93`) — phải mount/install CLI + cấp API key env (`DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`... L186-192); Alpine cần `libc6-compat` hoặc mount glibc host cho CLI glibc (L173-176) (N1).
- Daemon inject `OD_BIN`, `OD_DAEMON_URL`, `OD_PROJECT_ID`, `OD_PROJECT_DIR` vào env agent để media/image skills gọi ngược daemon (`QUICKSTART.md` §Media generation) (N1).
- **BYOK proxy mode** (`POST /api/proxy/{anthropic,openai,azure,google,senseaudio}/stream` — `routes/chat.ts:986+`, `byok-tools.ts`): chạy không cần CLI nào, nhưng **text-only** — upstream trả text → parse khối `<artifact>` → ghi project files; có tool-calling daemon-side cho image/video generation, nhưng **không có filesystem tools** (không đọc/ghi/chạy lệnh trong workspace) (N2). → Phù hợp làm fallback, không phải trải nghiệm chính.

### 3.6 Footprint

| Thông số | Giá trị | Nguồn |
|---|---|---|
| Node | ~24.x (`engines`) | `package.json` |
| Container mem limit mặc định | 384m (heap 192MB) | compose L13, L30 |
| Idle memory (đã verify bởi upstream) | ~18-22 MiB | `deploy/.env.example:29-31` |
| Port | 7456 | compose L16-17 |
| pids_limit | 256 | compose L31 |
| Nhịp release | rất nhanh (~37 releases, commit mỗi ngày) | GitHub Releases |

### 3.7 Những điểm KHÔNG tìm thấy ở OD (đã kiểm tra, không phỏng đoán)

1. **Không có "single-project lock"** — không env kiểu `OD_DEFAULT_PROJECT_ID`/`OD_LOCK_WORKSPACE_DIR`; UI luôn có Home/New Project. Project `od-owned` (trong data dir) vẫn tạo được — nhưng vì nằm trong data dir riêng của container, nó **không đụng workspace SPP**.
2. Không có multi-user/tenant model (xem 3.4).
3. Chưa verify: OD web UI có hỗ trợ **base-path** (chạy dưới prefix `/design/...`) hay không — ảnh hưởng phương án nhúng (mục 6.5, câu hỏi POC Q2).

---

## 4. Căn cứ từ phía SPP

### 4.1 Workspace model — workspace ĐÃ là thư mục trên đĩa

- DB: bảng `workspaces` (id, slug, title, status, kind, `agent_override`...) + `workspace_members(user_id, workspace_id, roles[])` — `apps/backend/lib/workspace.ts:269-313` (`resolveMyWorkspaces`); workspace personal/kind tại `:382-410` (N3).
- **Thư mục đĩa**: `WORKSPACES_ROOT = env.WORKSPACES_ROOT ?? "/var/workspaces"` (container view) — `apps/backend/lib/workspace-setup.ts:42`; mọi fs operation build `join(WORKSPACES_ROOT, slug, memberSlug)` (`:157,185,521,747` — mkdir, provision member folders, delete files) (N3).
- **Host view** (path gửi cho daemon/container ngoài): `WORKSPACES_HOST_ROOT = env.WORKSPACES_HOST_ROOT || "/home/ubuntu/bsm/workspaces"` — `apps/backend/lib/openacp.ts:37-38`; session path `${WORKSPACES_HOST_ROOT}/${slug}/${emailSlug}` (`openacp.ts:185`) (N3).
- Compose mount: `${WORKSPACES_HOST_PATH:-/home/ubuntu/bsm/workspaces}:/var/workspaces:rw` — `docker-compose.prod.yml:78` (N3).
- Frontend: route 1 workspace `apps/frontend/app/w/[slug]/layout.tsx` (WorkspaceContext: slug, workspace, roles, members, repos); switch workspace qua `WorkspaceSwitcher` (`GlobalRail.tsx:430+`, `router.push('/w/<slug>')` tại `:627`); nav sections `WORKSPACE_SECTION_LABELS` + nav items `GlobalRail.tsx:313-375` (N3).

→ **Điểm neo then chốt**: OD chỉ cần import đúng `${WORKSPACES_HOST_ROOT}/<slug>/<memberSlug>` là làm việc trên đúng workspace, cùng dữ liệu với ACP agent.

### 4.2 ACP sandbox — pattern "1 workspace = 1 container" đã vận hành

- Backend **không tự gọi Docker**; mọi lifecycle container đi qua OpenACP daemon HTTP API: `OPENACP_URL` (`openacp.ts:27-31`), `createWorkspaceSession(slug, emailSlug)` → `POST /api/v1/sessions` với `{workspace, agent, model, mcpToken, sandboxEnabled}` (`openacp.ts:180-237`) (N3).
- Container do daemon Go (`bsm-superpower-acp`, `internal/agent/docker_sandbox.go`) tạo — bind-mount workspace + `.claude` + shared-plugin RO, network sandbox riêng (`docs/superpower-os/12-architecture.md:515-517`) (N3).
- Admin container API có sẵn: list/kill containers, `setSandboxNetworkOverride` (network per-workspace dạng `acpsp-<slug>`) — `openacp.ts:1350-1419` (N3).
- Agent run: `runPromptAndAwait` (`openacp.ts:596+`) → POST prompt + SSE `${OPENACP_URL}/api/v1/events` (`:289,897`), turn tracker theo usage/cost (`:565+`); stream ra client qua stream bus Redis/Memory (`chat-stream.ts:48`, Last-Event-ID resume); frontend pump bằng `getReader()` (`useChatStream.ts:295,666`) (N3).
- Agent per-workspace đã hỗ trợ **opencode**: `acp-agent-settings.ts` (per-workspace `agent_override` → `system_settings.default_acp_agent` → fallback `claude-code`; `AcpAgent` gồm claude-code/opencode — `packages/shared/src/workspace-types.ts:25-33`) (N3).
- Session pool LRU 5 session/user (`session-pool.ts`) (N3).

→ SPP đã quen vận hành container theo workspace (tạo, port, network, lifecycle). Thêm 1 loại container OD per-workspace là mở rộng tự nhiên của pattern hiện có.

### 4.3 Pattern nhúng app ngoài

- **Catch-all API proxy có sẵn**: `apps/frontend/app/api/[...path]/route.ts` forward `/api/*` → `BACKEND_INTERNAL_URL` (strip hop-by-hop headers) — pattern chuẩn để thêm proxy path mới sang OD container (N3).
- `apps/frontend/next.config.ts` **không có rewrites** — chỉ `output: standalone`; không có nginx trong repo (Cloudflare DNS → port host trực tiếp) (N3).
- **Iframe pattern có sẵn** nhưng đang stub: Canvas `LinkNode.tsx:60-320` (sandbox attr, resize, error state); `lib/embeds.ts` trả null ("Kanwas embed utilities — not used in Superpower") — có UI mẫu để tận dụng (N3).
- Auth: `middleware.ts` verify cookie `ba_token` (JWT HS256, `BA_JWT_SECRET` share FE/BE); membership gate chuẩn `requireWorkspaceRole/requireWorkspaceMember` (`workspace.ts:346-374`, `permissions.ts:91-142` — 404 khi slug không tồn tại, 401/403 + MFA check) (N3).
- docker-compose hiện chỉ có frontend/backend/redis — chưa có service proxy/app ngoài nào (N3).

### 4.4 Frontend shell — chỗ nhúng "Design"

- Layout workspace: rail trái (GlobalRail) + topbar breadcrumb + content `<div className="flex flex-1 min-h-0 overflow-hidden">{children}</div>` (`w/[slug]/layout.tsx` cuối file) — đủ chứa iframe full-height (N3).
- Thêm section "Design" = thêm `app/w/[slug]/design/page.tsx` + 1 nav item ở `GlobalRail.tsx:365-375` + label ở `:313` (N3).
- Chưa có micro-frontend/postMessage bridge — nếu cần giao tiếp 2 chiều sẽ tự viết (v1 không cần).

### 4.5 Env/config pattern liên quan

`OPENACP_URL=http://host.docker.internal:21421` (socat bridge → daemon 127.0.0.1:21420, `12-architecture.md:1153-1159`), `OPENACP_TOKEN`, `WORKSPACES_ROOT` / `WORKSPACES_HOST_ROOT` / `WORKSPACES_HOST_PATH`, `BACKEND_INTERNAL_URL=http://backend:3001`, `REDIS_URL`, `BA_JWT_SECRET`, `PM2_INSTANCES` (N3).

---

## 5. Ma trận đánh giá theo yêu cầu

| # | Yêu cầu | Khả thi? | Căn cứ chính | Gap cần giải |
|---|---|---|---|---|
| 1 | OD UI nằm trong SPP | **Có** (2 phương án, mục 6.5) | Daemon serve UI + API cùng origin (N1); SPP có iframe pattern + layout content full-height (N3) | Auth cho browser trong iframe; OD UI chưa verify base-path |
| 2 | OD chỉ làm việc trên workspace SPP đang mở | **Có — gần đủ sẵn** | `POST /api/import/folder` + `orchestratorWorkspace` contract (N2); `OD_SANDBOX_MODE` + allowed roots (N2); baseDir bất biến | Không có single-project lock ở UI — project od-owned trong data dir vẫn tạo được (không ảnh hưởng workspace SPP) |
| 3 | Không cho chuyển workspace tự do | **Có** | Sandbox import gate từ chối mọi path ngoài allowed roots, chống symlink (N2); import chặn system/credential dirs | — |
| 4 | Dữ liệu thống nhất với agent SPP | **Có** | Folder-backed project = chính workspace dir mà ACP sandbox bind-mount (N2+N3) | — |
| 5 | Multi-user trên cùng OD | Không nên | Single-tenant token, không user model (N1) | Isolation bằng 1 container + 1 token per workspace (đúng mô hình SPP) |
| 6 | Agent chạy trong OD | **Có, cần build image** (A) hoặc dùng opencode sẵn trong ACP image (B) | Image không bundle CLI (N1); opencode là runtime def chính thức của OD (N1); ACP sandbox image đã có opencode (N3) | A: build/maintain image `od + opencode`; B: build lại image ACP khi nâng OD; cân nhắc memory limit cao hơn khi agent chạy |
| 7 | Vận hành dài hạn | **Có, có điều kiện** | Apache-2.0; compose an toàn mặc định | Upstream release hàng tuần → phải pin version |

---

## 6. Giải pháp kỹ thuật đề xuất

### 6.1 Kiến trúc đích — Phương án A (DỰ PHÒNG)

> **Phương án chính là B (6.2b): OD chạy trực tiếp trong ACP sandbox container hiện có của workspace.** Phương án A (container OD riêng biệt) chỉ là fallback khi blast radius hoặc version-coupling không chấp nhận được. Sơ đồ dưới đây mô tả A đầy đủ để dùng làm baseline so sánh.

```
Browser (SPP UI, origin spp.example.com)
  │  /w/<slug>/design  (route mới, nav item "Design")
  ▼
iframe → OD UI (origin riêng, port per-workspace, hoặc qua auth-proxy)
  │  same-origin /api, /artifacts, /frames (HTTP + SSE)
  ▼
OD container (1 per SPP workspace)
  ├─ daemon Express (serve static web + API, SQLite)
  ├─ opencode CLI (agent runtime, chạy trong container)
  ├─ volume riêng: OD data dir (/app/.od ↔ OD_DATA_DIR) — SQLite, artifacts index, sandbox home
  ├─ bind-mount (rw): ${WORKSPACES_HOST_ROOT}/<slug>/<memberSlug>   ← CÙNG thư mục ACP sandbox mount
  └─ env: OD_SANDBOX_MODE=1
          OD_SANDBOX_IMPORT_ALLOWED_ROOTS=<workspace dir>
          OD_DATA_DIR=<volume>
          OD_BIND_HOST=0.0.0.0 (trong network nội bộ)
          OD_API_TOKEN=<token per-workspace do SPP backend sinh>
          OD_ALLOWED_ORIGINS=<origin SPP>
          OPENROUTER_API_KEY / provider keys (tách theo container)
  network: bridge nội bộ / acpsp-<slug>; KHÔNG expose public internet
```

Nguyên tắc: **mỗi workspace SPP = 1 OD container độc lập** — isolation user đạt được ở tầng hạ tầng (khác OD standalone chia sẻ 1 daemon), tái dùng đúng pattern ACP sandbox đang chạy.

### 6.2 Container & vòng đời (phương án A — fallback)

Phương án chính (B) không cần container riêng; xem 6.2b.

1. **Image riêng** `bsm-superpower-opendesign:v1`: FROM `ghcr.io/nexu-io/od:<pinned>` + cài opencode (và glibc compat nếu cần — tham khảo `deploy/README.md:173-176`). Pin version OD; nâng có chủ đích theo changelog (upstream release hàng tuần — coi như vendored dependency).
2. **Lifecycle**: tạo container lazy (lần đầu user mở Design trong workspace) hoặc theo cùng nhịp provision workspace; kill theo idle tương tự session pool ACP. Port allocation theo pattern `host.docker.internal:<port>` hiện có.
3. Tài nguyên: mem limit nên đặt **1-2GB** (không phải 384m mặc định) vì agent CLI chạy trong container; rootfs `read_only` + `no-new-privileges` + `pids_limit` giữ theo compose gốc của OD.

### 6.2b Phương án B (CHÍNH) — OD chạy trực tiếp bên trong ACP sandbox container

Mỗi workspace SPP đã có 1 container riêng với agent (opencode/Claude Code) setup sẵn. Thay vì tạo thêm 1 container OD riêng (phương án A), **OD daemon + web UI chạy như một process thường ngay bên trong container đó** — image `bsm-superpower-acp-sandbox:v2` đã có Node 24 + opencode + glibc đầy đủ, chỉ cần thêm OD daemon là đủ runtime. KHÔNG phải Docker-in-Docker: không Docker nào chạy trong container, chỉ là thêm 1 Node process cạnh entrypoint hiện có.

Cách bật:
1. **Cài đặt OD vào image ACP sandbox**: thêm build step vào Dockerfile `bsm-superpower-acp-sandbox` (build OD từ source `pnpm --filter @open-design/daemon build` + web static export, hoặc copy `apps/daemon/dist` + `apps/web/out` từ stage build OD). Được phép vì đây là image inhouse tự chủ (spp repo control), không đụng image upstream.
2. **Env của OD trong container**: `OD_DATA_DIR=<riêng trong container>`, `OD_BIND_HOST=127.0.0.1` (chỉ nghe loopback trong container), `OD_PORT=<port riêng>`, `OD_SANDBOX_MODE=1`, `OD_SANDBOX_IMPORT_ALLOWED_ROOTS=<workspace dir trong container>` (chính là dir ACP đang bind-mount), `OD_API_TOKEN=<token per-workspace>`.
3. **Workspace dir dùng chung**: OD import chính thư mục mà ACP container đang bind-mount → file design OD ghi ra ACP agent thấy ngay qua filesystem (không qua mạng), và ngược lại. Zero network hop cho tương tác file.
4. **Agent tương tác trong cùng process tree**: OD daemon spawn opencode (có sẵn trong image) → agent chạy như child process của OD daemon → ghi file vào workspace dir. ACP agent (opencode/Claude Code riêng của ACP daemon) cùng mount workspace dir → đọc/ghi chung directory, không cần RPC/HTTP giữa 2 container.
5. **Gateway/proxy**: SPP backend truy cập OD qua `host.docker.internal:<port>` như hiện ACP; browser không truy cập trực tiếp OD (auth bridge 6.4, phương án A auth-proxy).
6. **Lifecycle**: start OD cùng entrypoint container (supervisor script / entrypoint.sh chạy daemon background), hoặc start lazy qua API admin của ACP daemon.

Lợi điểm của phương án B (tại sao đây là phương án đúng):
- Không thêm container per workspace — số container không đổi, không phải maintain lifecycle thêm.
- Workspace dir đã bind-mount sẵn — không cần mount thêm, không cần cross-container file sharing.
- opencode CLI đã có sẵn trong image → không cần build image OD+opencode riêng.
- Agent tương tác trong cùng 1 container → đơn giản hơn nhiều so với 2 container riêng biệt (không cần gọi qua mạng, không cần chia sẻ volume, không cần đồng bộ state).
- Network: OD nằm ngay trong ACP sandbox network — không cần port public thêm.
- Reuse entrypoint/lifecycle hiện có của ACP container.

Rủi ro / đánh đổi của phương án B (cần quản lý, nhưng không phải blocker):
1. **Blast radius tăng**: OD daemon hỏng/OOM có thể kéo cả ACP container (chat agent) sập theo. Giảm thiểu: giám sát mem/process; có thể set cgroup limit riêng cho OD process; POC-2b verify trước khi production.
2. **Mâu thuẫn resource**: mem limit ACP container hiện tại được sizing cho agent chat; thêm OD (heap 192MB + agent spawn) có thể cần nâng limit cho TẤT CẢ workspace kể cả workspace không dùng Design. Giảm thiểu: đo profile thực tế (POC-1/POC-2); chỉ bật OD khi workspace thực sự dùng (lazy start).
3. **Version coupling**: nâng OD (upstream release hàng tuần) = build lại image ACP sandbox = restart mọi ACP container đang chạy (mất session agent chạy dở). Giảm thiểu: pin version dài; nâng theo cửa sổ bảo trị; có thể tách OD thành layer riêng trong Dockerfile để cache tốt hơn.
4. **Node version coupling**: OD yêu cầu Node ~24 — trùng với Node 24 của ACP image hiện tại, nhưng nếu một bên nâng Node thì bên kia cũng kéo theo. Giảm thiểu: pin cả 2; upgrade cùng lúc có kiểm soát.
5. **Không khớp "sandbox gốc của OD"**: compose gốc của OD bật `read_only` rootfs + `no-new-privileges` + `pids_limit 256` — áp các ràng buộc này lên ACP container sẽ phá ACP (agent cần ghi workspace). Bỏ các ràng buộc này thì mất một lớp hardening OD standalone có sẵn. Giảm thiểu: OD tự có `OD_SANDBOX_MODE` env isolate agent home/config/tmp vào data dir — đây là lớp bảo mật chính, không phải container-level hardening.
6. **Session pool LRU của SPP (5 session/user)** không biết gì về OD — OD daemon phải do ACP container quản thêm 1 phụ thuộc runtime cần theo dõi riêng. Giảm thiểu: thêm health check + restart logic cho OD process trong entrypoint script.

**Khuyến nghị: B là phương án chính.** A (container OD riêng) chỉ là fallback khi blast radius hoặc version-coupling không chấp nhận được.

### 6.3 Workspace binding (ghim OD vào workspace)

Khi tạo container, SPP backend gọi đúng sequence OD API:

1. `POST /api/import/folder` với:
   - `baseDir`: `/data/workspace` — đường dẫn workspace dir **trong container** (đã bind-mount từ `${WORKSPACES_HOST_ROOT}/<slug>/<memberSlug>`);
   - `orchestratorWorkspace`: `{kind: "scratch", sourceLabel: "spp:<slug>", sourceRef: "<revision/timestamp>", writeback: "external"}` — ghi nhận provenance, OD biết workspace do orchestrator (SPP) sở hữu quyền writeback;
2. Env khóa phạm vi: `OD_SANDBOX_MODE=1`, `OD_SANDBOX_IMPORT_ALLOWED_ROOTS=/data/workspace` → mọi attempt import path khác bị OD tự từ chối (`sandbox-mode.ts:96-104`).
3. `baseDir` bất biến sau import (N2) → project không thể bị trỏ sang chỗ khác.

Kết quả: project OD duy nhất có ý nghĩa nghiệp vụ bị **ghim cứng** vào workspace dir; project "rác" (nếu user tạo trong UI) chỉ sống trong OD data dir của container đó, không chạm dữ liệu SPP.

### 6.4 Auth bridge (SPP → OD)

Vấn đề: OD chỉ hiểu single shared token (Bearer/Basic); SPP cần gate theo workspace membership và không lộ token ra browser.

Thiết kế:

1. Backend SPP: route `POST /api/workspaces/[slug]/design-session` — qua `requireWorkspaceMember` → sinh **token per-workspace** (random 32B, lưu Redis có TTL) → dùng làm `OD_API_TOKEN` khi tạo/kłą container OD.
2. Browser → OD: OD không nhận token qua query/cookie (chưa tìm thấy cơ chế này — cần verify POC Q1), iframe không set header được. Hai phương án:
   - **(A) — khuyến nghị v1**: chạy **auth-proxy sidecar nhỏ** (hoặc mở rộng OpenACP daemon) trước OD container: kiểm tra JWT `ba_token` của SPP (cùng `BA_JWT_SECRET` + membership claim) rồi forward kèm `Authorization: Bearer <od-token>` vào OD. Browser chỉ thấy proxy; OD token không rời server. OD bật `OD_DISABLE_API_AUTH=1` (mode được docs hỗ trợ chính thức cho reverse-proxy đã auth).
   - **(B)**: reverse-proxy ngay trong SPP frontend (mở rộng catch-all `[...path]`) inject Bearer — đơn giản hạ tầng, nhưng vướng xung đột prefix: OD UI gọi `/api/*` tuyệt đối trên origin của nó, trùng `/api/*` của SPP → chỉ khả thi nếu OD web hỗ trợ base-path (POC Q2).
3. `OD_ALLOWED_ORIGINS` set = origin SPP (khi nhúng iframe cross-origin, request `/api` từ iframe mang Origin của origin nhúng — cần allowlist origin SPP; verify hành vi này ở POC Q3).

### 6.5 Nhúng UI

- **Phương án A (khuyến nghị v1)**: route `app/w/[slug]/design/page.tsx` render iframe full-height trỏ đến OD URL per-workspace (port/proxy từ config hoặc port map backend); nav thêm 1 item `GlobalRail.tsx:365-375`. Lợi: OD tự quản toàn bộ state/routing bên trong iframe, không đụng build SPP; chi phí bảo trì thấp. Hạn chế: cross-origin (giải bằng `OD_ALLOWED_ORIGINS`), UI OD có topbar riêng (chấp nhận ở v1).
- **Phương án B**: path-prefix reverse proxy (`/design/*` → OD) — same-origin, đẹp hơn, nhưng phụ thuộc POC Q2 (base-path) và cần xử lý SSE qua proxy.
- **Phương án C (v2+)**: serve static export của OD web bởi chính SPP + custom fetch wrapper — kiểm soát UI sâu (ẩn Home/New Project, đúng yêu cầu "không chuyển workspace tự do" cả về UX), đổi lại chi phí maintain fork UI cao. Chỉ làm nếu A/B không đủ.

### 6.6 Agent runtime trong OD

- Build image `od + opencode`; daemon OD tự detect opencode qua PATH và dùng stream format `json-event-stream` (N1).
- API key per container (env, theo pattern ACP sandbox đang dùng `OPENROUTER_API_KEY`); sandbox mode của OD tự redirect HOME/config của opencode vào data dir → không đụng config host.
- Fallback: BYOK proxy mode (text-only, không filesystem tools) — chỉ dùng khi không thao tác được image; không phải trải nghiệm chính.
- Lưu ý khác biệt với ACP: hiện agent SPP chạy trong **ACP sandbox container riêng** do daemon Go quản; trong phương án này agent design chạy **trong OD container**. Nếu muốn agent design dùng chung ACP sandbox (1 container cho cả chat lẫn design), cần nghiên cứu thêm hướng OD runtime adapter (`acp-json-rpc`) trỏ ra ACP daemon — để v2, không block v1.

### 6.7 Dữ liệu & artifact

- OD data (SQLite, index, sandbox home) nằm trong volume riêng per container — mất container không mất file thiết kế (file nằm trong workspace dir).
- File design sinh ra ghi trực tiếp vào workspace dir (folder-backed) → **Files API của SPP và ACP agent thấy ngay**; SPP giữ quyền commit/push (writeback=external, đúng contract mục 3.2).
- Export HTML/PDF/PPTX/MP4 của OD ghi trong workspace → có thể expose qua Files API như artifact SPP.

### 6.8 Bảo mật (checklist)

- OD container KHÔNG public internet; chỉ network nội bộ + truy cập qua auth-proxy/SPP.
- Token per-workspace, TTL, xoay khi container tái tạo.
- `OD_ALLOWED_ORIGINS` = origin SPP.
- Rootfs read-only, no-new-privileges, pids_limit, mem_limit, tmpfs /tmp (theo compose gốc OD).
- OD tự chặn import system/credential dirs; workspace dir của SPP vốn chỉ chứa repo/file workspace nên rủi ro thấp; không mount `.claude`/credential của host vào OD container (khác ACP — vì OD có sandbox env riêng).
- Agent trong OD container có quyền ghi workspace dir — **cùng mức quyền** ACP sandbox hiện có, không mở rộng tấn công diện mới.

---

## 7. Rủi ro & hạn chế

| # | Rủi ro | Mức độ | Giảm thiểu |
|---|---|---|---|
| R1 | Không có single-project lock ở UI — user tạo project od-owned rác | Thấp (không đụng dữ liệu SPP) | Chấp nhận v1; v2 patch UI (phương án C) hoặc hướng dẫn |
| R2 | Auth browser trong iframe — OD không nhận token qua query/cookie (chưa verify) | Trung bình | Auth-proxy sidecar (6.4-A); POC Q1/Q3 |
| R3 | OD web chưa verify base-path support | Trung bình (chặn phương án B) | POC Q2; fallback phương án A |
| R4 | Upstream release hàng tuần, breaking change có thể xảy ra | Trung bình | Pin version; quy trình nâng có chủ đích + smoke test |
| R5 | Memory khi agent chạy trong OD container | Thấp | Limit 1-2GB; theo dõi; tách agent ra container riêng nếu cần (v2) |
| R6 | Image `od + opencode` phải tự build/maintain | Thấp | Dockerfile mỏng (FROM od + install opencode); CI build theo pin version |
| R7 | License khi redistribute vào customer release (`bsm-releases`) | Thấp | Apache-2.0 cho phép; giữ LICENSE/NOTICE attribution khi bundle image |
| R8 | SSE/static qua auth-proxy chưa verify hiệu năng | Thấp | POC Q4 đo trực tiếp |
| R9 | (Chỉ phương án B) OD daemon hỏng/OOM kéo sập ACP container (chat agent) theo | Trung bình | Chỉ chọn B nếu chấp nhận coupling; giám sát mem; fallback về A |
| R10 | (Chỉ phương án B) Nâng OD = build lại image ACP + restart mọi ACP container (mất session agent chạy dở) | Trung bình | Pin version dài; nâng theo cửa sổ bảo trì; hoặc chọn A |
| R11 | (Chỉ phương án B) Mất lớp hardening compose OD (read_only rootfs, no-new-privileges, pids_limit) khi áp lên ACP container | Thấp | Chấp nhận — ACP đã có isolation riêng; cân nhắc lại nếu security review yêu cầu |

---

## 8. Lộ trình POC (đề xuất)

| Bước | Nội dung | Thời lượng | Tiêu chí đạt |
|---|---|---|---|
| POC-1 | Chạy image OD local với `OD_SANDBOX_MODE=1` + `OD_SANDBOX_IMPORT_ALLOWED_ROOTS=<dir test>`; import folder; thử import path ngoài root (phải bị chặn); thử tạo project od-owned | 0.5-1 ngày | Lock hoạt động đúng; sandbox env đúng như code |
| POC-2 | Build image `od + opencode`; chạy 1 run thiết kế trong container; verify file ghi vào workspace dir | 0.5 ngày | Agent chạy end-to-end, file xuất hiện đúng chỗ |
| POC-2b | (Phương án B) Cài OD daemon vào copy của image ACP sandbox; chạy OD cạnh opencode cùng 1 container; verify OD daemon serve + agent run + không phá ACP entrypoint | 0.5-1 ngày | OD chạy trong ACP container, ACP agent vẫn chạy bình thường song song |
| POC-3 | Auth: verify Q1 (token qua query/cookie?), dựng auth-proxy sidecar kiểm tra JWT SPP → OD; nhúng iframe vào `/w/[slug]/design` (dev) | 1 ngày | Mở Design từ SPP UI, auth qua membership, không lộ token |
| POC-4 | Verify Q2 (OD web base-path), Q3 (Origin header từ iframe), Q4 (SSE qua proxy) | 0.5 ngày | Chốt phương án nhúng A hay B |

**Câu hỏi mở cần POC trả lời:**
- Q1: OD có chấp nhận token qua query param/cookie không? (nếu có → bỏ auth-proxy)
- Q2: OD web static export chạy được dưới base-path `/design/` không?
- Q3: Request từ iframe cross-origin (Origin = SPP) qua `OD_ALLOWED_ORIGINS` có đủ cho mọi API + SSE không?
- Q4: Hiệu năng SSE + static asset qua auth-proxy/Next route handler.

Sau POC: ghi quyết định kiến trúc vào ADR (docs/decisions/) và tạo task triển khai trong project.

---

## 9. Phụ lục — Danh mục bằng chứng

### Phía OpenDesign (N1 docs / N2 code clone main 24/09/2026)

| Nội dung | Bằng chứng |
|---|---|
| Docker 1 container serve API+UI | `deploy/README.md:3-5`; `docs/architecture.md` §1; `deploy/docker-compose.yml` |
| Image, port, mem, healthcheck, read_only | `deploy/docker-compose.yml:6,16-22,25-31,32-43` |
| Single-tenant token, bắt buộc khi bind public | `deploy/README.md:60-64`; `apps/daemon/src/server.ts:3152-3176`; `apps/daemon/src/api-token-auth.ts` |
| Origin allowlist | `apps/daemon/src/origin-validation.ts:15-29`; `server.ts:3475-3476` |
| Orchestrator workspace contract (doc) | `docs/orchestrator-workspaces.md` (toàn bộ) |
| Orchestrator workspace contract (code) | `apps/daemon/src/workspace-contract.ts:6-14,53,59,87-128` |
| baseDir chỉ set qua import/folder; bất biến | `apps/daemon/src/routes/project/index.ts:3876-3902, 5274`; `apps/daemon/src/import-export-routes.ts:344+` |
| Sandbox mode + allowed roots + env isolation | `apps/daemon/src/sandbox-mode.ts:6-7,37-49,67-104,106-128,162-195`; `daemon-paths.ts:125-133` |
| Import validation (realpath/root/data-dir/symlink) | `apps/daemon/src/import-export-routes.ts:283-311, 437-443` |
| Agent runtime theo PATH, 27 defs | `QUICKSTART.md:14-16`; `docs/agent-adapters.md` §1-3 |
| Image không bundle CLI; keys env; glibc | `deploy/README.md:91-93, 173-176, 186-192` |
| BYOK proxy text-only | `apps/daemon/src/routes/chat.ts:986+`; `apps/daemon/src/byok-tools.ts` |
| Web UI tách (3 output modes) | `apps/web/next.config.ts`; `docs/architecture.md` |
| Node ~24, footprint | `package.json` engines; `deploy/.env.example:29-31` |
| Không có single-project lock / multi-user | grep toàn bộ `apps/daemon/src` — không tìm thấy |

### Phía SPP (N3)

| Nội dung | Bằng chứng |
|---|---|
| Workspace = thư mục đĩa | `apps/backend/lib/workspace-setup.ts:42,157,185,521,747`; `openacp.ts:37-38,185`; `docker-compose.prod.yml:78` |
| Workspace model + membership | `apps/backend/lib/workspace.ts:269-313,346-374,382-410`; `permissions.ts:91-142`; `packages/shared/src/workspace-types.ts:25-33` |
| ACP qua daemon HTTP, container Go tạo | `openacp.ts:27-31,180-237,289,565+,596+,897,1350-1419`; `docs/superpower-os/12-architecture.md:515-517,1153-1159` |
| SSE streaming stack | `apps/backend/lib/chat-stream.ts:48`; `apps/frontend/app/w/[slug]/chat/useChatStream.ts:295,666`; `ChatPanel.tsx:372` |
| Catch-all proxy pattern | `apps/frontend/app/api/[...path]/route.ts` |
| Iframe pattern (stub) | `apps/frontend/app/components/canvas/nodes/LinkNode.tsx:60-320`; `lib/embeds.ts` |
| Auth middleware | `apps/frontend/middleware.ts` (ba_token, BA_JWT_SECRET) |
| Shell nhúng Design | `apps/frontend/app/w/[slug]/layout.tsx`; `GlobalRail.tsx:313-375,430+,627` |
| Agent per-workspace (opencode support) | `apps/backend/lib/acp-agent-settings.ts`; session-pool.ts |

---

*Hết báo cáo.*
