---

# 0. 总体目标与核心策略（定版）
**目标**

+ Web 端：注册/登录 → 创建 Task（编辑 YAML）→ 启动运行 → 实时看各阶段状态 → 查看/下载阶段 md + 其他产物（code/experiment/scripts 等）→ 提示词（system_message）版本化管理与选择运行版本

**核心策略（关键决策）**

1. **每次 Run 一个 Docker 容器**：解决并发、隔离、不同提示词同时运行的问题（你已确认 Docker 可用）。
2. **不改原 AI_Scientist 默认 prompts**：Web 后端保存每个账号的 PromptSet（仅 system_message），运行时在容器内“覆盖/优先加载”本次 run 生成的 prompts（仅容器内生效）。
3. **状态/阶段来源以 SQLite 为准**：沿用系统生成的 `proj_db_*.db`，从 `dbtask` 读 `id/stage/status/content/result_path` 给前端展示。

---

# 1. 仓库与服务拆分（你们需要新增的工程）
建议新建一个独立仓库（或同仓多目录）：

```plain
ai-scientist-web/
  backend/          # FastAPI + Celery Worker + Docker SDK
  frontend/         # Next.js
  infra/            # docker-compose / k8s manifests
  runner_image/     # AI_Scientist Runner 镜像构建（Dockerfile）
  shared/           # prompt 模板、yaml 模板（可选）
```

---

# 2. Runner 镜像：把运行说明里的“手工步骤”固化成可重复的容器
## TODO 2.1：制作 AI_Scientist Runner Dockerfile（一次构建，重复运行）
**依据运行说明**：项目目录 `/home/guv/AI_Scientist/`，依赖用 `uv sync` 同步。

- [ ] `runner_image/Dockerfile`：把 AI_Scientist 代码 COPY 进镜像（建议固定到某个 git commit）
- [ ] 在镜像 build 阶段执行 `uv sync`（避免每次 run 都 sync）
- [ ] 设定工作目录为 `/home/guv/AI_Scientist`
- [ ] 入口脚本 `entrypoint.sh` 接受参数：`YAML_PATH`、`PROJECT_ID`

> **验收**：在服务器上 `docker run ...` 能成功跑通 `uv run -m stages.manual_proposal ...` 并生成 `agent-service/datacache/.../proj_db_*.db`。
>

---

## TODO 2.2：定义“每个 Run 的挂载点”（保证所有产物落到宿主机 run 目录）
运行说明里产物关键路径：

+ DB：`agent-service/datacache/<username>/proj_db_*.db`（终端会打印路径）
+ md：`dbtask.result_path` 指向的文件
+ code：`./agent-service/datacache/<username>/code/task_id/`
+ experiment JSON：`./agent-service/datacache/<username>/experiment/task_id/`

**挂载建议（强烈推荐，最少改动）**  
对每个 run，宿主机准备目录：`/data/app/runs/{run_id}/`

容器启动时做 bind mount：

+ `-v /data/app/runs/{run_id}/initial_configs:/home/guv/AI_Scientist/initial_configs`
+ `-v /data/app/runs/{run_id}/datacache:/home/guv/AI_Scientist/agent-service/datacache`
+ `-v /data/app/runs/{run_id}/prompts:/home/guv/AI_Scientist/prompts`（仅容器内覆盖 prompts）
+ `-v /data/app/runs/{run_id}/logs:/logs`

这样：数据库、md、code、experiment 等所有输出都自动落在 `/data/app/runs/{run_id}/datacache/...`

> **验收**：run 结束后，宿主机 run 目录内能看到 `datacache/<username>/proj_db_*.db` 以及 md/其它产物。
>

---

## TODO 2.3：确定容器内启动命令（来自运行说明）
运行说明给出的核心启动：  
`uv run -m stages.manual_proposal -p <yaml> -i <project_id>`

你们文档里示例命令的 `-p/-i` 有轻微写法不一致之处（描述里说 `-p` 指向 `./initial_configs/challenge_test.yaml`，`-i` 是项目 id）。建议在容器里统一为：

- [ ] `uv run -m stages.manual_proposal -p ./initial_configs/{yaml_filename} -i {project_id}`

另外保留两个高级能力（后续做按钮即可）：

+ 失败 task 单独重跑：`uv run -m scheduler.worker --db <db> --id <task_id>`
+ 从 gen 继续 scheduler：`uv run -m scheduler.scheduler --db_path <db> --gen <gen>`

---

