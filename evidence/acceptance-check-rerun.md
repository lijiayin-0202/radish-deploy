# acceptance-check 验收检查重跑记录

> 项目：shop-trade（题目 01）　检查对象版本：dev/01 @ `58719fb`（本次补齐前的 HEAD）
> 重跑时间：2026-11-12　重跑依据：`.codebuddy/skills/acceptance-check/SKILL.md` v1.0
> 说明：本次重跑由**开发侧同一会话**执行，属「自检」性质，**不构成独立验收会话结论**，按 Skill 要求标注待独立验收复核。

## 一、版本对应

| 项 | 值 |
| --- | --- |
| 检查基准提交 | `58719fb`（分支 dev/01） |
| 本次新增证据 | `evidence/` 下 schema.sql、mysql_raw_00~05、race_raw_output、quality_gate_output、api_validation_probe、coverage-report、ci.yml 与 4 份说明文档 |
| 环境事实 | Windows 本机：Go 1.22.x、CGO_ENABLED=0、无 gcc；WSL Ubuntu：MySQL 8.4.11（InnoDB）、Go 1.26.8、gcc 15.2.0 |
| 远端事实 | `git remote -v` 为空；无 main 分支；无 PR、无 CI 运行记录、无部署记录 |

## 二、逐项核查（门禁必做项）

| 编号 | 核查项 | 依据 | 实际证据 | 结论 | 归属分类 | 缺口与复验条件 |
| --- | --- | --- | --- | --- | --- | --- |
| G-01 | 格式检查 | 门禁 | `gofmt -l .` 无输出，`evidence/quality_gate_output.txt` | 通过 | — | — |
| G-02 | 静态检查 | 门禁 | `go vet ./...` exit=0，同上 | 通过 | — | — |
| G-03 | 编译 | 门禁 | `go build ./...` exit=0，同上 | 通过 | — | — |
| G-04 | 单元测试 | 门禁 | `go test -count=1 ./...` 6 包 ok、exit=0，同上 | 通过 | — | — |
| G-05 | 覆盖率整体 ≥85% | 门禁 | 94.2%（1508/1601），`evidence/coverage-gate.out` | 通过 | — | — |
| G-06 | 各核心业务包 ≥85% | 门禁 | `server/service` 98.5%（1161/1179） | 通过 | — | `server/api/v1` 82.2%，非核心包但建议补错误分支用例 |
| G-07 | `go test -race` | 门禁 | WSL gcc 15.2.0 下 `CGO_ENABLED=1 go test -race ./... -count=1`，6 包 ok、race_exit=0、无 DATA RACE（`evidence/race_raw_output.txt`） | 通过 | 环境缺失已解除 | — |
| G-08 | 真实 MySQL(InnoDB) 落库 | Q-01 | MySQL 8.4.11 实测建库建表、SHOW CREATE TABLE、索引与唯一约束清单（`evidence/mysql_raw_01_schema.txt`、`mysql_raw_02_inspect.txt`） | 通过 | 环境缺失已解除 | — |
| G-09 | 数据库重启后结构/索引/约束正常 | A4-04 | `service mysql restart` 后 `mysqld is alive`、索引与唯一约束一致、数据留存，ERROR 计数 0（`evidence/mysql_raw_04_restart.txt`） | 通过 | — | — |
| G-10 | 唯一键冲突生效 | A2-04 | 三类唯一约束实测报 `ERROR 1062`（`evidence/mysql_raw_03_unique.txt`） | 通过 | — | — |
| G-11 | 服务重启后业务结果仍可查询 | A2-04 | 终止进程1→启动进程2→同一订单仍可查询且状态一致；断言 8/8 PASS（`evidence/mysql_raw_05_app_persistence.txt`） | 通过 | — | — |
| G-12 | 真实 InnoDB 行锁下并发不超卖 | A3-05 | 20 并发成功 3 次、失败 17 次（M-02），`available+occupied==5` 恒等 | 通过 | — | — |
| G-13 | 接口入参校验与异常分支 | A3-04 | 57 条非法入参探针，0 条 500 / 0 条 INTERNAL_ERROR / 0 条非 JSON（`evidence/api_validation_probe.txt`） | 通过 | — | — |
| G-14 | 五组演示场景可复现 | 门禁 | `evidence/独立反例探测结果.json`（119 PASS / 1 环境限制 DIFF） | 通过 | — | — |
| G-15 | 页面可访问 | A2-05 | 9 个原型视图 HTTP 200（既有证据） | 通过 | — | — |
| G-16 | Apipost 接口用例集合 | A2-03 | 按定稿接口清单重建 5 组场景 / 48 个用例（`apipost-collection.json`），状态「未运行」 | 待补证 | 过程证据缺失 | 需在 Apipost 平台实际运行并导出结果 |
| G-17 | 独立测试会话 / 验收会话 | 门禁 | 本仓库无 `evidence/sessions/`、无 `events.jsonl`（`evidence/会话导出说明.md`） | 待补证 | 环境/权限缺失 | 需平台侧导出三段会话记录 |
| G-18 | GitHub 远端 / PR / CI 运行 | 门禁 | 无远端、无 main、无 PR、无 CI 运行记录；仅提供可执行配置 `evidence/ci.yml` | 待补证 | 环境/权限缺失 | 关联远端后由真实 PR 触发流水线 |
| G-19 | 部署与上线冒烟 | 门禁 | 无部署地址、无制品、无上线记录 | 待补证 | 环境/权限缺失 | 合并后执行部署并留冒烟与回滚说明 |
| G-20 | 讲解视频与时间目录 | 门禁 | 未产出 | 待补证 | 人工录制 | 人工录制并补时间目录 |
| G-21 | 当日班级群提交凭据 | 门禁 | 未产出 | 待补证 | 人工提交 | 当日实际提交后留存凭据 |
| G-22 | 提交消息格式合规 | commit-convention.md | 既有 7 次提交中首条 `feat: 电商订单售前退款完整业务实现` 不含版本号与编号；本次新增提交按类型区分且不冒充编号 | 部分通过 | 过程证据缺失 | 历史提交不可改写；后续 feat/fix 须先完成 meegle 编号核验（当前环境无 meegle CLI，故本次不使用 feat/fix 类型） |
| G-23 | 敏感信息脱敏 | Q-06 | MySQL 应用账号口令仅存于 WSL `/tmp/shop_dsn_pw`，未进入仓库、日志与本文 | 通过 | — | — |
| G-24 | Token 用量台账 | 评分要求 | 本机未采集到分阶段 usage 原件，无可比总量 | 待补证 | 教师基准未发布 + 过程证据缺失 | 教师发布基准后补交官方 usage 原件 |

