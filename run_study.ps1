<#
.SYNOPSIS
    Runs the Earth2Studio study runner using the verified environment.
.EXAMPLE
    .\run_study.ps1 -Days 7
#>
param(
    [int]$Days = 7
)

$targetPath = "/mnt/d/programming/Blockchain development/Z-space/earth2studio"
wsl.exe -d Ubuntu -e bash -c "cd '$targetPath' && .venv/bin/python -m od_experiments.scientific_study.study_runner --days $Days"
