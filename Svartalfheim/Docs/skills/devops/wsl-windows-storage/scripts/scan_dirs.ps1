# Scan for largest directories/files on a Windows drive from WSL
# Usage: powershell.exe -ExecutionPolicy Bypass -File /tmp/scan_dirs.ps1 -Path "C:\Users\Game_"
#        powershell.exe -ExecutionPolicy Bypass -File /tmp/scan_dirs.ps1 -Path "C:\Users\Game_\AppData\Local"

param(
    [string]$Path = "C:\Users\Game_",
    [double]$MinGB = 0.5
)

$minBytes = $MinGB * 1GB

Write-Host "Scanning $Path for directories larger than $MinGB GB..."
Write-Host ""

Get-ChildItem $Path -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $s = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        if ($s -gt $minBytes) {
            $sizeGB = [math]::Round($s / 1GB, 2)
            Write-Host "$sizeGB GB - $($_.Name)"
        }
    } catch {
        # Skip inaccessible directories
    }
} | Sort-Object -Descending