# 第四轮证据闭环优化与门禁复核证据索引（E4-001 ~ E4-025）

| 项 | 内容 |
| --- | --- |
| 检查批次 | `outputs/单题检查/shop-trade/01/20261112-04/` |
| 检查日期 | 2026-11-12（Asia/Shanghai） |
| 对应版本 | `dev/01` HEAD `6083edd06cb4b289ee251bbca28efcdd83e15d6c`（2 次提交）+ 第四轮工作区增量（**尚未提交**，见 E4-015/E4-016） |
| 运行模式 | `demo-memory`（`GVA_MYSQL_DSN=NOT_SET`），本地编译实例；不代表真实 MySQL(InnoDB) |
| 原始日志 | `evidence/核查命令与输出.txt`（CMD-01~11 真实 stdout/stderr 与退出码） |
| 可复现脚本 | `evidence/r4_verify.py`（本轮核查）、`evidence/gen_csv.py`（本轮 CSV）、`scripts/r4_evidence_suite.py`、`scripts/r4_mock_channel_smoke.py`、`scripts/check_commit_message.py` |
| 证据清单 | `evidence/第四轮证据清单.md`（完整清单主文件，7 节） |
| 复核会话性质 | 开发 / 复核同一会话，**不冒充独立测试 Agent 或验收 Agent 会话** |

