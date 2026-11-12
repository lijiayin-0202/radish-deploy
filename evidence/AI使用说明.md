# AI 使用说明（一页）

| 项 | 内容 |
| --- | --- |
| 项目 | `shop-trade` 题目 01 小型电商订单交易、发货与售前退款 |
| 会话角色 | 开发 Agent（本轮）；测试 / 验收 Agent 独立会话尚未建立 |
| 分支 | `dev/01`（本地首次提交，无远端） |
| 依据 | 题面共同要求第 3/8/9 节、任务规划 `DOC-03`、`AGENTS.md`、`.agent/06` |

## 1. AI 用在哪些阶段

| 阶段 | AI 参与内容 | 学生责任 |
| --- | --- | --- |
| 需求分析 | 依据题面 Markdown 生成 12 章需求文档（不生成接口/表/代码） | 逐项审核，确认未扩题 |
| 原型设计 | 生成 `V-01~V-08`、状态机、`M-01~M-30` 文案与显隐矩阵说明 | 审核页面与状态口径 |
| 任务规划 | 生成并校验 v1.1 任务规划，修正循环依赖与门禁倒置 | 确认任务编号与 8 小时分配 |
| 约束与 Skill | 编写 `AGENTS.md` v1.0/v1.1、`.agent/` 6 份、3 个自编 Skill | 确认版本、历史版本保留与授权（C-08） |
| 开发 | `schema.sql`、model、service、controller、router、`main.go`、演示脚本、Apipost 用例草案、接口清单定稿 | **逐项审核生成代码**；发现问题保留问题描述、修正要求与复测过程 |
| 检查 | 调用 `student-project-audit` 生成 3.23/10 不合格报告，作为整改输入 | 据报告下达逐条整改要求 |
| 整改 | 补齐可运行入口、五组场景接口、文档与证据说明、Git 提交链 | 核验允许/禁止的完成声明边界 |

## 2. 使用的工具与 Skill

- 自编 Skill：`gva-model-generate`、`unit-test-race`、`apipost-case-gen`（六类说明、实际调用记录、闭环与缺口见 `skill-usage.md`）。
- 插件 Skill：`student-project-audit`、`skill-creator`、`writing-skills`、`brainstorming`、`test-driven-development`、`verification-before-completion`。
- 工具：文件读写/检索、命令执行（Go 工具链、Git、PowerShell）、结构化审计脚本。未使用未说明的第三方依赖或真实支付/物流服务。

## 3. AI 明确未做 / 不得声称的事

1. 未建立独立测试 Agent 与验收 Agent 会话；`test-report.md`、`apipost-run-summary.md` 均为**开发草稿**。
2. 未跑通 `go test -race`（本机 `CGO_ENABLED=0`、无 gcc/clang），未连接真实 MySQL(InnoDB) 测试库；草稿覆盖率 87.7% / 86.0% 不是正式验收数据。
3. 未运行 Apipost 第 2 轮、未做浏览器第 3 轮页面验收，无 `apipost-run-export.json`。
4. 无 meegle 编号核验原始输出、无 GitHub MCP 建仓记录、无 PR / CI / 部署 / 视频 / 群提交记录。
5. 未生成全过程会话导出与结构化事件清单；上下文压缩后无法还原精确时间戳，故只提供说明文档而不编造 `events.jsonl`。
6. 未编写测试 Agent / 验收 Agent 的报告与结论，未把模拟支付渠道宣称为真实第三方接入成果。

## 4. 三轮验证状态（不得跳序）

| 轮次 | 状态 | 缺失证据 |
| --- | --- | --- |
| 第 1 轮 单测 + 覆盖率 + race | 部分完成（开发会话草稿） | 真实 MySQL(InnoDB) 环境、`CGO_ENABLED=1` 的 race 原始输出 |
| 第 2 轮 Apipost | 用例已基于定稿重建，**未运行** | 运行标识、通过/失败数、`apipost-run-export.json` |
| 第 3 轮 浏览器页面验收 | 未开始 | 独立验收会话、逐项结论、脱敏截图/录屏 |

## 5. 学生核验与整改闭环

学生审核发现的问题须登记「问题描述 → 修正要求 → 复测过程」；开发 Agent 在 `dev/01` 以 `fix` 类型修复（含编号核验）后交测试 Agent 复测，再由验收 Agent 复核。本轮开发自检记录见 `test-report.md` D-01~D-06，**不等价于**测试 Agent 的缺陷闭环。

## 6. 完成声明边界

本轮只允许声明「整改完成：可启动、可编译、具备可演示接口，补齐 Git 提交链与 `skill-usage.md`，race 门禁条件已就绪」。禁止声明「门禁验收通过 / 可合并 main / 已部署上线 / 三轮验证完成」。详见 `docs/完成声明边界.md`。

## 7. 关联文件

`skill-usage.md`、`evidence/会话导出说明.md`、`evidence/事件清单说明.md`、`evidence/验收报告说明.md`、`evidence/交付证据说明.md`、`test-report.md`、`docs/git-提交指引.md`。
