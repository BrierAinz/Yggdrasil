@echo off
cd /d "%~dp0"
python Scripts/cifar10_wide_resnet_gauntlet.py --epochs 50
pause