# 3. Web 后端：账号/任务/提示词/容器调度/产物服务
推荐栈：**FastAPI + PostgreSQL + Redis + Celery + Docker SDK**  
（Docker SDK 用于从后端启动 runner 容器；Celery 负责长任务）

## TODO 3.1：数据库表设计（最小闭环）
- [ ] `users`
    - id, email, password_hash, created_at
- [ ] `prompt_sets`
    - id, user_id, name, created_at
- [ ] `prompt_versions`
    - id, prompt_set_id, version, created_by, created_at, notes
    - payload(JSON): `{ "system_scientist": "...", "system_designer": "...", ... }`
- [ ] `runs`
    - id(run_id), user_id, created_at, updated_at
    - status: queued/running/completed/failed/canceled
    - yaml_path, prompt_version_id
    - container_id, exit_code
    - ai_username（写入 YAML 的 username，建议 = app 用户名或 user_id）
- [ ] `run_artifacts`
    - id, run_id, kind(md/db/log/code/experiment/json/other), stage, task_id, path, created_at

---

## TODO 3.2：后端核心 API（前端页面直接对接）
### Auth
- [ ] `POST /auth/register`
- [ ] `POST /auth/login`
- [ ] `GET /me`

### Prompts（只编辑 system_message）
- [ ] `GET /promptsets`
- [ ] `POST /promptsets`
- [ ] `GET /promptsets/{id}/versions`
- [ ] `GET /promptsets/{id}/versions/{version}`
- [ ] `POST /promptsets/{id}/versions`（保存新版本）
- [ ] `GET /promptsets/{id}/diff?v1=&v2=`（可选，后面做）

### Runs
- [ ] `POST /runs`
    - 入参：yaml_text / yaml_filename（或自动命名）、project_id（可用 run_id）、prompt_version_id
    - 行为：落盘 run 目录 → 写 YAML → 生成 prompts → 入队 Celery
- [ ] `GET /runs`（历史列表：ID/创建时间/最后修改/创建人/状态）
- [ ] `GET /runs/{id}`（详情：阶段状态、产物链接）
- [ ] `GET /runs/{id}/stages`（从 sqlite dbtask 查）
- [ ] `GET /runs/{id}/artifacts`（扫描并返回可下载列表）
- [ ] `GET /runs/{id}/download?path=...`（安全下载）
- [ ] `POST /runs/{id}/cancel`（停止容器）
- [ ] `GET /runs/{id}/events`（SSE：推送 stage/status/log 更新）

---

## TODO 3.3：prompts 生成（只让用户改 system_message）
你已经确定只编辑 `system_message`。建议做成“模板 + 注入”：

- [ ] 在 `runner_image/` 或 `backend/shared/` 放一份 **prompts 模板目录**（从现有 prompts 复制一份作为基线）
- [ ] 每次 run 开始：
    1. copy 模板 prompts → `run_dir/prompts/`
    2. 用后端存的 system_message 覆盖每个 `system_*.py` 里对应的 system_message 字段
        * 实现方式 A（快）：正则替换 `system_message: """ ... """` 区块
        * 实现方式 B（更稳）：模板里把 `system_message` 改为从 `prompts_data.json` 读取（推荐长期）
- [ ] 生成完成后，启动容器时把 `run_dir/prompts` mount 到容器 `/home/guv/AI_Scientist/prompts`

> **验收**：同一时间启动两个 run，选择不同 PromptVersion，生成的 md 内容确实不同（且互不影响）。
>

---

## TODO 3.4：Run Worker（Celery 任务）——启动容器、采集日志、落库
Worker 任务流程（可直接照这个写代码）：

- [ ] `create_run_workspace(run_id)`：
    - 创建目录：`initial_configs/ datacache/ prompts/ logs/`
- [ ] `write_yaml(run_id, yaml_text)` → 保存到 `initial_configs/{yaml_filename}`
- [ ] `render_prompts(run_id, prompt_version_payload)` → 生成 `prompts/`
- [ ] `docker_run_container(run_id)`：
    - image: `ai_scientist_runner:{tag}`
    - volumes: 按 2.2 挂载
    - env: `PROJECT_ID, YAML_FILENAME, AI_USERNAME`
    - command: `uv run -m stages.manual_proposal -p ./initial_configs/{yaml_filename} -i {project_id}`
- [ ] `stream_logs(container)`：stdout/stderr 写入 `logs/stdout.log`、`logs/stderr.log`
- [ ] `wait_container_exit`：
    - exit_code==0 → status=completed，否则 failed
