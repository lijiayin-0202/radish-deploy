# 覆盖率版本化快照索引

> 用途：使覆盖率原始文件可追溯到具体交付版本与提交哈希。
> 依据：AGENTS.md Q-02；scripts/coverage_gate.py（阈值判定与版本标注）。

## 一、目录内容

| 文件 | 说明 |
| --- | --- |
| coverage-v1.8.0-def0977.out | 版本化覆盖率原始文件，对应提交 def0977 |
| coverage-v1.8.0-def0977.func.txt | 同一次采集的逐函数原始输出 |
| coverage-v1.8.0-def0977.gate.txt | 同一次采集的阈值门禁判定原始输出 |
| coverage-v1.8.0-def0977.manifest.json | 结构化清单（版本、哈希、时间、命令、逐包覆盖率） |

## 二、版本与文件对应关系

| 版本标注 | 提交哈希 | 快照前缀 | 整体覆盖率 | 核心业务包 server/service |
| --- | --- | --- | --- | --- |
| v1.8.0 | def0977 | coverage-v1.8.0-def0977.* | 97.63%（1563 / 1601） | 98.47%（1161 / 1179） |

仓库根目录的 coverage.out 与 evidence/coverage-gate.out 为「最新一次采集」的工作副本，
evidence/coverage-gate-func.txt 为其逐函数明细；需要核对历史版本时以本目录的版本化快照为准。

## 三、复现方式

```powershell
# 1. 采集覆盖率原始文件（PowerShell 下必须给 ./... 加引号，否则参数会被吞掉）
go test -count=1 "-coverpkg=./..." "-coverprofile=evidence/coverage/coverage-v1.8.0-def0977.out" "./..."

# 2. 逐函数明细
go tool cover "-func=evidence/coverage/coverage-v1.8.0-def0977.out"

# 3. 阈值判定并输出带版本标注的清单
python -X utf8 scripts/coverage_gate.py --profile evidence/coverage/coverage-v1.8.0-def0977.out --overall 85 --pkg server/service:85 --revision v1.8.0 --commit def0977 --manifest evidence/coverage/coverage-v1.8.0-def0977.manifest.json
```

第 3 步在覆盖率不达标时以非零码退出，可直接作为 CI 门禁步骤（见 .github/workflows/ci.yml）。

## 四、逐包覆盖率（v1.8.0 / def0977）

| 包 | 覆盖率 | 已覆盖 / 总语句 |
| --- | --- | --- |
| server/api/v1（接入层） | 99.08% | 323 / 326 |
| server/service（核心业务包） | 98.47% | 1161 / 1179 |
| server/router | 100.00% | 24 / 24 |
| server/model | 100.00% | 3 / 3 |
| server/initialize | 90.00% | 27 / 30 |
| shop-trade（main 入口） | 64.10% | 25 / 39 |
| **整体** | **97.63%** | **1563 / 1601** |

未排除任何自编生产代码；接入层由 82.21%（268 / 326）提升到 99.08%（323 / 326），
提升来源为 server/api/v1/api_branch_coverage_test.go 补齐的拒绝与异常分支用例。
