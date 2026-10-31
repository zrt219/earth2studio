@echo off
REM Earth2Studio launcher script for Windows Command Prompt
set "TARGET_PATH=/mnt/d/programming/Blockchain development/Z-space/earth2studio"
wsl.exe -d Ubuntu -e bash -c "cd '%TARGET_PATH%' && .venv/bin/python -m od_experiments.scientific_study.study_runner %*"
