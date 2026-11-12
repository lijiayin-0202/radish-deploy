# 证据索引（检查批次 20261112-01）

时区：北京时间（Asia/Shanghai）。检查日期：2026-11-12。所有路径相对 `d:/Desktop/shop`，除非注明绝对位置。
证据均为本次检查实际读取或执行的材料；学生文档与 Agent 自述只作线索，已向源码、命令输出或 Git 状态交叉核查。

| 编号 | 类型 | 源路径 / 定位 | 版本 / 时间 | 精简引文、命令或退出码 | 支持或反驳 |
| --- | --- | --- | --- | --- | --- |
| E-001 | 教师题面 | `C:/Users/10990/.codebuddy/skills/student-project-audit/references/assignment.md` 第 11–183 行（共同要求）、185–230 行（题目 01）；`references/source-manifest.json` | 快照 2026-11-11，sha256 `4e49fcd8…` | 「必须使用数据库保存核心业务数据」「必须实现可操作的最小业务页面」「整体 ≥85%」「开发前经 GitHub MCP 创建」「五组完整工作场景」 | 判定依据；用于核对所有 A/B 要求 |
| E-002 | 提交规范 | 工作区 `commit-convention.md`；技能内置 `references/commit-convention.md` | 快照 2026-11-11，sha256 `8db6fcd…` | `[类型] [版本号] [需求/Bug编号] 中文描述`；`feat/fix` 编号必填；`meegle workitem get … --project-key r17te9` | B4 判定依据 |
| E-003 | 全量清点 | `Get-ChildItem -Recurse -File -Force`，排除 `.git/` | 2026-11-12 检查时 | 共 41 个文件；`*.html` 0、`*.yaml/yml` 0、视频/图片 0；无 `main.go`、无 router、无 Dockerfile、无 `.github`、无 README | 反驳「可运行交付/页面/CI/视频」；支持 A4 全类 fail |
| E-004 | Git 状态 | `git rev-parse --verify HEAD`、`git log --oneline --all`、`git branch -a`、`git remote -v`、`git status --short`、`.git/HEAD` | 2026-11-12 检查时 | `fatal: Needed a single revision`；log/branch/remote 均无输出；`.git/HEAD: ref: refs/heads/dev/01`；status 26 行全 `??` | 反驳「分阶段提交/PR/合并/远端仓库」 |
| E-005 | 构建核查 | `go list -f '{{.Name}} {{.ImportPath}}' ./...`、`go build ./...` | 2026-11-12 复跑 | 4 个包均为库包（v1/global/model/service），无 `main` 包；`build_exit=0` 但不生成可执行文件 | 反驳「服务可启动」 |
| E-006 | 独立复跑（只读） | `gofmt -l .`、`go vet ./...`、`go test -cover ./... -count=1` | 2026-11-12 复跑，未写学生文件 | `gofmt_exit=0`；`vet_exit=0`；`test_exit=0`；`service 85.3%`，`api/v1 0.0%`，`model 0.0%`，`global [no test files]` | 支持 R-A3-04 pass；支持 R-A3-02 数值 |
| E-007 | race 原始输出 | `race-output.txt` 第 3–7 行 | 2026-11-12 | `CGO_ENABLED=0`；`go: -race requires cgo; enable cgo by setting CGO_ENABLED=1`；`race-exit=2`；文件自述「PR 门禁中的并发竞争检测项为未通过」 | 反驳 R-A3-03；支持门禁未通过 |
| E-008 | 覆盖率原件 | `coverage.out`、`coverage-all.out`、`coverage-report.md` | 2026-11-12 | service 85.3%；`-coverpkg=./...` total 85.2%；`gorm_repository.go` 由 sqlmock 覆盖，未排除自编 DAO | 支持 R-A3-02 部分；报告自述「草案」 |
| E-009 | 测试报告 | `test-report.md` 标题、第 1/3/5 节 | 2026-11-12 | 标题「开发 Agent 会话产物，不是第 1 轮正式证据」；D-01~D-04 自检修正；第 5 节列阻塞项 | 反驳独立测试 Agent 阶段；支持 B1-06 部分 |
| E-010 | Apipost 状态 | `apipost-run-summary.md` 表格与第 2 节 | 2026-11-12 | 「未运行，无数据」「无 Apipost 运行标识」「未生成 apipost-run-export.json」 | 反驳第 2 轮接口自动化完成 |
| E-011 | Apipost 用例 | `apipost-collection.json`（本次 `ConvertFrom-Json` 校验） | 2026-11-12 | `scenarios=5`、`cases=48`、`status=未运行；不得作为第 2 轮接口自动化证据`；格式说明为非官方导出格式 | 支持用例草案存在；反驳用例已运行 |
| E-012 | 数据库初始化 | `schema.sql` 第 1–121 行（尤其 115–121 演示数据） | 2026-11-12 | 3 表 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`；演示数据仅 2 个商品，无用户/账号表，无 3 买家与员工账号 | 支持 A2-01/03 部分；反驳 A2-02 |
| E-013 | 原型文档 | `题目01-…-原型设计文档.md` 第 5–13 行、17–32 行 | v1.0 | 「原型形态：轻量可操作 HTML 原型；本文档只说明页面结构」「不产出前端 HTML 代码」；PT-05「不得用静态页面、写死成功结果或文档说明代替」 | 与 E-003（0 个 HTML）共同反驳可操作原型 |
| E-014 | 接口与骨架 | `docs/interface-list-draft.md` 第 3、8、11 行；`server/api/v1/health.go` | 2026-11-12 | 「本文件不是已定稿接口设计，不生成 API/Router 代码」；`X-Role`/`X-User-Id` 为假设「不代表真实鉴权实现」；health.go 仅返回 `{"status":"ok"}` | 反驳业务接口与服务端身份解析 |
| E-015 | Agent 约束 | `AGENTS.md`（v1.1，第 0/1/2/5/7 节）、`AGENTS-v1.0.md` | 2026-11-12 | v1.1 Q-01 为 MySQL(InnoDB)；版本历史行写「本轮不提交」；1.1 要求三 Agent 独立会话、2.5 列 PR 门禁 | 支持 B2-01 部分；反驳「已按门禁执行」 |
| E-016 | 项目规则 | `.agent/01`~`06`，尤其 `05-testing-acceptance.md` 第 7–19、39 行 | 2026-11-12 | 三轮强制验证顺序不可跳过；第 39 行「预置 3 个买家、运营、仓库、客服账号」 | 判定依据；与 E-012 冲突 |
| E-017 | Skill 记录 | `skill-usage.md` 第 1–15 行 | 2026-11-12 | 8 行调用记录，列为「时间/Skill/调用目的/产出位置/证据状态」；末行声明草案性质 | 支持 B3-02/03 部分；缺题面六项说明 |
| E-018 | 自编 Skill | `.codebuddy/skills/{gva-model-generate,unit-test-race,apipost-case-gen}/SKILL.md` frontmatter 与正文 | 2026-11-12 | 三者用途分别为模型&DDL 生成、单测 race、Apipost 用例生成；均含用途/触发/输入/步骤/输出/失败处理/完成标准 | 支持 B3-01 结构；反驳「存在验收检查 Skill」 |
| E-019 | 假设与授权 | `docs/dev-assumptions.md` 第 5–20 行 | 2026-11-12 | A-DEV-07「产物仅为草案」；A-DEV-11「不提交、不推送、不创建远端」；A-DEV-09「本机 CGO_ENABLED=0」 | 支持多项 partial 的自述；反驳 MCP 建仓/提交 |
| E-020 | 阶段文档 | 需求文档、原型设计文档、任务规划文档 v1.1 | 2026-11-12 | 三份 Markdown 说明文档存在，任务规划 v1.1 含 8.3 核查表 | 支持 B1-01 部分；非可操作原型 |
| E-021 | 缺失证据搜索 | 全库按扩展名/名称模式检索 `mp4/mov/avi/mkv/png/jpg/pdf/yml/yaml/jsonl/log/csv`、`README|Dockerfile|session|会话|验收|部署|deploy|pipeline|meegle|PR|视频|群` | 2026-11-12 检查时 | 仅命中 `.git/hooks/*.sample`；无会话导出、事件清单、AI 使用说明、验收报告、CI/CD、部署记录、meegle 输出、MCP 建仓记录、视频、群提交 | 支持 A4/B1/B2/B4 多项 fail，注明为「全量定位后确认不存在」 |
| E-022 | 业务源码 | `server/service/order_service.go`（16 个方法）、`gorm_repository.go`、`types.go` | 2026-11-12 | `SELECT … FOR UPDATE`、`available_stock >= ?`、`stock_restored = 0`、`BizError{Commit:true}`、`duplicateRejectPayment` | 支持 A1/A2 多项「逻辑代码存在」的部分完成 |
| E-023 | 测试源码 | `server/service/{order_service_test,order_service_branches_test,gorm_repository_test,memory_repository_test}.go` | 2026-11-12 | 20 并发抢 5 件、sqlmock 覆盖 25 个仓储方法、迟到支付不二次恢复等断言 | 支持 A3-01 部分；草案夹具不替代真实 MySQL |
| E-024 | 身份与越权 | `docs/interface-list-draft.md` 第 8 行；`server/service/types.go` `Actor{UserID,Role}`；E-005（无 HTTP 层） | 2026-11-12 | 身份由调用方直接传入结构体，无请求层与服务端会话 | 反驳 A2-05 的「改请求编号不能越权」可验证性 |
| E-025 | 检查环境 | 本机 Windows PowerShell；`python --version` = 3.14.8；Go 工具链；E-007 的 `CGO_ENABLED=0` | 2026-11-12 | 计分脚本 `python scripts/score_audit.py` 正常执行，输出 `3.23/10 不合格；原始分 3.23` | 说明检查能力边界；未运行学生服务（无入口）、未播放视频（无文件）、未访问教师平台 |

## 本次未执行 / 未访问 / 未播放清单

- 未运行学生服务：无 `main` 包与启动入口（E-005），因此无法做启动、数据库初始化、角色操作与重启持久化验证。
- 未连接真实 MySQL(InnoDB)：工作区无数据库配置与连接初始化，检查者未创建或改动任何真实数据。
- 未播放讲解视频、未查看群提交：全库无媒体文件与群记录（E-003、E-021）。
- 未访问 GitHub / 飞书 meegle / CI 平台：本次仅做本地只读核查（E-004、E-021）；教师平台事件不在工作区材料内。
- 未读取任何真实凭证；证据索引不含密钥、令牌或用户敏感信息。
