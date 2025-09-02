@echo off
setlocal enabledelayedexpansion

REM ===== 切换到父目录 =====
cd /d "%~dp0.." || (
    echo [ERROR] 无法切换到父目录！
    pause
    exit /b 1
)

REM ===== 创建符号链接（Junction） =====
REM 检查并创建 PicoammeterCtlrLib 链接
if not exist "PicoammeterCtlrLib" (
    mklink /J PicoammeterCtlrLib SEM_UI_PicoammeterCtrlLib >nul 2>&1 || (
        echo [ERROR] 创建 Junction 失败！请确认目标目录 SEM_UI_PicoammeterCtrlLib 存在
        pause
        exit /b 1
    )
    echo [OK] Junction 创建成功
) else (
    echo [SKIP] PicoammeterCtlrLib 已存在，跳过创建
)

REM 检查并创建 PicoammeterCtlrLib 链接
if not exist "AutoFocusLib" (
    mklink /J AutomationLib AutoFocusLib >nul 2>&1 || (
        echo [ERROR] 创建 AutomationLib 失败！请确认目标目录 AutoFocusLib 存在
        pause
        exit /b 1
    )
    echo [OK] Junction 创建成功
) else (
    echo [SKIP] AutomationLib 已存在，跳过创建
)



REM 检查并创建 GPCSClientLib 链接
if not exist "GPCSClientLib" (
    mklink /J GPCSClientLib ClientLib >nul 2>&1 || (
        echo [ERROR] 创建 Junction 失败！请确认目标目录 ClientLib 存在
        pause
        exit /b 1
    )
    echo [OK] Junction 创建成功
) else (
    echo [SKIP] GPCSClientLib 已存在，跳过创建
)

REM ===== 切换回脚本所在目录 =====
cd /d "%~dp0" || (
    echo [ERROR] 无法切换回脚本目录！
    pause
    exit /b 1
)

REM ===== 准备目标目录 =====
if not exist "..\SEM_UI\bin\Debug\" (
    echo [INFO] 正在创建目标目录：..\SEM_UI\bin\Debug\
    mkdir "..\SEM_UI\bin\Debug\" >nul 2>&1 || (
        echo [ERROR] 创建SEM_UI\bin\Debug目录失败！请检查路径权限
        pause
        exit /b 1
    )
)

REM ===== 静默复制目录 =====
REM 复制 AppData（如果目标不存在）
if exist "AppData\" (
    if not exist "..\SEM_UI\bin\Debug\AppData\" (
        xcopy "AppData" "..\SEM_UI\bin\Debug\AppData\" /E /H /C /I /Y /Q >nul || (
            echo [ERROR] AppData 复制失败！
            pause
            exit /b 1
        )
        echo [OK] AppData 复制完成
    ) else (
        echo [SKIP] AppData 目标已存在，跳过复制
    )
) else (
    echo [ERROR] 源目录 AppData 不存在！
    pause
    exit /b 1
)

cd /d "%~dp0../SEM_UI" || (
    echo [ERROR] 不存在SEM_UI！！！
    pause
    exit /b 1
)

REM 复制 SVGFolder（如果目标不存在）
if exist "SVGFolder\" (
    if not exist "bin\Debug\SVGFolder\" (
        echo [INFO] 正在复制 SVGFolder...
        xcopy "SVGFolder" "bin\Debug\SVGFolder\" /E /H /C /I /Y /Q >nul || (
            echo [ERROR] SVGFolder 复制失败！
            pause
            exit /b 1
        )
        echo [OK] SVGFolder 复制完成
    ) else (
        echo [SKIP] SVGFolder 目标已存在，跳过复制
    )
) else (
    echo [ERROR] 源目录 SVGFolder 不存在！
    pause
    exit /b 1
)

cd /d "%~dp0..\AppData" || (
    echo [ERROR] 回到上级目录失败
    pause
    exit /b 1
)

REM 确保目标目录存在
if not exist "..\CSServer\bin\Debug\" (
    mkdir "..\CSServer\bin\Debug\" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] 创建CSServer\bin\Debug目录失败！请检查路径权限
        pause
        exit /b 1
    )
)

REM ===== 复制 database 目录中的文件（强制替换） =====
if exist "database\*.*" (
    REM 直接复制文件到Debug目录
    xcopy "database\*.*" "..\CSServer\bin\Debug\" /H /Y /Q >nul || (
        echo [ERROR] database 文件复制失败！
        pause
        exit /b 1
    )
    echo [OK] database 文件复制完成
) else (
    echo [WARN] 源目录 AppData\database 中没有文件，跳过复制
)

REM ===== 复制 diss6 目录中的文件（强制替换） =====
if exist "diss6\*.*" (
    REM 直接复制文件到Debug目录
    xcopy "diss6\*.*" "..\CSServer\bin\Debug\" /H /Y /Q >nul || (
        echo [ERROR] diss6 文件复制失败！
        pause
        exit /b 1
    )
    echo [OK] diss6 文件复制完成
) else (
    echo [WARN] 源目录 AppData\diss6 中没有文件，跳过复制
)


cd /d "%~dp0.." || (
    echo [ERROR] 目录切换失败！！！
    pause
    exit /b 1
)

git submodule foreach --recursive "git checkout master && git pull origin master"
echo [OK] 所有子模块切换到master分支
echo =======================================================

echo [SUCCESS] 所有操作已完成！
endlocal
pause
