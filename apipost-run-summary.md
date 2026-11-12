# Apipost 第 2 轮运行摘要（基于接口清单 v1.0 定稿重建，非运行结果）

| 项 | 内容 |
| --- | --- |
| 场景编号 | `TST-S1`、`TST-S2`、`TST-S3`、`TST-S4`、`TST-S5` |
| 用例数 | 48（详见 `apipost-case-list.md`） |
| 通过数 / 失败数 | **未运行，无数据** |
| 实际运行命令或 Apipost 运行标识 | **无** |
| 运行导出文件 | **无**（未生成 `apipost-run-export.json`，禁止编造） |
| 对应提交版本 | 整改批次本地首次提交，见 `docs/git-提交指引.md`；本批用例仍未运行 |
| 会话角色 | 开发 Agent（草案）；第 2 轮须由测试 Agent 独立会话执行 |

## 为什么没有运行结果

1. 第 1 轮门禁未通过：本机 `CGO_ENABLED=0` 且无 C 编译器，`go test -race` 未启动（见 `race-output.txt`）。按三轮验证顺序，第 1 轮未通过不得开始第 2 轮。
2. 接口清单已定稿为 `docs/interface-list.md` v1.0，`api/v1` 与路由已实现，Apipost 集合已基于定稿重建；但集合本身仍未在 Apipost 中运行。
3. 可控模拟通知入口已由 `API-04` / `API-10` / `API-14` 实现；真实 MySQL(InnoDB) 测试库与演示数据基线尚未就绪，正式第 2 轮仍须在持久化模式执行。
4. 本轮用户授权为「生成测试/用例草案，但明确不得作为正式三轮验证证据」。

## 草案产物

| 文件 | 说明 |
| --- | --- |
| `apipost-collection.json` | 基于定稿接口清单重建的用例集合（非 Apipost 官方导出格式，导入前需按实际导出格式转换） |
| `apipost-case-list.md` | 48 个用例清单与 `AC/V/M/E` 关联 |
| `apipost-assertion-matrix.md` | 失败原因、验收条件、异常边界断言矩阵 |
| `apipost-run-summary.md` | 本文件，草案状态说明 |

## 交回测试 Agent 的待办

1. 在具备 `CGO_ENABLED=1` 与 gcc/clang 的环境执行 `scripts/run-race.ps1`，产出正式 race / 覆盖率原始输出。
2. 复核定稿接口清单后，把集合转换为实际 Apipost 导出格式，配置环境变量与前置/后置脚本，接入 `API-04` / `API-10` / `API-14` 模拟通知入口。
3. 执行 48 个用例，导出 `apipost-run-export.json` 与真实通过/失败数；失败用例登记编号、现象、复现步骤、修正要求，交回开发 Agent 以 `fix` 修复（含 meegle 编号核验）后复测。
4. 第 2 轮全部通过后，由验收 Agent 在独立会话执行第 3 轮浏览器页面验收（`V-01~V-08` 与显隐矩阵）。
5. 全过程不得把模拟支付渠道宣称为真实第三方接入成果；密钥、口令、令牌一律脱敏。
