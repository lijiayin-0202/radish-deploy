# 第二轮门禁复核 证据索引（E2-001 ~ E2-023）

| 项 | 内容 |
| --- | --- |
| 检查对象 | `shop-trade` 题目 01，`dev/01` 提交 `6cc6f134ee071e0a1cb8e71f03f824a178a249e0` |
| 检查日期 | 2026-11-12（北京时间 Asia/Shanghai） |
| 版本对应 | 全部证据绑定上述 HEAD；检查前 `git status --short --branch` 输出 `## dev/01`（工作区干净），检查产物写入本目录后新增未跟踪文件 |
| 证据性质 | 第二轮复核的原始命令输出、文件定位与全量清点记录；不含密钥、访问令牌或用户敏感信息 |

| 编号 | 类型 | 源路径 / 命令 | 定位与版本 | 引文 / 退出码 | 支持或反驳 |
| --- | --- | --- | --- | --- | --- |
| E2-001 | 题面与规范 | `C:/Users/10990/.codebuddy/skills/student-project-audit/references/source-manifest.json`、`assignment.md`、`commit-convention.md`、`rubric.md`、`checklist.md`、`report-template.md`、`prompt-audit.md`、`scripts/score_audit.py` | 快照 2026-11-11；sha256 `4e49fcd8…` / `8db6fcd…` | 固定权重 A1 3.00 / A2 1.80 / A3 1.70 / A4 1.50 / B1 0.60 / B2 0.80 / B3 0.30 / B4 0.30 | 评分规则与格式依据；第二轮沿用 |
| E2-002 | Git 核查 | `git -C d:/Desktop/shop log -1 --format='%H | %s | %cI'`、`rev-parse HEAD`、`branch --show-current`、`status --short --branch`、`remote -v`、`rev-list --count HEAD` | HEAD 全库 | `6cc6f134ee071e0a1cb8e71f03f824a178a249e0 | feat: 电商订单售前退款完整业务实现 | 2026-11-12T12:44:01+08:00`；`dev/01`；`## dev/01`；remote 空；commit count=1 | 支持「有效 HEAD 与版本链存在」；反驳「分阶段真实提交历史已具备」「已有 PR/远端」 |
| E2-003 | 启动实测 | `Start-Process go run main.go` + `Invoke-RestMethod /health` + `/api/v1/me` | 第二轮全新进程，pid 见核查日志 | `health={"mode":"demo-memory","status":"ok"}`；`me={"code":"0","message":"ok","data":{"account":"buyer01","role":"买家","user_id":1001}}`；`health_ok=True` | 支持 `go run main.go` 直接启动、健康接口、身份解析 |
| E2-004 | 五组场景实测 | `& ./scripts/demo-five-scenarios.ps1` 对 E2-003 的实例执行 | 同一 go run 实例 | 40 个步骤全部返回预期 `code`；含 `M-19/M-10/M-22/M-08/M-09/M-28/M-29/M-30/M-20`；末行「五组场景 HTTP 演示结束」 | 支持五组场景接口可用、角色闭环、异常与竞争裁决；反驳「无可运行业务接口」 |
| E2-005 | 质量复跑 | `gofmt -l .` / `go vet ./...` / `go build ./...` / `go test ./... -count=1` / `go test -coverprofile "$env:TEMP/r2-service.out" ./server/service/... -count=1` / `go test -coverpkg ./... -coverprofile "$env:TEMP/r2-all.out" ./... -count=1` / `go test ./server/service/... -race -count=1` | 临时 profile，未改写学生文件 | gofmt/vet/build/test exit=0；service `87.7%`；整体 `total: 86.0%`；race `go: -race requires cgo`，exit=2 | 支持格式/静态/单测/覆盖率草稿达标；证明 race 失败为环境前置缺失而非测试失败 |
| E2-006 | Skill 记录 | `d:/Desktop/shop/skill-usage.md` | 第 11、20~25、34~39、48~53、61、73、77~89 行 | 六类说明 ①技能用途 ②触发条件 ③输入 ④输出产物 ⑤验收检查点 ⑥禁用场景；3 个自编 Skill 逐项齐全；第 5 节 8 行调用；第 6 节闭环；第 7 节缺口 | 支持 R-B3-03 pass；反驳「六类说明缺失」 |
| E2-007 | 接口清单 | `d:/Desktop/shop/docs/interface-list.md` | 第 1~3、15、25~48、50~58 行 | 「状态：**已定稿并与实现一致**」；`API-01`~`API-20`；`X-Demo-Account`；五组场景接口序列；`docs/interface-list-draft.md` 不再作为用例依据 | 支持定稿接口清单与实现对齐 |
| E2-008 | 文档清点 | `list_dir d:/Desktop/shop/evidence`、`d:/Desktop/shop/docs` | evidence 12 文件、docs 5 文件 | 5 份说明文档（交付证据/验收报告/会话导出/事件清单/AI使用）+ 7 份原始输出；docs 含完成声明边界、git-提交指引、interface-list 定稿 | 支持 evidence 全套说明文档存在；同时证明文件性质为「说明」而非会话导出/验收报告本体 |
| E2-009 | 测试报告 | `d:/Desktop/shop/test-report.md` | 第 1~21 行及第 3、5、7、8 节 | 「草稿覆盖率」87.7%/86.0%；「真实环境覆盖率」尚未产生；`$env:CGO_ENABLED = "1"` + `go test ./... -race -count=1`；D-01~D-08 | 支持缺陷 2 整改；明确报告自述为开发草稿、非正式第 1 轮证据 |
| E2-010 | Apipost 状态 | `d:/Desktop/shop/apipost-run-summary.md`、`apipost-collection.json` | 第 1~18 行；JSON 解析 | 「通过数/失败数：**未运行，无数据**」；「无 `apipost-run-export.json`」；`json_ok`，5 组场景 | 反驳「第 2 轮已运行」；支持用例已基于定稿重建 |
| E2-011 | race 原件 | `d:/Desktop/shop/race-output.txt`、`evidence/final-verification-output.txt`、`scripts/run-race.ps1` | 第 8 节 race 探针 | `-race requires cgo; enable cgo by setting CGO_ENABLED=1`，exit=2 | 环境缺失项依据，不判代码缺陷 |
| E2-012 | 环境核查 | `go env CGO_ENABLED`、`Get-Command gcc/meegle`、`[bool]$env:GVA_MYSQL_DSN`、`Test-Path .github/workflows / Dockerfile`、递归统计 `*.html` / `*.jsonl` / 视频 | 第二轮命令组 2 | `CGO_ENABLED=0`；`gcc=NOT_FOUND`；`GVA_MYSQL_DSN_set=False`；`meegle=NOT_FOUND`；`workflows=False`；`Dockerfile=False`；`html_count=0`；`jsonl_count=0`；`video_count=0` | 支持四类环境限制识别；支持页面/事件清单/视频成果缺失 |
| E2-013 | 数据层 | `d:/Desktop/shop/schema.sql`、`server/service/gorm_repository.go` | 第一轮已核，第二轮延续 | 三表 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`；`Clauses(clause.Locking{Strength:"UPDATE"})`；`available_stock >= ?` 条件更新 | 支持持久化设计存在；不能替代真实 MySQL 运行证据 |
| E2-014 | 声明边界与 Git 指引 | `d:/Desktop/shop/docs/完成声明边界.md`、`docs/git-提交指引.md` | 完成声明边界第 21~34 行；Git 指引第 1~2 节 | 「本轮允许的表述：整改完成…」「禁止：门禁全部通过」；第 2.1 节登记 message 格式、缺版本号/编号、未 meegle 核验、混合类型 | 支持「未伪造完成声明」；支持提交格式偏差如实披露 |
| E2-015 | 第一轮基线 | `outputs/单题检查/shop-trade/01/20261112-01/audit-input.json`、`score.json`、`检查报告.md` | 42 原子项，3.23/10 不合格 | pass 1 / partial 23 / fail 18；A1 1.35、A2 0.75、A3 0.68、A4 0.00、B1 0.10、B2 0.20、B3 0.15、B4 0.00 | 第二轮评分矩阵与权重保持稳定；整改输入依据 |
| E2-016 | 身份与接口实现 | `server/api/v1/order.go`、`views.go`、`server/router/order.go` | 第二轮复核 | `demoAccounts` 7 个账号；`X-Demo-Account` 映射；21 条路由；统一 `code/message/data` | 支持角色、越权与接口实测结果的来源 |
| E2-017 | Agent 约束 | `d:/Desktop/shop/AGENTS.md`、`AGENTS-v1.0.md`、`.agent/01~06` | v1.0/v1.1 | 三 Agent 会话隔离、可修改范围、门禁、P-01~P-08 | 支持约束文件存在；无独立加载记录 |
| E2-018 | 自编 Skill | `d:/Desktop/shop/.codebuddy/skills/*/SKILL.md` | 3 个 v1.0 | 用途/触发/输入/步骤/输出/失败处理/完成标准齐备；无验收检查 Skill | 支持 R-B3-01 部分完成 |
| E2-019 | 假设清单 | `d:/Desktop/shop/docs/dev-assumptions.md` | A-DEV-01~16 | 记录接口草案、CGO/race 限制、覆盖率口径、演示仓储等 | 支持假设与授权有记录 |
| E2-020 | 交付证据说明 | `d:/Desktop/shop/evidence/交付证据说明.md` | 第 1~8 节 | E-01~E-15 状态表；meegle 核验流程；PR 合并流程；CI/CD 流程；GitHub MCP 流程；「无远端」；脱敏要求 | 支持流程说明齐全；反驳「已有 PR/CI/部署记录」 |
| E2-021 | 过程说明文档 | `evidence/会话导出说明.md`、`事件清单说明.md`、`AI使用说明.md`、`验收报告说明.md` | 各文件标题与第 1、3 节 | 均声明「非交付物本体」「不含通过结论」「未生成 events.jsonl」「独立会话未建立」 | 支持部分整改；反驳「会话导出/事件清单/验收报告已交付」 |
| E2-022 | 历史接口草案 | `d:/Desktop/shop/docs/interface-list-draft.md` | 全文 | 保留为历史版本，不再作为用例依据 | 支持定稿取代草案 |
| E2-023 | 覆盖率原件 | `d:/Desktop/shop/coverage.out`、`coverage-all.out`、`coverage-report.md`、`gofmt-vet-output.txt` | 学生产物（未改写） | service 87.7%、整体 86.0% | 支持草稿覆盖率数值；非正式验收证据 |

## 未运行 / 未访问 / 未播放清单

| 项 | 原因 | 影响 |
| --- | --- | --- |
| `CGO_ENABLED=1 go test ./... -race` | 本机 `CGO_ENABLED=0`、无 gcc/clang | R-A3-03 记 unknown，第 1 轮门禁未通过 |
| 真实 MySQL(InnoDB) 测试库 | `GVA_MYSQL_DSN` 未设置、无实例 | 持久化、行锁、唯一键冲突与重启后查询证据缺失（R-A2-01/03/04） |
| `meegle workitem get ... --project-key r17te9` | CLI 未安装、无权限 | R-B4-03 记 unknown，编号核验不可核实 |
| GitHub MCP 建仓 / PR / CI / 部署 / 冒烟 | 无远端、无平台权限、无流水线配置 | R-B1-04、R-B4-01、R-A4-03/04 |
| Apipost 第 2 轮运行导出 | 第 1 轮门禁未通过，按三轮顺序不得开始 | R-A3-05、R-A4-01 |
| 视频播放与群提交 | 无视频/图片/音频、无群凭据 | R-A4-05 |
| 独立测试 Agent / 验收 Agent 会话 | 本轮复核与开发过程在同一会话，无导出 | R-B1-02/03、R-A3-05 |
