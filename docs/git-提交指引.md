# Git 提交指引（`dev/01`）

| 项 | 内容 |
| --- | --- |
| 项目 | `shop-trade` 题目 01 |
| 依据 | 根目录 `commit-convention.md`（原文未改写）、`AGENTS.md` 第 2 章、`.agent/04-workflow-git.md`、`.agent/06-workflow-devflow.md` |
| 适用分支 | `dev/01`（**禁止直接提交或推送 `main`**） |
| 文件性质 | 开发 Agent 编写的操作指引与偏差说明；不是 PR / CI 运行结果 |

## 1. 当前真实状态（2026-11-12）

| 检查命令 | 结果 |
| --- | --- |
| `git branch --show-current` | `dev/01` |
| `git remote -v` | 空：当前**无远程仓库**（因此不存在 PR / CI / 部署记录，不得编造） |
| `git status --short --branch` | 整改前为 `## No commits yet on dev/01` + 全部文件未跟踪 |
| `git log -1 --oneline` | 整改前报 `fatal: your current branch 'dev/01' does not have any commits yet`；按第 2 节建立首次提交后有有效 HEAD |
| `git config user.name` / `user.email` | 已有全局身份；本轮**未修改任何 git config** |
| `meegle` CLI | `Get-Command meegle` 无结果，**本机未安装 / 不可用** |
| `go env CGO_ENABLED` / `gcc` | `0` / 无 C 编译器，`go test -race` 前置条件不满足 |

首次提交后可用以下命令复核提交链（原始输出须另行保存，不得只写结论）：

```powershell
cd d:/Desktop/shop
git status --short --branch
git log --oneline --decorate -1
git rev-parse HEAD
git branch --show-current
```

## 2. 首次提交（用户明确指定）

用户在整改指令中要求：「初始化 Git，给 `dev/01` 做第一次 commit 生成有效 HEAD，提交说明按用户指定 `feat: 电商订单售前退款完整业务实现`」。

执行命令：

```powershell
cd d:/Desktop/shop
git checkout -B dev/01     # 分支已存在且无提交时，仅确认当前分支仍为 dev/01
git add -A
git commit -m "feat: 电商订单售前退款完整业务实现"
```

### 2.1 与 `commit-convention.md` 的偏差（如实登记，不掩盖）

| 规范要求 | 本次实际 | 影响 |
| --- | --- | --- |
| 格式 `[类型] [版本号] [需求/Bug编号] 中文描述` | `feat: 电商订单售前退款完整业务实现` | 格式不符，缺版本号与编号 |
| `feat` 版本号、编号必填 | 无 | 不满足必填规则 |
| `feat` 提交前必须执行 `meegle workitem get --work-item-id <数字编号> --project-key r17te9` 并保留输出 | 本机 `meegle` 不可用，且无经核验的真实工作项 ID，**未执行核验** | 不得声称已核验，不得伪造编号或输出 |
| 一次 commit 只含一种类型 | 首次提交包含生产代码、测试代码、文档、Skill 与证据产物 | 属混合类型基线提交 |

**结论**：本次提交仅为「建立有效 HEAD 的初始化基线提交」，按用户明确指定执行；**不得视为合规 `feat` 提交**，不得作为 PR 门禁「提交格式合规、编号核验真实」的证据。后续门禁核验须由验收 Agent 逐项判定，缺项如实记为不通过。
**禁止**在事后改写历史以伪装成合规提交；如需修正，只能由学生确认后新增独立提交并保留原历史。

### 2.2 首次提交偏差的修正记录（本批次）

用户本轮指令要求「修正首次 commit 格式偏差，在 `docs/git-提交指引.md` 更新说明，标记本次整改 commit 符合规范」。处理方式：

