# Do bu P6 (R2-02) - sua doi 2 (P6/PREREG_ADDENDUM_MD_AMEND2_20261124.md): chay NGAY, ngoai khung dem, luot cuoi.
# ASCII thuan (PS 5.1). Han luot 4 h 30 tu luc bat dau (results/S3C_LUOT_<ngay>.json).
$repo = 'D:\THS Programing\Microduck'
$py = Join-Path $repo 'desktop\.venv\Scripts\python.exe'
$wd = Join-Path $repo 'study\pipeline2'
$log = Join-Path $wd ('results\S3C_local_' + (Get-Date -Format 'yyyyMMdd_HHmm') + '.log')
$env:PYTHONIOENCODING = 'utf-8'
$env:THS_DATASETS = 'D:\Datasets'
Set-Location $wd
& $py 'scripts\run_s3c.py' 'local' '--bo-khung-dem' '--zip-dir' 'D:\Datasets\_tools\ollama_0.40.16' *>> $log
"exit=$LASTEXITCODE" | Out-File -Append -Encoding utf8 $log
