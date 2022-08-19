@echo off
echo 添加插件环境变量
echo 完全路径： %~dp0
set regpath=HKEY_CURRENT_USER\Environment
set evname= MAYA_PLUG_IN_PATH
set toolpath= %~dp0
reg add "%regpath%" /v %evname% /d %toolpath% /f
pause>nul