| 项 | 处理 |
| --- | --- |
| 历史提交 `6cc6f134…` | **不改写、不 amend**。该哈希已被第二轮门禁复核报告、覆盖率与运行实例绑定，改写会破坏版本对应（AGENTS.md P-08）；偏差记录永久保留在第 2.1 节 |
| 本次整改 commit | 采用 `[opt] [v1.1.0] 补齐验收检查Skill与商品调价等交付产物`，符合 `[类型] [版本号] 中文描述` 格式；`opt` 类型**版本号必填、编号可选**，无需 meegle 编号核验，因此**格式符合 `commit-convention.md`** |
| 为何不用 `feat` | 本机 `meegle` CLI 不可用，`feat` 强制的编号核验无法完成（AGENTS.md 2.4）；本批次是「已有交付物的补齐与完善」，未新增题面业务规则。**禁止**因缺编号把新增业务功能伪装成 `docs` / `test` / `opt`：后续若新增题面业务功能，仍须走 `feat` + 真实编号核验并保留原始输出 |
| 一次一类型 | 本批次全部新增/更新文件归入 `opt` 一类，不与 `docs` / `test` 混用 |
| 未伪造 | 不生成 meegle 核验输出、不编造编号、不声称 PR / CI 已运行；CI 模板只含注释，不是运行证据 |

**标记**：本次整改 commit 格式符合规范，可用 `git log -1 --format=%s` 与 `commit-convention.md` 逐项比对；提交哈希以 `git log -1` 为准，不在本文件写死，避免文档与自身提交形成循环引用。**编号核验仍属环境缺失项**（见 `evidence/交付证据说明.md`），不得据此宣称 `feat` 门禁已通过。

### 2.3 第四轮补充：对比样例与可执行校验脚本

| 新增项 | 路径 | 作用 |
| --- | --- | --- |
| 对比样例说明 | `docs/commit-convention-校验说明.md` | 逐项对比首次偏差提交与本次 `opt` 提交；**不改写 `commit-convention.md` 原文**（题集随附来源副本，AGENTS.md 明确「原文不作改写」） |
| 校验脚本 | `scripts/check_commit_message.py` | 按 `[类型] [版本号] [需求/Bug编号] 中文描述` 解析 `git log` 的真实 message，按类型必填规则判定 PASS/FAIL |
| 原始输出 | `evidence/commit-message-check-output.txt` | 第四轮真实执行输出 |

真实执行结果（`python scripts/check_commit_message.py`）：

```text
[1] 6083edd06cb4 | [opt] [v1.1.0] 补齐验收检查Skill与商品调价等交付产物
     类型=opt 版本号=v1.1.0 编号=(无) → PASS 符合规范
[2] 6cc6f134ee07 | feat: 电商订单售前退款完整业务实现
     → FAIL 不符合规范（冒号形式，缺版本号与编号）
合计 2 条，PASS 1 条，FAIL 1 条
```

**边界**：脚本只校验格式，不执行 `meegle` 编号核验、不判断编号归属、不验证一次提交是否真的只含一种类型，也不是 CI 运行结果。首次提交偏差按 P-08 保留历史，不 amend；第四轮工作区增量（证据、文档、测试）尚未提交，不改变现有 2 次提交的版本链。

### 2.4 第五轮增量提交约定（test / docs 分批，证据不夹带生产代码）

> 第五轮是**证据闭环轮次**：不新增题面业务功能、不改写订单状态机、不新增业务状态。
> 因此本轮**不使用 `feat` / `fix`**（本机 `meegle` CLI 不可用，无法完成 AGENTS.md 2.4 的编号核验；
> 且本轮无新增业务需求、无已登记 Bug）。按 `commit-convention.md`，`opt` / `test` / `docs` 的编号可选。

#### 2.4.1 分批原则

