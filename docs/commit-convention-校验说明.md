# commit-convention 对比样例与校验说明（第四轮补齐）

| 项 | 内容 |
| --- | --- |
| 文件性质 | 第四轮证据闭环新增的**说明与校验附件**；不是规范原文 |
| 规范原文 | 根目录 `commit-convention.md`（题集随附来源副本） |
| 原文是否改写 | **否，一字未改**。`AGENTS.md` 头部与第 2.2 节明确「原文不作改写」，本文件只在其之外补充样例、对比与可执行校验 |
| 校验脚本 | `scripts/check_commit_message.py`（只读取原文路径存在性，不修改任何规范文件） |
| 原始输出 | `evidence/commit-message-check-output.txt`（`python scripts/check_commit_message.py` 的真实输出） |
| 适用分支 | `dev/01`；禁止直接提交或推送 `main` |

## 1. 规范要点（摘自原文，不改写）

```text
[类型] [版本号] [需求/Bug编号] 中文描述
```

| 类型 | 版本号 | 编号 |
| --- | --- | --- |
| `feat` | 必填 | 必填 |
| `fix` | 必填 | 必填 |
| `hotfix` | 必填 | 可选（事后补） |
| `opt` | 必填 | 可选 |
| `docs` | 可选 | 可选 |
| `test` | 可选 | 可选 |

一次 commit 只包含一个类型；描述使用中文、简洁明了；版本号格式 `v{主版本}.{次版本}.{修订号}`；编号为飞书项目真实工作项 ID，格式 `#数字`。

## 2. 两条真实提交的对比样例

| 对比项 | 首次基线提交（偏差，保留历史） | 本次整改提交（格式合规） |
| --- | --- | --- |
| 哈希 | `6cc6f134ee071e0a1cb8e71f03f824a178a249e0` | `6083edd06cb4b289ee251bbca28efcdd83e15d6c` |
| 提交时间 | `2026-11-12T12:44:01+08:00` | `2026-11-12T14:07:29+08:00` |
| 原始 message | `feat: 电商订单售前退款完整业务实现` | `[opt] [v1.1.0] 补齐验收检查Skill与商品调价等交付产物` |
| 类型 | `feat:` 冒号形式，不匹配 `[类型]` | `opt` |
| 版本号 | 缺失（`feat` 必填） | `v1.1.0` |
| 编号 | 缺失（`feat` 必填） | 无（`opt` 编号可选） |
| 中文描述 | 有 | 有 |
| 一次一类型 | 混合生产代码/测试/文档/Skill/证据 | 全部归入 `opt` 一类 |
| 格式校验结论 | **FAIL** | **PASS** |
| 处理方式 | 不 amend、不改写；偏差永久保留在 `docs/git-提交指引.md` 2.1 节（P-08） | 作为「格式合规」样本，见 `docs/git-提交指引.md` 2.2 节 |

> 首次提交是用户明确指定的初始化基线提交；本文件只做格式对比，不事后修改历史、不把偏差伪装成合规。

## 3. 校验脚本用法

```powershell
cd d:/Desktop/shop
$env:PYTHONIOENCODING = 'utf-8'
python scripts/check_commit_message.py                       # 校验当前分支全部真实提交
python scripts/check_commit_message.py --message "[feat] [v1.2.0] [#123456] 示例"  # 校验单条
python scripts/check_commit_message.py --json                 # 附 JSON 便于归档
```

脚本输出每条提交的哈希、message、解析出的类型/版本号/编号/描述、必填规则命中情况、PASS/FAIL 与不符合项。真实执行结果见 `evidence/commit-message-check-output.txt`。

单元级边界样例（脚本内含）：

| 样例 message | 期望 | 原因 |
| --- | --- | --- |
| `[opt] [v1.1.0] 补齐交付产物` | PASS | opt 版本号必填、编号可选 |
| `[feat] [v1.2.0] [#123] 新增下单` | PASS | feat 版本号与编号齐全 |
| `[feat] [v1.2.0] 新增下单` | FAIL | feat 缺编号 |
| `[fix] 修复缺陷` | FAIL | fix 缺版本号与编号 |
| `feat: 电商订单售前退款完整业务实现` | FAIL | 冒号形式不匹配 `[类型]` |
| `[docs] [v1.2.0] 更新文档` | PASS | docs 版本号/编号均可选 |
| `[opt] [v1.1] 补齐` | FAIL | 版本号须三段式 |

## 4. 校验边界（不得越界宣称）

- 本脚本**只校验格式**，不执行 `meegle workitem get --work-item-id <编号> --project-key r17te9`，不判断编号是否属于相应需求/缺陷，也不验证一次提交是否真的只含一种类型。
- 本机 `meegle` CLI 不可用（`NOT_FOUND`）、无远端仓库；`feat`/`fix` 的**编号核验原始输出属环境/过程证据缺失**，不得伪造，不得因格式 PASS 就宣称 `feat` 门禁已通过。
- PR 门禁、状态检查、合并与部署仍不存在；本文件不是 CI 运行结果。
- 第四轮工作区增量（证据、文档、测试）**尚未提交**，不改变 `dev/01` 现有 2 次提交的版本链；如需提交须按类型拆分并由学生确认。
