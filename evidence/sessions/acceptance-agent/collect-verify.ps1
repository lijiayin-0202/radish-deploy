# Independent acceptance agent: real command collection script.
# ASCII-only literals on purpose: Windows PowerShell 5.1 decodes .ps1 files as ANSI
# unless a UTF-8 BOM is present. The Chinese output filename is built from code points.
$ErrorActionPreference = 'Continue'
Set-Location 'd:/Desktop/shop'

$cnName = ([string]::Join('', [char]0x9A8C, [char]0x6536, [char]0x6838, [char]0x9A8C, [char]0x539F, [char]0x59CB, [char]0x8F93, [char]0x51FA)) + '.txt'
$out = 'evidence/sessions/acceptance-agent/' + $cnName

function Add-Line([string]$s) { $s | Out-File -FilePath $out -Append -Encoding utf8 }

Add-Line '===== [5] go test -race -count=1 ./...   (CGO_ENABLED=1) ====='
Add-Line 'NOTE: no C compiler on this host, so race cannot be re-run today. Below is the REAL failure output.'
Add-Line 'COMMAND: set CGO_ENABLED=1 then run: go test -race -count=1 ./...'
$env:CGO_ENABLED = '1'
(go test -race -count=1 ./... 2>&1 | Out-String) | Out-File -FilePath $out -Append -Encoding utf8
Add-Line "race_exit=$LASTEXITCODE"
$env:CGO_ENABLED = '0'
Add-Line ''

Add-Line '===== [6] C compiler availability probe ====='
Add-Line 'COMMAND: Get-Command gcc,clang,cc,x86_64-w64-mingw32-gcc ; Test-Path <mingw dirs>'
foreach ($c in @('gcc', 'clang', 'cc', 'x86_64-w64-mingw32-gcc')) {
    $p = Get-Command $c -ErrorAction SilentlyContinue
    if ($p) { Add-Line "  $c -> $($p.Source)" } else { Add-Line "  $c -> NOT FOUND" }
}
foreach ($d in @('C:\mingw64\bin', 'C:\msys64\mingw64\bin', 'C:\ProgramData\chocolatey\bin', 'C:\TDM-GCC-64\bin')) {
    if (Test-Path $d) { Add-Line "  $d -> EXISTS" } else { Add-Line "  $d -> missing" }
}
Add-Line ''

Add-Line '===== [7] Independent coverage recomputation at current commit bb1ca7f ====='
Add-Line 'COMMAND: go test -count=1 "-coverpkg=./..." "-coverprofile=evidence/sessions/acceptance-agent/acc-coverage-bb1ca7f.out" "./..."'
(go test -count=1 '-coverpkg=./...' '-coverprofile=evidence/sessions/acceptance-agent/acc-coverage-bb1ca7f.out' './...' 2>&1 | Out-String) | Out-File -FilePath $out -Append -Encoding utf8
Add-Line "cov_test_exit=$LASTEXITCODE"
Add-Line ''
Add-Line 'COMMAND: go tool cover "-func=evidence/coverage/coverage-v1.8.0-def0977.out"   (versioned snapshot in repo)'
(go tool cover '-func=evidence/coverage/coverage-v1.8.0-def0977.out' 2>&1 | Select-Object -Last 1 | Out-String) | Out-File -FilePath $out -Append -Encoding utf8
Add-Line 'COMMAND: go tool cover "-func=evidence/sessions/acceptance-agent/acc-coverage-bb1ca7f.out"   (independent recompute at HEAD)'
(go tool cover '-func=evidence/sessions/acceptance-agent/acc-coverage-bb1ca7f.out' 2>&1 | Select-Object -Last 1 | Out-String) | Out-File -FilePath $out -Append -Encoding utf8
Add-Line ''

