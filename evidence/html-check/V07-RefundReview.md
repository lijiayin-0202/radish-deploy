# V07 页面测试截图说明与独立访问断言

| 项 | 内容 |
| --- | --- |
| 页面 | `/static/v07-refund-review.html` |
| 原型视图 | V07 RefundReview |
| 演示账号 | `cs01` |
| 采集时间 | 2026-11-12T14:58:15.053201+08:00 |
| 运行模式 | `demo-memory`（本地编译实例，非真实 MySQL / 非部署版本） |

## 独立访问断言（本页单独执行，不合并汇总）

| 编号 | 断言 | 实际 | 结论 |
| --- | --- | --- | --- |
| A1 | HTTP 状态 200 | 200 | PASS |
| A2 | 含 `<title>` | True | PASS |
| A3 | 含 `<h1>` 视图标题 | True | PASS |
| A4 | 引用 `/static/app.js` | True | PASS |
| A5 | 含 `Shop.init` 身份初始化 | True | PASS |
| A6 | 含 `id="out"` 结果区 | True | PASS |
| A7 | 响应字节数 > 0 | 3411 | PASS |

## 截图说明（如实标注，不伪造）

- **本轮未生成浏览器截图文件**：本机复核只做 HTTP 层访问断言，未使用浏览器自动化、未导出截图。
- 截图须由第 3 轮浏览器页面验收在**独立验收 Agent 会话**中补充，并与本页 A1~A7 断言、提交哈希、采集时间一起归档。
- 本文件不冒充截图、不冒充第 3 轮验收结论、不冒充独立测试/验收会话产物。

## 关联证据

- 单页冒烟记录：`evidence/smoke/PAGE-V07.txt`
- 页面源码：`resource/static/v07-refund-review.html`
- 接口契约：`docs/interface-list.md` 第 6.1 节 / 附录 A

---

## 第五轮增强断言（A8~A12）

| 项 | 内容 |
| --- | --- |
| 增强断言采集时间 | 2026-11-12T16:22:22.954133+08:00 |
| 采集方式 | 静态页面源码逐项断言 + HTTP 层复核（真实 GET 静态页） |
| HTTP 层复核 | `GET /static/v07-refund-review.html` → HTTP 200（3411 字节）→ **PASS** |
| 口径 | **静态源码 + HTTP 层断言**；非浏览器截图、非第 3 轮浏览器验收、非独立验收会话 |

| 编号 | 断言 | 实际 | 结论 |
| --- | --- | --- | --- |
| A8 | 本页（含公共脚本 `app.js`）引用的 /api/v1 路径均登记在 `docs/interface-list.md`（API-01~API-23） | /api/v1/orders/：页面/app.js=app.js=True，接口表=True；/refund/approve：页面/app.js=app.js=True，接口表=True；/refund/reject：页面/app.js=app.js=True，接口表=True；/refund/retry：页面/app.js=app.js=True，接口表=True；/api/v1/refund/callback：页面/app.js=app.js=True，接口表=True；/api/v1/ops/stock-check/：页面/app.js=app.js=True，接口表=True；/api/v1/ops/summary：页面/app.js=app.js=True，接口表=True | PASS |
| A9 | 关键按钮 ID 存在且以 `Shop.click` 绑定（有入口且有行为） | 8 个按钮全部命中：btnApprove,btnReject,btnRetry,btnDetail,btnFail,btnOK,btnCheck,btnSummary | PASS |
| A10 | 页内 M-xx 失败原因编号属于 M-01~M-30，且该页必现编号确实出现 | 页内出现 M-08,M-24；越界编号 无；必现缺失 无 | PASS |
| A11 | `Shop.init` 演示账号角色与视图角色一致 | Shop.init('cs01') → 角色 客服；期望 客服 | PASS |
| A12 | 仅使用 GET/POST，无 DELETE/PUT/PATCH，无删除或直接改写订单状态入口 | Shop.call 显式方法 ['POST']；源码中出现的写动词 ['POST']；越界动词 无 | PASS |

### A8 契约一致性逐路径明细

| 接口路径 | 页面源码 / app.js | 接口契约表 | 结论 |
| --- | --- | --- | --- |
| /api/v1/orders/ | 页面/app.js=True | 接口表=True | PASS |
| /refund/approve | 页面/app.js=True | 接口表=True | PASS |
| /refund/reject | 页面/app.js=True | 接口表=True | PASS |
| /refund/retry | 页面/app.js=True | 接口表=True | PASS |
| /api/v1/refund/callback | 页面/app.js=True | 接口表=True | PASS |
| /api/v1/ops/stock-check/ | 页面/app.js=True | 接口表=True | PASS |
| /api/v1/ops/summary | 页面/app.js=True | 接口表=True | PASS |

### A9 关键交互入口逐按钮明细

| 按钮 ID | 元素存在 | 行为绑定 | 结论 |
| --- | --- | --- | --- |
| btnApprove | id 存在=True | Shop.click 绑定=True | PASS |
| btnReject | id 存在=True | Shop.click 绑定=True | PASS |
| btnRetry | id 存在=True | Shop.click 绑定=True | PASS |
| btnDetail | id 存在=True | Shop.click 绑定=True | PASS |
| btnFail | id 存在=True | Shop.click 绑定=True | PASS |
| btnOK | id 存在=True | Shop.click 绑定=True | PASS |
| btnCheck | id 存在=True | Shop.click 绑定=True | PASS |
| btnSummary | id 存在=True | Shop.click 绑定=True | PASS |

> A8~A12 只证明「页面声明与接口契约、角色、失败原因、写操作口径一致」，**不替代浏览器端渲染与交互验收**；截图仍须由第 3 轮浏览器验收在独立验收会话中补充。

## 第五轮关联证据

- 增强断言采集脚本：`scripts/r5_htmlcheck_enhance.py`
- 页面源码：`resource/static/v07-refund-review.html`
- 接口契约：`docs/interface-list.md`（附录 A 的 API-01~API-23 契约表、附录 B 全量边界矩阵）
- 同批次证据：`evidence/partial-closure/`、`evidence/manual-round2/`
