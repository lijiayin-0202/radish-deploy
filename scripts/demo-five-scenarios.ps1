# 题目 01 五组强制演示场景 HTTP 演示脚本（开发草稿，不是第 2 轮正式接口证据）
# 前置：先启动服务（go run main.go 或编译出的二进制），默认地址 http://127.0.0.1:8080
# 与 docs/interface-list.md v1.0 定稿一致；若用 GVA_ADDR 改端口，需传 -BaseUrl 覆盖。
# 建议用全新进程执行，因脚本会推进服务端演示时钟并消耗库存。
# 身份由 X-Demo-Account 解析；X-Role / X-User-Id 一律不作为身份依据。
param(
    [string]$BaseUrl = 'http://127.0.0.1:8080'
)
$ErrorActionPreference = 'Stop'

function Invoke-Api {
    param([string]$Method, [string]$Path, [string]$Account, [object]$Body, [hashtable]$ExtraHeaders)
    $headers = @{ 'X-Demo-Account' = $Account }
    if ($null -ne $ExtraHeaders) {
        foreach ($k in $ExtraHeaders.Keys) { $headers[$k] = $ExtraHeaders[$k] }
    }
    $params = @{ Method = $Method; Uri = ($BaseUrl + $Path); Headers = $headers }
    if ($null -ne $Body) {
        $params.Body = ($Body | ConvertTo-Json -Depth 6 -Compress)
        $params.ContentType = 'application/json'
    }
    return Invoke-RestMethod @params
}

function Show-Step {
    param([string]$Id, [string]$Name, [object]$Resp)
    Write-Output ("[{0}] {1} => code={2} message={3}" -f $Id, $Name, $Resp.code, $Resp.message)
}

Write-Output '=== TST-S1 活动正常成交 ==='
$o1 = Invoke-Api POST '/api/v1/orders' 'buyer01' @{ goods_id = 1; quantity = 2 }
Show-Step 'S1-01' '买家下单 2 件' $o1
$s1No = $o1.data.order_no
$p1 = Invoke-Api POST '/api/v1/payment/callback' 'mock01' @{ order_no = $s1No; channel_trade_no = 'S1-PAY-001'; amount = 20000; signature_valid = $true }
Show-Step 'S1-02' '模拟渠道支付成功' $p1
$st1 = Invoke-Api GET "/api/v1/orders/$s1No/status" 'buyer01'
Show-Step 'S1-03' ('订单状态查询 status=' + $st1.data.status) $st1
$sh1 = Invoke-Api POST "/api/v1/orders/$s1No/shipment" 'warehouse01' @{ carrier = '顺丰'; tracking_no = 'SF-S1-001' }
Show-Step 'S1-04' '仓库登记发货' $sh1
$dupShip = Invoke-Api POST "/api/v1/orders/$s1No/shipment" 'warehouse01' @{ carrier = '顺丰'; tracking_no = 'SF-S1-002' }
Show-Step 'S1-05' '重复发货应被拒绝' $dupShip
$sum1 = Invoke-Api GET '/api/v1/ops/summary' 'ops01'
Show-Step 'S1-06' '运营核查汇总' $sum1

Write-Output '=== TST-S2 缺货与弃单（库存释放 / 20 次抢单）==='
$success = 0
$reject = 0
$firstNo = ''
for ($i = 1; $i -le 20; $i++) {
    $r = Invoke-Api POST '/api/v1/orders' 'buyer02' @{ goods_id = 1; quantity = 1 }
    if ($r.code -eq '0') {
        $success++
        if ($firstNo -eq '') { $firstNo = $r.data.order_no }
    } else {
        $reject++
    }
}
Write-Output ("[S2-01] 20 次抢单 => 成功={0} 被拒={1}（库存守恒，绝不超卖；真实并发请用 Apipost 20 并发用例 + go test -race）" -f $success, $reject)
$cancel = Invoke-Api POST "/api/v1/orders/$firstNo/cancel" 'buyer02'
Show-Step 'S2-02' '买家取消弃单（释放一次）' $cancel
$cancelDup = Invoke-Api POST "/api/v1/orders/$firstNo/cancel" 'buyer02'
Show-Step 'S2-03' '重复取消应被拒绝' $cancelDup