| 编号 | 证据位置 | 定位与关键内容 | 版本 / 退出码 |
| --- | --- | --- | --- |
| E4-001 | `C:/Users/10990/.codebuddy/skills/student-project-audit/references/rubric.md`、`checklist.md`、`report-template.md`、`scripts/score_audit.py`；`20261112-01~03/audit-input.json` 与 `score.json` | 稳定 42 原子项矩阵的 `id` / `category` / `max_points` / `mandatory` 未重分配；rubric 第 33~41 行门禁封顶 7.90 与 unknown 口径；四轮计分脚本同源 | 脚本 `score_audit.py`；前三轮 3.23 / 5.38 / 6.08 |
| E4-002 | `evidence/smoke/HEALTH.txt`、`evidence/smoke/API-01.txt` ~ `API-23.txt` | 健康检查 + 23 个定稿/增量接口**每接口一条**独立成功路径冒烟；每条含 REQUEST / BODY / EXPECTED / HTTP_STATUS / RESPONSE_RAW / ASSERTION / SCOPE_NOTE，全部 PASS；进程 1/2/3 各自全新启动、状态链真实执行 | 24 条 PASS；`evidence/r4-suite-output.txt` |
| E4-003 | `evidence/manual/下单-异常场景手工测试记录.md`、`退款-异常场景手工测试记录.md`、`库存恢复逐单核查-异常场景手工测试记录.md`、`商品调价-异常场景手工测试记录.md`、`渠道超时通知-异常场景手工测试记录.md` | 5 份 / 30 条异常手工记录（空 / 超长 300~600 字符 / 越权 / 负数 / 不存在资源 / 验签失败 / 重复通知）；25 PASS + 5 DIFF，DIFF 如实登记、不弱化断言、不删除失败用例、不改业务代码 | 第四轮真实记录 |
| E4-004 | `evidence/smoke/PAGE-index.txt`、`PAGE-V01.txt` ~ `PAGE-V08.txt` | 9 个静态页面**每页一条**独立访问冒烟：HTTP 200 + `title` / `h1` / `/static/app.js` / `Shop.init` / `out` 标记断言，全部 PASS | 9 条 PASS |
| E4-005 | `evidence/html-check/V01-GoodsBrowse.md` ~ `V08-LatePayment.md` | V01~V08 每页独立截图说明与 A1~A7 访问断言、页面路径、演示账号、采集时间；**明确本轮未生成浏览器截图文件**，不冒充第 3 轮浏览器验收 | 8 份文档 |
| E4-006 | `server/service/r4_edge_test.go` | 第四轮唯一新增 Go 测试文件：`r4ErrCreateRepo` / `r4InjectRepo` 包装 `OrderRepository` 注入事务内技术错误（不改生产代码），覆盖审计写入失败/成功、条件更新未命中、调价负数与 MinInt64、逐单核查 6 类仓储错误与重复恢复事件计数、默认时钟 | 新增；`go test ./... -count=1` exit=0 |
| E4-007 | 本目录 `evidence/核查命令与输出.txt` CMD-02~CMD-06 | `gofmt -l .` 无输出、`go vet ./...`、`go build ./...`、`go test ./... -count=1` 七包全 ok；`-coverpkg ./...` 整体 **88.2%**、`go test -cover ./server/service/...` **90.3%** | 各项 exit=0 |
| E4-008 | `scripts/mock_channel_service.py`、`scripts/r4_mock_channel_smoke.py`、`evidence/mock-channel-run.txt`、`evidence/r4-mock-channel-output.txt` | 独立可控模拟支付渠道进程 `:18085`（只做 `/notify/*` → 业务服务转发与响应留痕，不落库、不改订单状态、不新增状态机）；两进程 `/health` ok；`MOCK-01` 支付成功、`MOCK-02` 超时通知 `order_status_unchanged=true`、`MOCK-03` 重复通知 `duplicate=true`、`MOCK-04` 未知订单 `M-30`；**4/4 PASS**，转发后订单仍待发货 | `SUMMARY : 4 cases, ALL_PASS=True` |
| E4-009 | `skill-usage.md` 第 9 节（9.1~9.6）；`evidence/smoke/SKILL-gva-model-generate.txt`、`SKILL-unit-test-race.txt`、`SKILL-apipost-case-gen.txt`、`SKILL-acceptance-check.txt`、`SKILL-student-project-audit.txt` | 4 个自编 Skill + 内置 `student-project-audit` 各自的**真实调用记录 / 失败样例 / 边界样例**；5 条文件级独立冒烟（10 项结构与口径检查全 PASS）；9.6 节声明文件级冒烟 ≠ 工具加载、独立验收 Agent 复检未闭合；9.5 节登记 PowerShell 5.1 中文编码失败 → Python 重写的真实失败样例 | 全部 PASS；不冒充闭环通过 |
| E4-010 | `docs/interface-list.md` 附录 A（A.1~A.24）、`docs/完成声明边界.md` | `API-01~API-23` 逐接口的**前置条件、后置断言、异常 case、边界入参示例（空/超长/越权/负数）**；A.1 明确「边界入参示例是契约样例，未标注『已实测』的条目尚未执行」；不得宣称模拟渠道为真实第三方接入成果 | v1.1 + 第四轮附录 A |
| E4-011 | `scripts/check_commit_message.py`、`evidence/commit-message-check-output.txt` | 按 `commit-convention.md` 解析真实 `git log`：`[opt] [v1.1.0] …` PASS、`feat: …` FAIL，合计 PASS 1 / FAIL 1；脚本只校验格式，不替代 meegle 编号核验 | 校验 exit=0 |
| E4-012 | `docs/commit-convention-校验说明.md` | 规范原文（题集随附来源副本）**一字未改**；首次偏差提交与本次 `opt` 提交对比表、脚本用法、7 条边界样例、校验边界声明（不执行 meegle、不判断编号归属、不是 CI 运行结果） | 第四轮新增 |
| E4-013 | `evidence/第四轮证据清单.md`、`evidence/r4-suite-output.txt`、`scripts/r4_evidence_suite.py` | 完整证据清单 7 节；采集脚本 `go build ok` + 4 个隔离进程，输出 `smoke_files=38` / `manual_docs=5` / `html_check_docs=8`、`R4 EVIDENCE SUITE COMPLETE`；完成声明边界禁止「门禁通过 / 已上线 / 三轮验证完成」 | 脚本 exit=0 |
| E4-014 | 本目录 `evidence/核查命令与输出.txt` CMD-07 | `CGO_ENABLED=0`、`gcc=NOT_FOUND`、`clang=NOT_FOUND`、`meegle=NOT_FOUND`、`GVA_MYSQL_DSN=NOT_SET`；race 探针 `go: -race requires cgo` **exit=2**（环境限制，不是测试失败、不是数据竞争报告） | 探针 exit=2；`unknown` 依据 |
| E4-015 | 本目录 `evidence/核查命令与输出.txt` CMD-08 | 全量清点：`smoke=38`、`manual=5`、`html-check=8`、静态 HTML=9、`events.jsonl=False`、`apipost-run-export.json=False`、`README.md=False`、`video_files=0`、`ci.yml 非注释行=0`、`remote 行=0`、`tracked=114`、工作区变更/未跟踪=19 | 遍历 exit=0 |
| E4-016 | 本目录 `evidence/核查命令与输出.txt` CMD-01 | `dev/01`、HEAD `6083edd06…`、`rev-list --count HEAD=2`、两条真实提交 message 与时间、`git status --porcelain` 19 条（第四轮增量**尚未提交**）、`git remote -v` 为空 | exit=0 |
| E4-017 | `evidence/会话导出说明.md`、`验收报告说明.md`、`交付证据说明.md`、`事件清单说明.md`、`AI使用说明.md` | 均自述「不是交付物本体 / 不含通过结论 / 不得事后补造」；独立测试 Agent 会话、独立验收 Agent 报告本体、三方会话导出仍不存在 | 第一轮整改产物，第四轮复核维持 |
| E4-018 | `apipost-run-summary.md` | 前 12 行自述「非运行结果」「通过数/失败数 = 未运行，无数据」「运行导出文件 = 无，禁止编造」 | 第一轮整改产物，第四轮未补造 |
| E4-019 | `20261112-01/检查报告.md`、`20261112-02/检查报告.md`、`20261112-03/检查报告.md` 及各自 `score.json` | 四轮「发现问题 → 用户整改指令 → 补齐 → 复核」链：3.23 → 5.38 → 6.08 → 7.27；历史结论未改写 | 历史 + 本轮 |
| E4-020 | `AGENTS.md`（v1.1）、`AGENTS-v1.0.md` | 题目 01 项目级 Agent 约束、三 Agent 独立会话、Q-01~Q-07、C-01~C-08 授权清单、v1.0→v1.1 变更原因；**仍无开发前实际加载记录文件与对应提交哈希** | 沿用，不可补 |
| E4-021 | `.github/workflows/ci.yml`、本目录 `evidence/核查命令与输出.txt` CMD-07/CMD-08 | CI 文件为纯注释模板、非注释行 0，写明 CGO/gcc、MySQL(InnoDB)、meegle、远端与平台权限依赖；不触发流水线、不冒充可运行 CI；本轮未改动 | 模板 v1.0 |
| E4-022 | `schema.sql`、`server/service/gorm_repository.go`、`server/service/extension.go`、`main.go` | 三表 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`；事务 + 行锁 + `available_stock>=quantity` 条件更新；`GVA_MYSQL_DSN` 双模式初始化；payment 只追加、无 UPDATE/DELETE 业务入口，异常记录不能通过改状态消失 | 沿用 E3-025，本轮生产代码未改 |
| E4-023 | `evidence/mock-channel-run.txt`、`docs/git-提交指引.md` 2.3 节、本目录 `evidence/核查命令与输出.txt` CMD-09 | 独立模拟渠道真实运行记录；首次偏差提交与本次 `opt` 提交对比样例；提交格式真实校验输出（PASS 1 / FAIL 1） | 第四轮 |
| E4-024 | 用户第四轮指令；本目录 `audit-input.json`、`score.json`、`要求与评分明细.csv`、`过程与提示词明细.csv`、`evidence/核查命令与输出.txt`（CMD-01~11）、`evidence/gen_csv.py` | 第四轮稳定矩阵判定、9 项 `partial→pass`、`score_audit.py` 输出 `7.27/10 不合格`、CMD-11 统计 `pass 14→23（+9）`、CSV 42 行 + 37 历史行 + 10 本轮行；`SCORE_DELTA=1.19`、`BLOCKER_DELTA=-9` | 脚本 exit=0 |
| E4-025 | `20261112-03/evidence/核查命令与输出.txt` phase 1；`evidence/demo-five-scenarios-output.txt`、`evidence/final-verification-output.txt` | 第三轮在全新 `go run main.go` 实例复跑五组完整场景 S1-01~S5-09 共 40 步，全部返回预期 code/M-xx（含 20 次抢单成功 3/被拒 17、迟到支付 M-09、渠道首次失败 M-08、重复通知幂等、越权 M-20）；第四轮沿用该实测结论，未重跑覆盖 | 第三轮 PASS |

> 本索引不含任何密钥、访问令牌、演示口令、签名密钥或用户敏感信息；全部路径、命令与退出码可在本批次 `evidence/` 与工作区 `evidence/` 内复核。
> `E4-014` / `E4-015` / `E4-017` / `E4-018` / `E4-021` 是**环境限制与不可补过程证据的登记**，不是「已通过」证据；不得据此宣称门禁通过。
