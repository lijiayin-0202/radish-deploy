# 第三轮门禁复核证据索引（E3-001 ~ E3-025）

| 项 | 内容 |
| --- | --- |
| 检查批次 | `outputs/单题检查/shop-trade/01/20261112-03/` |
| 检查日期 | 2026-11-12（Asia/Shanghai） |
| 对应版本 | `dev/01` HEAD `6083edd06cb4b289ee251bbca28efcdd83e15d6c`，2 次提交 |
| 原始日志 | `evidence/核查命令与输出.txt`（round3-verify.ps1 Tee 原始输出）、`evidence/核查命令与输出-补充.txt`（CMD-01~08） |
| 可复现脚本 | `evidence/round3-verify.ps1`、`scripts/verify-extension.ps1`、`scripts/demo-five-scenarios.ps1`、`evidence/gen_csv.py` |

| 编号 | 证据位置 | 定位与关键内容 | 版本 / 退出码 |
| --- | --- | --- | --- |
| E3-001 | `C:/Users/10990/.codebuddy/skills/student-project-audit/references/rubric.md`、`checklist.md`、`report-template.md`、`scripts/score_audit.py`；`20261112-02/audit-input.json`、`score.json` | rubric 第 33~42 行合格规则与 unknown 口径；第二轮 42 原子项、各类 max_points 与 mandatory，第三轮矩阵锁定不重分配 | 技能 v 内置；第二轮 5.38 |
| E3-002 | `核查命令与输出-补充.txt` CMD-01；`核查命令与输出.txt` phase 4 | `dev/01`、HEAD `6083edd…`、`rev-list --count HEAD=2`、两条提交 message 与时间、工作区干净、`git remote -v` 空 | exit=0 |
| E3-003 | `核查命令与输出.txt` phase 1 | `go run main.go` 直接启动（go=D:\Go\bin\go.exe，pid=35488）；`/health={"mode":"demo-memory","status":"ok"}`；`GET /` 200 | script_exit=0 |
| E3-004 | `核查命令与输出.txt` phase 1 | 五组场景 S1-01~S5-09 共 40 步在 go run 实例上全部返回预期 code/M-xx；S2-01 20 次抢单成功 3/被拒 17；S5-07/08 越权 M-20 | PASS |
| E3-005 | `核查命令与输出-补充.txt` CMD-02 | `gofmt -l .` 无输出、`go vet ./...`、`go build ./...`、`go test ./... -count=1` 7 包全部 ok | 各项 exit=0 |
| E3-006 | `核查命令与输出-补充.txt` CMD-03 | `-coverpkg ./...` 整体 `87.4%`；`server/service` `88.9%`；均 ≥85%，未排除自编 DAO/HTTP 代码 | cover_exit=0 |
| E3-007 | `核查命令与输出-补充.txt` CMD-03 | `CGO_ENABLED=0`、`gcc=NOT_FOUND`、`clang=NOT_FOUND`、`meegle=NOT_FOUND`、`GVA_MYSQL_DSN=NOT_SET`；race 探针 `-race requires cgo` | race_exit=2（环境） |
| E3-008 | `.codebuddy/skills/acceptance-check/SKILL.md` | 1~4 行 YAML 元数据；32~48 行上层约束；50~74 行输入/步骤/输出格式/失败处理/完成标准；只读、不伪造证据 | 新产物 v1.0 |
| E3-009 | `skill-usage.md` | 56~67 行第 3.1 节 `acceptance-check` ①~⑥ 六类说明；91~99 行第 5/6 节调用与 K-04 闭环；104~106 行第 7 节如实登记「未由验收 Agent 独立会话执行」 | 新产物 |
| E3-010 | `server/router/extension.go` | 13~20 行 `InitExtensionRouter`：API-21 `POST /admin/goods/:goods_id/price`、API-22 `POST /payment/timeout`、API-23 `GET /ops/stock-check/:order_no` | 新产物 |
| E3-011 | `docs/interface-list.md` | 7 行 v1.1 增量声明；79~111 行第 6 节三接口字段与静态页面清单；108~111 行口径：API-22 不改状态、API-23 只读、不引入缓存组件、第 3 轮浏览器验收仍属过程证据 | v1.1 |
| E3-012 | `server/initialize/router.go`、`resource/static/` | router.go 14 行 `Routers(..., exts ...)`、27~34 行扩展路由注册、`engine.Static("/static","resource/static")`、`GET / -> c.File(...)`；static 目录 9 个 HTML + `app.css` + `app.js` | 新产物 |
| E3-013 | `核查命令与输出.txt` phase 2；`scripts/verify-extension.ps1` | 12 个静态资源 HTTP 200；API-16/18/19/20/01 回归；API-21 调价 13000、M-12 快照不变、M-20 越权；API-22 状态不变与 `duplicate=true`；API-23 `consistent=true` 与越权 M-20；`ALL CHECKS PASSED` | PASS |
| E3-014 | `.github/workflows/ci.yml` | 1~31 行纯注释模板；8~17 行写明 CGO/gcc、MySQL(InnoDB)、meegle、远端与平台权限；19~26 行应含门禁步骤；`ci_non_comment_lines=0`，不触发流水线 | 新产物 |
| E3-015 | `docs/git-提交指引.md` | 45~55 行 2.1 节首次提交偏差如实登记；57~69 行 2.2 节修正记录：不 amend、`[opt] [v1.1.0]` 合规、后续 feat 仍须真实编号核验 | 新产物 |
| E3-016 | `docs/代码产物补齐说明.md`、`docs/完成声明边界.md` | 逐条对应第二轮代码/产物缺陷；3.1 节禁止「门禁验收通过/三轮验证完成/可合并 main/已上线」等声明 | 新产物 |
| E3-017 | `test-report.md` | 第 9 节第三批自检：新增 5 个测试文件、gofmt/vet/build/test exit=0、覆盖率、go run 与五组场景、静态页面与 API-21/22/23；race 未启动属环境 | 新产物 |
| E3-018 | `server/service/extension_test.go`、`extension_gorm_test.go`、`server/api/v1/extension_api_test.go`、`server/router/extension_router_test.go`、`server/initialize/static_router_test.go` | 第三批新增 5 个测试文件，覆盖调价、超时通知幂等、逐单核查、越权与静态路由 | 新产物 |
| E3-019 | `evidence/核查命令与输出.txt`、`核查命令与输出-补充.txt`、`round3-verify.ps1`、`gen_csv.py`；本目录 `score.json` / `audit-input.json` / 两份 CSV | 第三轮实际执行脚本、原始输出、稳定矩阵与计分结果；`gen_csv.py` 输出 42 行 + 29 历史 + 8 本轮行 | exit=0 |
| E3-020 | `核查命令与输出-补充.txt` CMD-06 | `README.md=False`、`apipost-run-export.json=False`、`events.jsonl=False`、`video_files=0`、`remote_lines=0`、`tracked_files=114`；`session_export_files=1`/`apipost_export_files=1` 仅为说明文档；工作区唯一未跟踪为本次审计输出目录 | exit=0 |
| E3-021 | `evidence/会话导出说明.md`、`验收报告说明.md`、`交付证据说明.md`、`AI使用说明.md`、`事件清单说明.md` | 均自述「不是交付物本体 / 不含通过结论 / 不得事后补造」，说明文档不等于会话导出、验收报告或事件清单 | 第一轮整改产物 |
| E3-022 | `apipost-run-summary.md` | 前 12 行：「非运行结果」「通过数/失败数 = 未运行，无数据」「运行导出文件 = 无，禁止编造」 | 第一轮整改产物 |
| E3-023 | `20261112-01/检查报告.md`、`20261112-02/检查报告.md` 与各自 `score.json` | 第一轮 3.23、第二轮 5.38；三轮「发现问题 → 整改 → 复检」链与历史结论 | 历史 |
| E3-024 | 用户第三轮复核指令；`.github/workflows/ci.yml` 8~17 行；`docs/完成声明边界.md` 3.1；`docs/代码产物补齐说明.md` | 明确 race/CGO、MySQL、meegle、远端 CI、独立测试会话、视频、Apipost 导出归【环境/过程证据缺失】，不判代码缺陷；不得伪造证据 | 本轮口径 |
| E3-025 | `schema.sql`、`server/service/gorm_repository.go`、`main.go` | 三表 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`；事务 + 行锁 + `available_stock>=quantity` 条件更新；`GVA_MYSQL_DSN` 存在为 `mysql-innodb`，否则 `demo-memory` | 沿用第二轮 E2-013/014 |

> 本索引不含任何密钥、访问令牌、演示口令或用户敏感信息；所有路径、命令与退出码可在本批次 `evidence/` 内复核。
