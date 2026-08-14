@echo off
REM ============================================================================
REM  24h 税务/政策监控入口：由 Windows 任务计划程序每 6 小时调用本脚本。
REM  执行 scrapy monitor —— 巡检所有站点，发现新政策推送微信。
REM ============================================================================
setlocal

REM 运行环境：development / production / testing
set SCRAPY_ENV=production

REM —— Python 解释器：建议用项目虚拟环境（改成你自己的路径）——
set PYTHON=C:\Users\SLAMM3USER\.workbuddy\binaries\python\envs\default\Scripts\python.exe
REM 若没单独建 venv，可改为： set PYTHON=python

REM —— 切到项目根目录（本脚本放在项目根或 scripts\ 下均可）——
cd /d "%~dp0\.."

%PYTHON% -m scrapy monitor
if errorlevel 1 (
    echo [monitor] scrapy monitor exited with errors; check logs\crawler.log
)
endlocal