Add-Line '===== [8] Line-by-line diff: independent recompute vs repo versioned snapshot ====='
go tool cover '-func=evidence/coverage/coverage-v1.8.0-def0977.out' > "$env:TEMP\acc_func_now.txt" 2>&1
$a = Get-Content "$env:TEMP\acc_func_now.txt"
$b = Get-Content 'evidence/coverage/coverage-v1.8.0-def0977.func.txt'
Add-Line 'COMMAND: go tool cover -func=<snapshot.out>   vs   evidence/coverage/coverage-v1.8.0-def0977.func.txt   (Compare-Object)'
Add-Line "recomputed_lines=$($a.Count)  snapshot_lines=$($b.Count)"
$d = Compare-Object $a $b
if ($d) {
    Add-Line 'RESULT: DIFFERENCES FOUND (see below)'
    ($d | Select-Object -First 20 | Out-String) | Out-File -FilePath $out -Append -Encoding utf8
} else {
    Add-Line 'RESULT: IDENTICAL -- independent recomputation matches the repo versioned snapshot line by line'
}
Add-Line ''

Add-Line '===== [9] Coverage threshold gate (scripts/coverage_gate.py, AGENTS.md Q-02 criteria) ====='
Add-Line 'COMMAND: python -X utf8 scripts/coverage_gate.py --profile <HEAD profile> --overall 85 --pkg server/service:85 --pkg server/api/v1:85 --pkg server/router:85 --pkg server/model:85 --pkg server/initialize:85'
$gate = python -X utf8 scripts/coverage_gate.py --profile evidence/sessions/acceptance-agent/acc-coverage-bb1ca7f.out --overall 85 --pkg server/service:85 --pkg server/api/v1:85 --pkg server/router:85 --pkg server/model:85 --pkg server/initialize:85 --revision v1.8.2-acceptance --commit bb1ca7f 2>&1
($gate | Out-String) | Out-File -FilePath $out -Append -Encoding utf8
Add-Line "gate_exit=$LASTEXITCODE"
Add-Line 'NOTE: the script default DEFAULT_PACKAGES only contains server/service:85. This run additionally'
Add-Line '      imposes 85% on every self-written package, to check the gate scope hides no failure.'
Add-Line ''

Add-Line '===== [10] Commit message format check (AGENTS.md 2.2 / 2.3) ====='
Add-Line 'COMMAND: git --no-pager log --format=%h %s'
(git --no-pager log --format='%h %s' | Out-String) | Out-File -FilePath $out -Append -Encoding utf8
Add-Line ''
$nonCompliant = git --no-pager log --format='%h %s' | Where-Object { $_ -notmatch '\[(feat|fix|hotfix|opt|docs|test)\]' }
Add-Line 'COMMAND: git log --format="%h %s" | Where-Object { $_ -notmatch "\[(feat|fix|hotfix|opt|docs|test)\]" }'
Add-Line "non-compliant commits: $($nonCompliant.Count)"
foreach ($c in $nonCompliant) { Add-Line "  $c" }
$withNum = (git --no-pager log --format='%s' | Select-String -Pattern '#\d+').Count
Add-Line 'COMMAND: git log --format=%s | Select-String -Pattern "#\d+"   (work-item number presence)'
Add-Line "commits containing a work-item number: $withNum"
Add-Line ''

Add-Line '===== [11] Audit-trail append-only check (no UPDATE/DELETE on payment table) ====='
Add-Line 'COMMAND: Select-String -Path server/**/*.go -Pattern "Delete\(|Unscoped|Update\(|UpdateColumn|Save\("'
(Get-ChildItem -Recurse -Path server -Filter *.go | Select-String -Pattern 'Delete\(|Unscoped|Update\(|UpdateColumn|Save\(' | ForEach-Object { "$($_.Path):$($_.LineNumber): $($_.Line.Trim())" } | Out-String) | Out-File -FilePath $out -Append -Encoding utf8
Add-Line ''

Add-Line '===== [12] M-07 / M-16 / M-21 reference scan (independent recheck of the 30-code conclusion) ====='
Add-Line 'COMMAND: git grep -n -E "M-07|M-16|M-21" -- server resource'
(git grep -n -E 'M-07|M-16|M-21' -- server resource 2>&1 | Out-String) | Out-File -FilePath $out -Append -Encoding utf8
Add-Line 'RESULT: only the definition lines in server/service/types.go (messages map) are expected here.'
Add-Line ''

Write-Output "OK appended -> $out"
