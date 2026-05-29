# claude.ps1 - 通过 cc-switch HTTP 代理调用 Claude
# 用法: .\claude.ps1 "你的问题"

param([string]$question)

if (-not $question) {
    Write-Host "用法: .\claude.ps1 `"你的问题`""
    exit 1
}

$body = @{
    model = "claude-sonnet-4-20250514"
    max_tokens = 4096
    messages = @(@{role = "user"; content = $question})
} | ConvertTo-Json -Depth 3 -Compress

$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)
[System.Net.Http.HttpClient]$client = @{
    Timeout = [TimeSpan]::FromSeconds(180)
}

# Use Invoke-WebRequest with proper encoding handling
$resp = Invoke-WebRequest -Uri "http://127.0.0.1:15721/v1/messages" `
    -Method Post `
    -ContentType "application/json" `
    -Headers @{
        "x-api-key" = "PROXY_MANAGED"
        "anthropic-version" = "2023-06-01"
    } `
    -Body $bodyBytes `
    -TimeoutSec 180 `
    -UseBasicParsing

$data = $resp.Content | ConvertFrom-Json
foreach ($item in $data.content) {
    if ($item.type -eq 'text') {
        Write-Host $item.text
    }
}
