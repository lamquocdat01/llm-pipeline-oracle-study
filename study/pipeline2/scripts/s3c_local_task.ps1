# Task cho do bu P6 (R2-02), nhanh local. ASCII thuan (PS 5.1).
# Chay: desktop venv python -> scripts/run_s3c.py local ; cho khung dem 23-08, chay tiep tu checkpoint, dung truoc 08:00.
$repo = 'D:\THS Programing\Microduck'
$py = Join-Path $repo 'desktop\.venv\Scripts\python.exe'
$wd = Join-Path $repo 'study\pipeline2'
$log = Join-Path $wd ('results\S3C_local_' + (Get-Date -Format 'yyyyMMdd_HHmm') + '.log')
$env:PYTHONIOENCODING = 'utf-8'
$env:THS_DATASETS = 'D:\Datasets'
Set-Location $wd
& $py 'scripts\run_s3c.py' 'local' '--zip-dir' 'D:\Datasets\_tools\ollama_0.40.16' *>> $log
"exit=$LASTEXITCODE" | Out-File -Append -Encoding utf8 $log