## 三、问题分类汇总

| 分类 | 条目 | 影响 |
| --- | --- | --- |
| 代码/产物缺陷 | 未发现新增 | — |
| 环境/权限缺失 | G-16~G-21、G-24 | 影响流程类与部署类评分项，需平台侧或人工动作补齐 |
| 过程证据缺失 | G-17、G-22 | 历史提交格式与独立会话记录无法事后补造 |

## 四、未运行 / 未访问 / 未播放清单

1. 未在 Apipost 平台实际运行接口用例（集合已生成，运行导出缺失）；
2. 未建立并导出独立测试会话、独立验收会话，未生成 `events.jsonl`；
3. 未关联 GitHub 远端，`evidence/ci.yml` 未在真实流水线中运行过，无运行记录；
4. 未执行合并后部署与上线冒烟，无部署地址与制品；
5. 未录制、未播放讲解视频；
6. 未在班级群实际提交，无当日提交凭据；
7. 未完成 meegle 工作项编号核验（当前环境无 meegle CLI）。

## 五、结论

- 业务与产物层面：G-01~G-15、G-23 共 15 项均有真实证据且通过，其中 MySQL 与 race 两项属本轮新增真实环境证据；
- 流程与交付层面：G-16~G-22、G-24 共 9 项仍为「待补证」，分别归类为环境/权限缺失、过程证据缺失或人工动作；
- 按本 Skill 规定，在必做门禁未全部具备真实证据前，**不输出「验收通过」结论**；本记录仅作为开发侧自检结果，需由独立验收会话复核后方可定案。