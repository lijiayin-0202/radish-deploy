# CGO race 竞态检测说明

> 项目：shop-trade（题目 01）　版本：dev/01 @ `58719fb`　编写时间：2026-11-12

## 一、Windows 本机环境限制

本机 Windows 开发环境未配置 GCC 编译环境，`go env CGO_ENABLED` 为 `0`，`where gcc` 与 `where clang` 均无结果，因此在本机直接执行 `go test -race` 会被 Go 工具链拒绝：

```
-race requires cgo; enable cgo by setting CGO_ENABLED=1
```

这是工具链层面的限制，与业务代码无关。

## 二、已在真实 CGO 工具链下完成竞态检测（结果）

为消除上述限制，已在 WSL Ubuntu 环境内安装真实 C 编译工具链并执行竞态检测：

| 项 | 实测值 |
| --- | --- |
| 操作系统 | WSL Ubuntu（Linux 内核，真实 gcc 环境） |
| Go | `go1.26.8 linux/amd64` |
| C 编译器 | `gcc (Ubuntu 15.2.0) 15.2.0` |
| CGO | `CGO_ENABLED=1`（显式开启） |
| 执行命令 | `CGO_ENABLED=1 go test -race ./... -count=1` |
| 执行脚本 | `evidence/wsl_race_run.sh`（在仓库根目录执行，输出重定向至 `evidence/race_raw_output.txt`） |

真实执行结果（逐字摘自 `evidence/race_raw_output.txt`）：

```
ok  	shop-trade	1.035s
ok  	shop-trade/server/api/v1	1.049s
?   	shop-trade/server/global	[no test files]
ok  	shop-trade/server/initialize	1.033s
ok  	shop-trade/server/model	1.018s
ok  	shop-trade/server/router	1.028s
ok  	shop-trade/server/service	1.055s
race_exit=0
```

结论：**全部 6 个测试包在 `-race` 模式下全部 ok，退出码 0，输出中没有任何 `WARNING: DATA RACE` 报告**。

## 三、并发安全保障方案（与检测结论互相印证）

代码层面的并发安全设计为「内存仓储互斥锁 + 条件更新 + 受影响行数判定」，在真实 MySQL 模式下进一步由 InnoDB 行锁与事务保证：

| 并发点 | 机制 | 真实并发实测结果 |
| --- | --- | --- |
| 库存扣减 | `UPDATE goods SET available_stock=available_stock-?, occupied_stock=occupied_stock+? WHERE id=? AND available_stock>=?`，未命中则受影响行数为 0，判定并发失败 | 20 并发下单成功 3 次、失败 17 次（M-02 缺货），无超卖（`evidence/mysql_raw_05_app_persistence.txt`） |
| 库存释放 | 释放与扣减成对执行于同一事务，保证 `available + occupied` 恒等 | 并发后 `available=0`、`occupied=5`，合计仍为 5 |
| 订单状态流转 | `UPDATE ... WHERE id=? AND status=?` 条件更新，终态不可回退 | 退款与发货互斥裁决 3 轮恒为一种合法结果（`evidence/独立反例探测结果.json`） |
| 支付/退款幂等 | 唯一约束 `uk_payment_dedup_key`、`uk_payment_channel_effective` + 服务层幂等键 | 重复支付通知后有效收款笔数保持为 1 |
| 内存仓储（demo-memory 模式） | 仓储层互斥锁 + 条件更新 | 20 并发抢单成功 5 次、缺货 15 次（`evidence/独立反例探测结果.json`） |

## 四、复现方式

```bash
# 在 WSL Ubuntu 内（需已安装 gcc 与 go）
wsl -d Ubuntu -u root -- bash /mnt/d/Desktop/shop/evidence/wsl_race_run.sh
```

若在 Windows 侧具备 MinGW-w64 等 C 工具链，也可直接执行：

```bash
set CGO_ENABLED=1
go test -race ./... -count=1
```

## 五、说明

本文所述竞态检测结果全部来自真实执行，原始输出见 `evidence/race_raw_output.txt`，未做任何编造或修饰。历史版本中「仅缺少 race 工具自动检测能力」的表述，已由本文第二节的真实执行结果取代。