Write-Output '=== TST-S3 售前退款（渠道首次失败、再次成功）==='
$o3 = Invoke-Api POST '/api/v1/orders' 'buyer01' @{ goods_id = 2; quantity = 1 }
Show-Step 'S3-01' '下单' $o3
$s3No = $o3.data.order_no
Invoke-Api POST '/api/v1/payment/callback' 'mock01' @{ order_no = $s3No; channel_trade_no = 'S3-PAY-001'; amount = 10000; signature_valid = $true } | Out-Null
$apply = Invoke-Api POST "/api/v1/orders/$s3No/refund/apply" 'buyer01' @{ reason = '不想要了' }
Show-Step 'S3-02' '买家申请整单退款' $apply
$shipBlocked = Invoke-Api POST "/api/v1/orders/$s3No/shipment" 'warehouse01' @{ carrier = '顺丰'; tracking_no = 'SF-S3-001' }
Show-Step 'S3-03' '申请期间发货应暂停' $shipBlocked
$approve = Invoke-Api POST "/api/v1/orders/$s3No/refund/approve" 'cs01' @{ remark = '同意整单退款' }
Show-Step 'S3-04' '客服同意并写明原因' $approve
$rfFail = Invoke-Api POST '/api/v1/refund/callback' 'mock01' @{ order_no = $s3No; refund_channel_trade_no = 'S3-RF-001'; amount = 10000; signature_valid = $true; success = $false }
Show-Step 'S3-05' '模拟渠道首次退款失败' $rfFail
$retry = Invoke-Api POST "/api/v1/orders/$s3No/refund/retry" 'cs01' @{ remark = '客服重试' }
Show-Step 'S3-06' '客服重试登记' $retry
$rfOk = Invoke-Api POST '/api/v1/refund/callback' 'mock01' @{ order_no = $s3No; refund_channel_trade_no = 'S3-RF-001'; amount = 10000; signature_valid = $true; success = $true }
Show-Step 'S3-07' '退款再次成功' $rfOk
$rfDup = Invoke-Api POST '/api/v1/refund/callback' 'mock01' @{ order_no = $s3No; refund_channel_trade_no = 'S3-RF-001'; amount = 10000; signature_valid = $true; success = $true }
Show-Step 'S3-08' '重复退款通知应幂等' $rfDup
$st3 = Invoke-Api GET "/api/v1/orders/$s3No/status" 'buyer01'
Show-Step 'S3-09' ('退款后状态 status=' + $st3.data.status) $st3

Write-Output '=== TST-S4 迟到支付（终态不变 + 异常核实退款）==='
$o4 = Invoke-Api POST '/api/v1/orders' 'buyer03' @{ goods_id = 2; quantity = 1 }
Show-Step 'S4-01' '下单' $o4
$s4No = $o4.data.order_no
$clock = Invoke-Api POST '/api/v1/admin/clock' 'ops01' @{ offset_minutes = 11 }
Show-Step 'S4-02' '运营推进演示教学时钟 11 分钟' $clock
$closed = Invoke-Api POST '/api/v1/admin/orders/close-expired' 'ops01' @{ limit = 100 }
Show-Step 'S4-03' '超时关闭待支付订单' $closed
$late = Invoke-Api POST '/api/v1/payment/callback' 'mock01' @{ order_no = $s4No; channel_trade_no = 'S4-LATE-001'; amount = 10000; signature_valid = $true }
Show-Step 'S4-04' '关闭后迟到支付成功通知' $late
$eventID = $late.data.event_id
$sum4 = Invoke-Api GET '/api/v1/ops/summary' 'ops01'
Show-Step 'S4-05' ('运营核查异常待处理数=' + $sum4.data.late_payment_events) $sum4
$verify = Invoke-Api POST "/api/v1/late-payment/$eventID/verify" 'cs01' @{ reason = '核实为迟到支付' }
Show-Step 'S4-06' '客服核实并写明原因' $verify
$initiate = Invoke-Api POST "/api/v1/late-payment/$eventID/refund/initiate" 'cs01' @{ refund_no = 'S4-LR-001'; reason = '核实后发起退款' }
Show-Step 'S4-07' '发起迟到支付退款' $initiate
$lrFail = Invoke-Api POST '/api/v1/late-payment/refund/callback' 'mock01' @{ event_id = $eventID; refund_no = 'S4-LR-001'; amount = 10000; signature_valid = $true; success = $false }
Show-Step 'S4-08' '迟到支付退款失败' $lrFail
$lrRetry = Invoke-Api POST '/api/v1/late-payment/refund/retry' 'cs01' @{ event_id = $eventID; refund_no = 'S4-LR-001'; remark = '客服重试' }
Show-Step 'S4-09' '迟到支付退款重试' $lrRetry
$lrOk = Invoke-Api POST '/api/v1/late-payment/refund/callback' 'mock01' @{ event_id = $eventID; refund_no = 'S4-LR-001'; amount = 10000; signature_valid = $true; success = $true }
Show-Step 'S4-10' '迟到支付退款成功' $lrOk
$st4 = Invoke-Api GET "/api/v1/orders/$s4No/status" 'buyer03'
Show-Step 'S4-11' ('终态保持 status=' + $st4.data.status) $st4
Invoke-Api POST '/api/v1/admin/clock' 'ops01' @{ offset_minutes = 0 } | Out-Null