| 批次 | 类型 | 内容 | 判定依据 |
| --- | --- | --- | --- |
| A | `opt` | 补齐的**交付物**（模拟支付渠道服务）与其冒烟输出 | 与第四轮 `[opt] [v1.1.0] 补齐验收检查Skill与商品调价等交付产物` 同一性质：交付物补齐，`opt` 版本号必填、编号可选 |
| B | `test` | 单元测试、测试采集脚本、测试类证据产物（冒烟 / 手工记录 / 页面断言 / partial 闭环 / 覆盖率与检查输出） | AGENTS.md 2.3「`test`：单元测试、并发验证、测试报告」 |
| C | `docs` | 接口契约附录 B、提交指引 2.4、`skill-usage.md` 第 10 节、第四轮与第五轮证据清单 | AGENTS.md 2.3「`docs`：需求/原型/任务/AGENTS/Skill 文档」 |
| D | `docs` | 回补 `R-A4-04` 的**版本链核查段**与最终 HEAD 记录 | 依赖 A/B/C 的真实哈希，必须在其后单独提交 |

**一次 commit 只含一种类型**；四个批次**互不夹带**：
A 不含测试与文档，B 不含交付物与产品文档，C 不含测试代码，D 不含任何代码。

#### 2.4.2 提交前检查清单（每批次逐条执行）

1. `git branch --show-current` 必须为 `dev/01`（禁止在 `main` 上提交）。
2. `git status --short` 复核**本次暂存范围**：只允许本批次文件入暂存区，**不得** `git add -A` 一次性混入其他类型。
3. `python scripts/check_commit_message.py --message "<本批次提交说明>"` 必须输出 `PASS 符合规范`，并把该输出与提交哈希一起留存。
4. `go test ./...`、`gofmt -l .`、`go vet ./...` 在**含 B 批次的提交前**必须全绿（覆盖率数字以真实执行输出为准，**不得**手工编辑）。
5. 提交后 `git log --oneline -4` 复核四条提交的类型与顺序。

#### 2.4.3 本轮真实提交序列（提交后回补，见 `evidence/partial-closure/R-A4-04.md`）

| 批次 | 类型 | 提交说明 | 包含文件 |
| --- | --- | --- | --- |
| A | `opt` | `[opt] [v1.2.0] 补齐模拟支付渠道服务与第四轮冒烟产物` | `scripts/mock_channel_service.py`、`scripts/r4_mock_channel_smoke.py`、`evidence/mock-channel-run.txt`、`evidence/r4-mock-channel-output.txt` |
| B | `test` | `[test] [v1.2.0] 补充第五轮边界单测与证据采集产物` | `server/service/r5_edge_test.go`、`server/service/r5_edge2_test.go`、`scripts/r5_closure_lib.py`、`scripts/r5_partial_closure.py`、`scripts/r5_partial_closure2.py`、`scripts/r5_manual2.py`、`scripts/r5_htmlcheck_enhance.py`、`scripts/check_commit_message.py`、`evidence/smoke/`、`evidence/manual/`、`evidence/manual-round2/`、`evidence/html-check/`、`evidence/partial-closure/`、`evidence/commit-message-check-output.txt`、`evidence/r4-suite-output.txt`、`evidence/code-artifact-verification.txt` 等测试类输出、`outputs/单题检查/` 下的检查运行输出 |
| C | `docs` | `[docs] [v1.2.0] 补齐接口边界矩阵与第五轮证据闭环文档` | `docs/interface-list.md`（附录 B）、`docs/git-提交指引.md`（2.4）、`skill-usage.md`（第 10 节）、`docs/commit-convention-校验说明.md`、`evidence/第四轮证据清单.md`、`evidence/第五轮证据清单.md` |
| D | `docs` | `[docs] [v1.2.0] 回补版本链核查与第五轮提交记录` | `evidence/partial-closure/R-A4-04.md`（提交后回补段）、`evidence/第五轮证据清单.md`（提交哈希列） |

#### 2.4.4 本轮禁止项

