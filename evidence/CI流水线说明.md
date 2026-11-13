# GitHub CI & MCP 自动化流水线说明

> 项目：shop-trade（题目 01）　版本：dev/01 @ `bb1ca7f`　编写时间：2026-11-13

## 一、情况说明

本项目当前为本地开发自测版本，**尚未搭建 GitHub 远端仓库关联、PR 自动 CI 流水线、合并后自动冒烟部署流程**：

- `git remote -v` 输出为空，无远端仓库；本地仅有 `dev/01` 一个分支，无 `main`、无 PR 记录；
- `.github/workflows/ci.yml` 已是**可执行工作流**（3 个作业、23 个步骤），不再是注释模板；
- 但**本仓库不存在任何 CI 运行记录，也未以任何方式伪造流水线日志、构建产物或运行结论**。

远端建仓、PR 触发与合并后部署依赖平台账号与仓库权限，属平台侧／环境侧依赖，无法在本地自行补齐；
本地已把该工作流用到的全部门禁做成脚本并真实跑通，使「配置」与「可复现执行」分离可核验。

## 二、可本地复现的完整测试方式

在仓库根目录执行以下命令即可完整运行全部单元测试并生成覆盖率报告，与流水线应当执行的内容一致：

```bash
gofmt -l .                      # 格式检查，无输出即通过
go vet ./...                    # 静态检查
go build ./...                  # 编译
go test -count=1 ./...          # 全量单元测试
go test -count=1 -coverpkg=./... -coverprofile=evidence/coverage-gate.out ./...   # 覆盖率
go tool cover -func=evidence/coverage-gate.out                                    # 逐函数覆盖率
```

**一条命令跑完全部门禁**（与 `.github/workflows/ci.yml` 同源同序）：

```bash
python -X utf8 scripts/pipeline_gates.py
```

该总控依次执行 10 个门禁项并把每个门禁的原始输出写入 `evidence/pipeline_gate_reports/`，
同时生成《门禁总表.md》。最近一次真实执行结果：**门禁项 10；通过 10；不通过 0**（2026-11-13 10:09:44）。

| 门禁项 | 对应 AGENTS.md 2.5 门禁 | 脚本 | 最近结果 |
| --- | --- | --- | --- |
| 格式检查 gofmt | 格式与静态检查 | `gofmt -l .` | exit=0 |
| 静态检查 go vet | 格式与静态检查 | `go vet ./...` | exit=0 |
| 编译 go build | 同源构建 | `go build ./...` | exit=0 |
| 单元测试 | 单元测试 | `go test -count=1 ./...` | exit=0 |
| 覆盖率阈值判定 | 覆盖率 | `scripts/coverage_gate.py` | 整体 97.63%、`server/service` 98.47%，exit=0 |
| 覆盖率证据一致性 | 覆盖率 | `scripts/coverage_evidence_gate.py` | 快照可追溯且达标，exit=0 |
| 五组必演示场景 | 五组场景 | `scripts/scenario_gate.py` | 5 组场景 / 38 条断言 / 关键失败码全命中，exit=0 |
| Git 流程 | Git 流程 | `scripts/git_process_gate.py` | 分支 dev/01、22 条提交格式全合规、0 merge，exit=0 |
| AI 与 Skill 记录齐备 | AI 与 Skill 记录 | `scripts/record_gate.py` | 13 项记录齐备，exit=0 |
| 敏感信息扫描 | 敏感信息保护 | `scripts/secret_scan_gate.py` | 211 个文件 0 命中，exit=0 |

竞态检测在本机因无 C 编译器不可执行，已改用 WSL 内真实 gcc 工具链执行并留档：`evidence/race竞态检测说明.md`、`evidence/race_raw_output.txt`（exit=0，无数据竞争报告）。

接口级验证同样可本地复现：`python -X utf8 evidence/api_validation_probe.py`（57 条非法入参探针，0 条未兜住）与 `python -X utf8 scripts/regen_apipost.py`（按定稿接口清单重新生成 5 组场景、48 个用例的 Apipost 集合）。

## 三、提供的流水线配置（真实可执行，尚未在远端运行）

仓库内已提供一份**可执行**的 CI 工作流定义 `.github/workflows/ci.yml`（生效路径），共 3 个作业、23 个步骤：

| 作业 | 步骤数 | 内容 |
| --- | --- | --- |
| `quality-gate` | 13 | checkout、setup-go、gofmt、go vet、go build、单元测试、竞态检测、覆盖率采集、覆盖率阈值判定、覆盖率明细、覆盖率证据一致性门禁、五组场景门禁、覆盖率与门禁报告上传 |
| `process-gate` | 6 | checkout（完整历史）、setup-go、Git 流程门禁、AI 与 Skill 记录齐备性门禁、敏感信息扫描门禁、过程门禁报告上传 |
| `deploy-gate` | 4 | checkout、setup-go、基础部署门禁（制品构建、版本登记、启动、健康检查、业务冒烟、回退准备校验）、制品与版本清单上传；依赖 `quality-gate` 与 `process-gate` 同时通过 |

需要说明：

- 该文件是**配置**，不是运行记录；本仓库**没有任何该工作流的运行结果**；
- 其中的每个判定步骤都调用本仓库的脚本，与 `scripts/pipeline_gates.py` 同源同序，判定口径唯一；
- 在未关联远端之前，评分项「CI 流水线实际运行」按缺证登记，不以配置文件替代。

## 四、后续动作

1. 在具备 GitHub 账号与 MCP 权限的环境中创建远端仓库并关联本仓库；
2. 由真实 PR 触发 `.github/workflows/ci.yml`，保存真实的运行链接、run id 与各步骤日志；
3. 合并后执行冒烟部署并留存部署地址、版本对应关系与回滚说明。

在完成上述动作前，涉及「GitHub MCP 建仓」「CI 流水线实际运行」「PR 合并」「部署冒烟」的评分项按缺证登记，本文不替代这些产物。