Write-Output '=== TST-S5 操作竞争、重复通知与越权 ==='
$o5 = Invoke-Api POST '/api/v1/orders' 'buyer01' @{ goods_id = 1; quantity = 1 }
$s5No = $o5.data.order_no
Invoke-Api POST '/api/v1/payment/callback' 'mock01' @{ order_no = $s5No; channel_trade_no = 'S5-PAY-001'; amount = 10000; signature_valid = $true } | Out-Null
$dupPay = Invoke-Api POST '/api/v1/payment/callback' 'mock01' @{ order_no = $s5No; channel_trade_no = 'S5-PAY-001'; amount = 10000; signature_valid = $true }
Show-Step 'S5-01' '重复支付通知应幂等' $dupPay
$badSign = Invoke-Api POST '/api/v1/payment/callback' 'mock01' @{ order_no = $s5No; channel_trade_no = 'S5-BAD-SIGN'; amount = 10000; signature_valid = $false }
Show-Step 'S5-02' '验签失败' $badSign
$badAmt = Invoke-Api POST '/api/v1/payment/callback' 'mock01' @{ order_no = $s5No; channel_trade_no = 'S5-BAD-AMT'; amount = 9999; signature_valid = $true }
Show-Step 'S5-03' '金额不符' $badAmt
$unknown = Invoke-Api POST '/api/v1/payment/callback' 'mock01' @{ order_no = 'NOT-EXIST'; channel_trade_no = 'S5-UNKNOWN'; amount = 10000; signature_valid = $true }
Show-Step 'S5-04' '未知订单' $unknown
$raceApply = Invoke-Api POST "/api/v1/orders/$s5No/refund/apply" 'buyer01' @{ reason = '并发申请' }
Show-Step 'S5-05' '退款申请与发货竞争：申请先到' $raceApply
$raceShip = Invoke-Api POST "/api/v1/orders/$s5No/shipment" 'warehouse01' @{ carrier = '顺丰'; tracking_no = 'SF-S5-001' }
Show-Step 'S5-06' '退款申请与发货竞争：发货后到应被拒' $raceShip
$denied = Invoke-Api GET "/api/v1/orders/$s1No" 'buyer02'
Show-Step 'S5-07' 'buyer02 越权查询 buyer01 订单' $denied
$denied2 = Invoke-Api GET "/api/v1/orders/$s1No" 'buyer02' $null @{ 'X-User-Id' = '1001'; 'X-Role' = '买家' }
Show-Step 'S5-08' '篡改请求用户编号仍应拒绝' $denied2
$sum5 = Invoke-Api GET '/api/v1/ops/summary' 'ops01'
Show-Step 'S5-09' '运营最终核查' $sum5

Write-Output '=== 五组场景 HTTP 演示结束：接口已可从头到尾调用；正式第 2 轮结果须由测试 Agent 在独立会话用 Apipost 运行导出 ==='