- **不得**把四个批次合并为一次提交，或在同一提交中夹带 `test` 与 `docs`。
- **不得**用 `docs` / `test` 提交夹带生产代码（第五轮**没有任何生产代码变更**，该风险为零）。
- **不得**为满足格式而编造 `meegle` 编号；本轮四条提交的编号列一律为空，`opt` 版本号按规范必填。
- **不得**在提交后 `amend` / `rebase` 改写 A/B/C；D 是**追加**提交，用于回补真实哈希。
- 提交哈希一律以 `git log` / `git rev-parse HEAD` 为准，**不在文档中写死未经复核的哈希**。


## 3. 后续合规提交流程

1. **确认分支**：`git branch --show-current` 必须为 `dev/01`。禁止在 `main` 上提交。
2. **确认编号**：学生提供飞书项目真实工作项 ID（需求或缺陷），且编号必须属于本次变更；不得使用占位符 `<真实编号>`。
3. **执行核验并保留完整原始输出**（命令、执行时间、完整结果、退出码）：

   ```bash
   meegle workitem get --work-item-id <数字编号> --project-key r17te9
   ```

   核验失败、编号不存在、工具不可用或查询失败时**禁止提交 `feat` / `fix`**，须提醒学生确认编号（C-05）。
4. **按类型拆分**，一次提交只含一种类型：

   | 类型 | 版本号 | 编号 | 本题用途 |
   | --- | --- | --- | --- |
   | `feat` | 必填 | 必填 | 下单、支付回调、退款、发货、页面等业务实现 |
   | `fix` | 必填 | 必填 | 缺陷清单中已登记 Bug 的修复 |
   | `hotfix` | 必填 | 可选（事后补） | 仅真实线上紧急修复 |
   | `opt` | 必填 | 可选 | 重构与优化 |
   | `docs` | 可选 | 可选 | 需求/原型/任务/AGENTS/Skill 文档 |
   | `test` | 可选 | 可选 | 单测、并发验证、测试报告 |

   合规示例（编号须替换为经核验的真实编号，不得提交占位符）：

   ```text
   [feat] [v1.0.0] [#数字编号] 实现订单创建与库存预扣
   [fix] [v1.0.1] [#数字编号] 修复重复支付通知重复记款
   [docs] 更新需求文档假设清单
   [test] 补充迟到支付场景单元测试
   ```

5. **提交后记录哈希**：`git rev-parse HEAD`，并把哈希写入测试/验收报告，建立版本对应关系。
6. **不得**因缺编号把功能变更伪装成 `docs`、`test` 或 `opt`；不得把 `docs` 提交夹带业务代码。

## 4. 推送远端与 PR 流程（当前均未执行）

```powershell
# 由学生在 GitHub MCP 创建独立仓库后，再关联远端（本轮无远端，不执行）
git remote add origin <仓库 URL>
git push -u origin dev/01
```

PR 前置门禁（全部通过才允许 `dev/01` → `main`）：单元测试全部通过；整体与核心业务包覆盖率 ≥85%；`go test -race` 在 `CGO_ENABLED=1` 环境无数据竞争；`gofmt` / `go vet` 通过；`TST-S1~S5` 有实际执行结果；独立验收 Agent 逐项通过；提交在 `dev/01` 且格式/编号核验真实；会话导出、`skill-usage.md`、AI 过程记录齐全。

合并优先保留原始提交；`main` 禁止直接推送、禁止删除、禁止强推；合并后须对 `main` 实际发布提交**重新执行门禁、构建与部署**，开发分支旧报告不得当作主分支已验证证据。

## 5. 本轮禁止项

- 不推送 `main`，不伪造 meegle 核验输出，不编造 PR / CI / 部署记录。
- 不修改 git config，不改写已建立的提交历史来掩盖第 2.1 节偏差。
- 不把密钥、访问令牌、演示口令、签名密钥或用户敏感信息写入仓库、日志与会话导出，相关内容一律脱敏。

## 6. 关联文档

`commit-convention.md`、`AGENTS.md`、`evidence/交付证据说明.md`、`docs/完成声明边界.md`、`test-report.md`。