- [ ] `post_index_artifacts(run_id)`：
    - 定位 sqlite：在 `datacache/**/proj_db_*.db` 搜索最新文件
    - 读 sqlite 的 `dbtask/dbproposal`，提取：
        * stage/status/task_id/content/result_path（用作详情页）
    - 将每个阶段 md 作为 artifact 记录
    - 将 `code/`、`experiment/`、`scripts/` 等目录作为 artifact 记录（如存在）

---

## TODO 3.5：阶段状态服务（直接复刻你 SQLite 插件看到的表格）
运行说明确认 `proj_db_*.db` 含 `dbtask`/`dbproposal` 两张表，且 `dbtask` 能看到 stage/status 及 result_path。

- [ ] `GET /runs/{id}/stages` 的实现：
    - 打开该 run 的 sqlite
    - `SELECT id, name, stage, status, content, result_path, updated_at FROM dbtask ORDER BY ...`
    - 返回 JSON 给前端（前端用表格展示）
- [ ] SSE 实时推送（最简单实现）：
    - 后端每 1s 轮询 sqlite 的 `dbtask`，如果某行 status/stage/content 有变化就推送事件
    - 事件类型：
        * `stage_update`：{task_id, stage, status, content_excerpt}
        * `artifact_ready`：{stage, url}

---

# 4. Web 前端：你描述的页面直接落地（Next.js）
## TODO 4.1：页面与组件（按你想要的 UI）
- [ ] `/login`、`/register`
- [ ] `/runs`：任务历史列表
    - columns：RunID、创建时间、最后修改、创建人、运行状态
    - actions：查看详情、取消（running 时）
- [ ] `/runs/new`：创建任务
    - YAML 编辑器（Monaco）
    - 选择 PromptSet/Version
    - 提交后跳转详情页并开始 SSE
- [ ] `/runs/[id]`：运行/历史详情
    - 顶部：基本信息（创建人、时间、prompt version、状态）
    - Stepper：Propose/Design/Challenge/Defense/Design(revised)…
    - 阶段表格：task_id/stage/status/content 摘要
    - 右侧：md 预览（点击某 stage 加载对应 md）
    - 下载区：md/db/log/code/experiment
    - 日志 Tab：stdout/stderr 实时滚动
- [ ] `/prompts`：提示词方案列表
- [ ] `/prompts/[id]`：提示词版本列表（创建人/时间/备注）
- [ ] `/prompts/[id]/edit`：编辑 system_message（按 agent 分栏）
    - 保存 → 新版本

---

# 5. 运维部署（docker-compose 一把梭）
## TODO 5.1：docker-compose（最小可跑）
- [ ] `postgres`
- [ ] `redis`
- [ ] `backend`（挂载 `/data/app` 到容器内同一路径）
- [ ] `frontend`
- [ ] （可选）`nginx` 反代 + HTTPS

## TODO 5.2：backend 启动 runner 容器的方式（两选一）
**方案 A（最快）**：backend 容器挂载 docker socket

- [ ] `-v /var/run/docker.sock:/var/run/docker.sock`
- [ ] 后端用 Docker SDK 创建 runner 容器

**方案 B（更安全）**：在宿主机跑一个 runner-daemon（后端通过 HTTP 让它起容器）

- [ ] 后端不接触 docker.sock

> MVP 建议先 A，之后再升级 B。
>

---

# 6. 测试清单（照这个验收就知道是否可上线）
## TODO 6.1：单用户跑通
- [ ] 注册登录
- [ ] 创建 PromptSet v1（默认 system_message）
- [ ] 创建 Run：粘贴运行说明里的 yaml 内容（content/hypothesis/proof 等）并启动
- [ ] Run 详情页能看到阶段状态变化（pending→completed/failed）
- [ ] 能打开 md 预览（来自 `result_path`）
- [ ] 能下载 sqlite/logs

## TODO 6.2：并发隔离
- [ ] 同时启动 Run A/B
- [ ] A 用 Prompt v1，B 用 Prompt v2（system_message 不同）
- [ ] 两个 Run 的 `datacache/`、`proj_db_*.db`、md 全部各自在自己的 run 目录中
- [ ] A/B 输出不串味（尤其 system_message 改动在输出中可观察）

## TODO 6.3：失败与重跑（可先做成“开发者按钮”）
- [ ] 人为制造一个失败（例如 prompt 写错导致 agent 崩）
- [ ] 前端显示 failed + 可查看 stdout/stderr
- [ ] 点击“重跑某 task”（调用 `scheduler.worker --db --id`）能跑出更完整错误（或成功）

---

