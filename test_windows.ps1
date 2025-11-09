$job = @{
    id = "test123"
    command = "echo Testing 123"
} | ConvertTo-Json -Compress

Write-Host "Testing QueueCTL System..."
Write-Host "`nEnqueuing job..."
python queuectl.py enqueue $job

Write-Host "`nStarting worker..."
$worker = Start-Process python -ArgumentList "queuectl.py", "worker", "start" -NoNewWindow -PassThru

Write-Host "`nChecking status after 2 seconds..."
Start-Sleep -Seconds 2
python queuectl.py status

Write-Host "`nListing completed jobs..."
python queuectl.py list --state completed

Write-Host "`nStopping worker..."
Stop-Process -Id $worker.Id -Force