# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

SEM (Scanning Electron Microscope) 控制软件系统，采用 C# / .NET Framework 开发，包含两个主要解决方案：

- **Server.sln** - 后端服务端，负责硬件控制、数据处理和通信
- **Ui.sln** - WPF 前端界面，提供用户交互界面

## 构建命令

```bash
# 使用 MSBuild 构建（需要 Visual Studio）
# 构建 Server
& "D:\Visual Studio\ide\MSBuild\Current\Bin\amd64\MSBuild.exe" Server.sln /p:Configuration=Release /p:OutputPath=E:\work\sem\build

# 构建 UI
& "D:\Visual Studio\ide\MSBuild\Current\Bin\amd64\MSBuild.exe" Ui.sln /p:Configuration=Release /p:OutputPath=E:\work\sem\build

# 清理构建产物（删除 .vs, obj, bin 目录）
clean.bat
```

## 初始化

```bash
# 克隆仓库（包含子模块）
git clone --recurse-submodules https://github.com/love-yuri/sem.git

# 运行初始化脚本
AppData/init.bat
```

初始化脚本会：
1. 创建符号链接（Junction）：`PicoammeterCtlrLib` -> `SEM_UI_PicoammeterCtrlLib`，`AutomationLib` -> `AutoFocusLib`，`GPCSClientLib` -> `ClientLib`
2. 复制配置文件到 bin 目录
3. 切换所有子模块到 master 分支

## 架构

### Server 端架构

```
CSServer (WinForms 应用程序入口)
  └── AppContext (系统托盘应用上下文)
       └── GPCSServer.CSServer (单例)
            ├── ComponentManager (组件管理器)
            │   ├── CommunicationHandler (NetMQ REQ/REP 通信)
            │   └── DeviceManager (设备管理)
            ├── DeviceFactory (设备工厂，初始化硬件设备)
            └── JobRunner (任务调度器)
```

### Client 端架构

```
SEM_UI (WPF 应用程序)
  └── MainWindow (主窗口)
       ├── Viewer 模块 (图像显示)
       ├── MenuBar 模块 (菜单栏)
       ├── ToolBar 模块 (工具栏)
       ├── CtrlPanel 模块 (控制面板)
       ├── KnobPanel 模块 (旋钮面板)
       ├── DataBar 模块 (数据栏)
       ├── AnnotationBar 模块 (标注栏)
       ├── CCDViewer 模块 (CCD 相机视图)
       ├── StateBar 模块 (状态栏)
       └── ShortCutBar 模块 (快捷栏)
```

### 通信机制

- 使用 **NetMQ** (ZeroMQ 的 .NET 实现) 进行进程间通信
- **REQ/REP 模式**：Client 发送命令到 Server（端口 12345）
- **PUB/SUB 模式**：Server 发布状态更新，Client 订阅（端口 23456）
- 命令格式：`Command(deviceId, cmdName)` + 参数字典

### 关键模块

| 模块 | 职责 |
|------|------|
| **GPCSCommon** | 共享类型定义（Command, ParamValue, BlockingQueue） |
| **GPCSClientLib** | 客户端通信库，封装 NetMQ 请求/订阅 |
| **GPCSServerLib** | 服务端通信库，处理命令分发 |
| **GPCSConfig** | 系统配置管理（SysConfigInfo） |
| **Database** | 数据库访问层 |
| **ImageLib** | 图像处理库 |
| **ScanGenLib** | 扫描生成器库 |
| **AutoFocusLib** | 自动对焦算法 |
| **AutoBCLib** | 自动亮度/对比度调节 |
| **DebugLogger** | 调试日志 |

### 子模块结构

项目使用 Git 子模块管理，分为两类：

**Server 子模块**（SEM_Server 仓库）：
- GPCSCommon, DebugLogger, ClientLib, ImageLib, UDPClient, AutoBCLib, AutoFocusLib, CSServer, Database, GPCSConfig, ServerLib, ScanGenLib

**UI 子模块**（SEM_UI 仓库）：
- SEM_UI, SEM_UI_CtrlEx, SEM_UI_SystemMessageWindow, SEM_UI_MenuBar, SEM_UI_JoyStick, SEM_UI_DataBar, SEM_UI_SettingWindows, SEM_UI_StateBar, SEM_UI_ShortCutBar, SEM_UI_AnnotationBar, SEM_UI_UserPreConfig, SEM_UI_ToolBar, SEM_UI_CtrlPanel, SEM_UI_Recipe, SEM_UI_Viewer, SEM_UI_CCDViewer, KnobPanelLib, SEM_UI_KnobPanel, ImageGraphics, ImageDocument, SEM_UI_Resolution, SEM_UI_Plasma, SEM_UI_PicoammeterCtrlLib, SEM_UI_SerialPort, SEM_PolygonCtrlLib

## 配置文件

- **AppData/database/Config.ini** - 系统参数配置（XML 格式），包含 CCD 参数、导航参数、分辨率参数等
- **AppData/database/** - 数据库文件目录
- **AppData/diss6/** - diss6 进程相关文件

## 开发注意事项

1. **符号链接依赖**：某些项目目录名与实际目录名不同（如 `GPCSClientLib` -> `ClientLib`），需要运行 `AppData/init.bat` 创建符号链接
2. **子模块管理**：所有子模块使用 `ignore = all` 配置，修改子模块后需要在各自仓库中提交
3. **分支策略**：子模块统一使用 `master` 分支
4. **通信端口**：默认 REQ/REP 端口 12345，PUB/SUB 端口 23456（可在 Config.ini 中配置）
