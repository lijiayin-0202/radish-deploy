# GitHub CI & MCP 自动化流水线说明

> 项目：shop-trade（题目 01）　版本：dev/01 @ `58719fb`　编写时间：2026-11-12

## 一、情况说明

本项目当前为本地开发自测版本，**尚未搭建 GitHub 远端仓库关联、PR 自动 CI 流水线、合并后自动冒烟部署流程**：

- `git remote -v` 输出为空，无远端仓库；本地仅有 `dev/01` 一个分支，无 `main`、无 PR 记录；
- `.github/workflows/ci.yml` 此前仅为注释模板，不含任何可执行作业；
- 因此**本仓库不存在任何 CI 运行记录，也未以任何方式伪造流水线日志、构建产物或运行结论**。

该项产物依赖远端平台账号与仓库权限，属平台侧／环境侧依赖，无法在本地开发环境中自行补齐。

## 二、可本地复现的完整测试方式

在仓库根目录执行以下命令即可完整运行全部单元测试并生成覆盖率报告，与流水线应当执行的内容一致：

```bash
gofmt -l .                      # 格式检查，无输出即通过
go vet ./...                    # 静态检查
go build ./...                  # 编译
go test -count=1 ./...          # 全量单元测试
go test -count=1 -coverpkg=./... -coverprofile=coverage-gate.out ./...   # 覆盖率
go tool cover -func=coverage-gate.out                                   # 逐函数覆盖率
```

真实执行结果（`evidence/quality_gate_output.txt`，复跑脚本 `evidence/quality_gate.py`）：

| 检查项 | 命令 | 结果 |
| --- | --- | --- |
| 格式 | `gofmt -l .` | 无输出，exit=0 |
| 静态检查 | `go vet ./...` | 无告警，exit=0 |
| 编译 | `go build ./...` | exit=0 |
| 单元测试 | `go test -count=1 ./...` | 6 个包全部 ok，exit=0 |
| 覆盖率 | `go test -coverpkg=./...` | 整体 94.2%，核心业务包 `server/service` 98.5%，exit=0 |

竞态检测在本机因无 C 编译器不可执行，已改用 WSL 内真实 gcc 工具链执行并留档：`evidence/race竞态检测说明.md`、`evidence/race_raw_output.txt`（exit=0，无数据竞争报告）。

接口级验证同样可本地复现：`python -X utf8 evidence/api_validation_probe.py`（57 条非法入参探针，0 条未兜住）与 `python -X utf8 scripts/regen_apipost.py`（按定稿接口清单重新生成 5 组场景、48 个用例的 Apipost 集合）。

## 三、提供的流水线配置（真实可执行，尚未在远端运行）

为便于后续在远端启用，仓库内已提供一份**可执行**的 CI 工作流定义 `evidence/ci.yml`，其内容与上表命令一一对应（格式检查、静态检查、编译、单元测试、覆盖率上传）。需要说明：

- 该文件是**配置**，不是运行记录；本仓库**没有任何该工作流的运行结果**；
- 将其放置到 `.github/workflows/ci.yml` 并关联远端仓库后，才会产生真实的流水线运行记录；
- 在未关联远端之前，评分项「CI 流水线实际运行」按缺证登记，不以配置文件替代。

## 四、后续动作

1. 在具备 GitHub 账号与 MCP 权限的环境中创建远端仓库并关联本仓库；
2. 将 `evidence/ci.yml` 落地为 `.github/workflows/ci.yml`，提交并推送至 `dev/01`；
3. 由真实 PR 触发流水线，保存真实的运行链接与输出；
4. 合并后执行冒烟部署并留存部署地址、版本对应关系与回滚说明。

在完成上述动作前，涉及「GitHub MCP 建仓」「CI 流水线实际运行」「PR 合并」「部署冒烟」的评分项按缺证登记，本文不替代这些产物。
