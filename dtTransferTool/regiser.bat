@echo off
echo ��Ӳ����������
echo ��ȫ·���� %~dp0
set regpath=HKEY_CURRENT_USER\Environment
set evname= MAYA_PLUG_IN_PATH
set toolpath= %~dp0
reg add "%regpath%" /v %evname% /d %toolpath% /f
pause>nul