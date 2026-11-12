# shop-trade 题目01：第 1 轮单元测试 + 竞态检测可重复执行脚本（草案）
# 正式证据必须由测试 Agent 在独立会话、dev/01 对应提交版本、真实 MySQL(InnoDB) 环境与可控 HTTP 模拟渠道上执行。
# 本机 CGO_ENABLED=0 且无 C 编译器，脚本会如实记录 race 前置条件不满足，不伪造通过结论。

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Host "[$stamp] 第 1 轮门禁脚本开始，工作目录 $root"

# 1. 格式与静态检查
"执行时间: $stamp" | Out-File -Encoding utf8 gofmt-vet-output.txt
"--- gofmt -l . ---" | Out-File -Append -Encoding utf8 gofmt-vet-output.txt
gofmt -l . 2>&1 | Out-File -Append -Encoding utf8 gofmt-vet-output.txt
"--- go vet ./... ---" | Out-File -Append -Encoding utf8 gofmt-vet-output.txt
go vet ./... 2>&1 | Out-File -Append -Encoding utf8 gofmt-vet-output.txt
"go vet exit=$LASTEXITCODE" | Out-File -Append -Encoding utf8 gofmt-vet-output.txt

# 2. 单元测试与覆盖率原始文件（service 核心业务包 + 全量自编生产代码两种口径）
go test "-coverprofile=coverage.out" ./server/service/... -count=1 2>&1 | Tee-Object -FilePath unit-test-output.txt
go tool cover "-func=coverage.out" 2>&1 | Tee-Object -FilePath coverage-report-raw.txt

go test "-coverpkg=./..." "-coverprofile=coverage-all.out" ./... -count=1 2>&1 | Tee-Object -FilePath coverage-all-output.txt
go tool cover "-func=coverage-all.out" 2>&1 | Tee-Object -FilePath coverage-all-report-raw.txt

# 3. 竞态检测：必须在 CGO_ENABLED=1 且有 C 编译器的环境执行
"执行时间: $stamp" | Out-File -Encoding utf8 race-output.txt
$cgo = (go env CGO_ENABLED).Trim()
"CGO_ENABLED=$cgo" | Out-File -Append -Encoding utf8 race-output.txt
if ($cgo -ne '1') {
    "前置条件不满足：go test -race 需要 CGO_ENABLED=1 与可用 C 编译器；本机未产出正式 race 证据。" | Out-File -Append -Encoding utf8 race-output.txt
    Write-Warning "CGO_ENABLED=$cgo，跳过 race；正式证据由测试 Agent 在具备 gcc/clang 的环境补跑。"
} else {
    "--- go test -race -coverprofile=coverage-race.out ./... ---" | Out-File -Append -Encoding utf8 race-output.txt
    go test -race "-coverprofile=coverage-race.out" ./... -count=1 2>&1 | Tee-Object -FilePath race-output-raw.txt
    "race exit=$LASTEXITCODE；原始输出见 race-output-raw.txt" | Out-File -Append -Encoding utf8 race-output.txt
}

Write-Host "[$stamp] 结束。请核对 coverage.out、coverage-all.out、race-output.txt、gofmt-vet-output.txt 与 unit-test-output.txt 的原始内容。"
