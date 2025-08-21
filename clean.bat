@echo off
setlocal enabledelayedexpansion

:: 获取脚本所在目录
set "scriptDir=%~dp0"
cd /d "%scriptDir%"

:: 要删除的目录列表
set "dirsToDelete=.vs obj bin"

:: 遍历所有目录并删除
for %%d in (%dirsToDelete%) do (
    echo 正在删除所有 "%%d" 目录...
    for /f "delims=" %%i in ('dir /s /b /ad "%%d" 2^>nul') do (
        rd /s /q "%%i" >nul 2>&1
        if !errorlevel! equ 0 (
            echo 已删除: %%i
        ) else (
            echo 删除失败: %%i
        )
    )
)

echo 清理完成！
pause