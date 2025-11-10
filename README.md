# CNC 数字孪生

## 1. 项目概述

本项目旨在构建一个基于 Web 的五轴 CNC 机床数字孪生系统。



---技术架构
后端: Flask + Flask-SocketIO
FMU处理: FMPy库
前端: Bootstrap 5 + Socket.IO客户端
通信: WebSocket实时双向通信

## 2. 项目结构

```
webserver-cnctwin/
│
├── Unity_Scripts/              # (重要) Unity 项目的 C# 核心脚本
│   ├── CNCMachineController.cs # 1. 机床总控制器(大脑): 负责接收坐标、控制运动、处理碰撞报告
│   └── MachinePartCollider.cs  # 2. 碰撞感知器(神经): 挂载在每个零件上，负责检测物理碰撞并上报
│
├── app.py                      # Flask 后端主程序，负责启动 Web 服务和 WebSocket 服务
├── cnc_simulation.db           # SQLite 数据库文件，存储模拟的 G 代码和机床坐标
├── database_schema.sql         # 数据库初始化脚本
├── requirements.txt            # Python 依赖包列表
├── static/                     # 存放 Unity WebGL 构建出的前端文件
│   ├── Build/
│   ├── TemplateData/
│   └── index.html
│
└── templates/
    └── index.html              # Flask 渲染的 HTML 模板，用于加载 Unity 应用
```

### 关键脚本说明

1.  **`app.py` (后端)**
    *   使用 Flask-SocketIO 创建 Web 服务器和 WebSocket 服务器。
    *   从 `cnc_simulation.db` 数据库中读取预存的机床轴坐标数据。
    *   通过 WebSocket (`/ws`) 以固定的时间间隔，持续向所有连接的前端客户端广播 (broadcast) 坐标数据。

2.  **`CNCMachineController.cs` (Unity 前端)**（待修改完善）
    *    场景总控制器，是整个 Unity 应用的核心。
    *   **功能**:
        *   与后端建立 WebSocket 连接。
        *   接收后端发来的坐标数据，并将其转化为机床各轴（X, Y, Z, A, C）的目标位置和旋转。
        *   通过 `Update()` 函数平滑地驱动场景中对应的 3D 模型运动到目标位置。
        *   接收来自 `MachinePartCollider.cs` 的碰撞报告。一旦收到报告，立即停止所有机床运动 (`isHaltedByCollision = true`)，并将碰撞的两个部件高亮为红色。
        *   内置了键盘测试功能 (`enableDebugMovement`)，允许在不连接后端的情况下，使用键盘上下箭头测试 Z 轴的运动和碰撞逻辑。

---

## 3. 环境搭建与启动流程

请按照以下步骤操作，以确保项目能成功运行。

### 3.1 后端启动

1.  **安装 Python**: 确保本地已安装 Python 3.8 或更高版本。
2.  **创建虚拟环境 (推荐)**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # Windows
    # source venv/bin/activate  # macOS/Linux
    ```
3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **初始化数据库**:
    *   如果项目根目录下没有 `cnc_simulation.db` 文件，请执行以下命令来创建并填充数据：
    ```bash
    sqlite3 cnc_simulation.db < database_schema.sql
    ```
5.  **启动后端服务**:
    ```bash
    python app.py
    ```
    启动成功后，您会看到类似 `WebSocket transport listening on http://127.0.0.1:5000` 的输出。

### 3.2 Unity 前端配置

1.  **打开 Unity 项目**: 使用 Unity Hub 打开包含 `Unity_Scripts` 文件夹的 Unity 项目。
2.  **关联模型与脚本**:
    *   在场景中创建一个空 GameObject 作为总控制器，并将 `CNCMachineController.cs` 挂载上去。
    *   将场景中代表机床各轴的 3D 模型，分别拖拽到总控制器脚本对应的 `Transform` 字段上（例如 `Table X`, `Spindle Z` 等）。
    *   为**每一个**需要参与碰撞检测的机床部件（包括工件）添加 `MachinePartCollider.cs` 脚本。
    *   在**每一个** `MachinePartCollider.cs` 脚本的 `Controller` 字段中，拖入总控制器对象。
3.  **构建项目**:
    *   打开 `File -> Build Settings`。
    *   确保平台选择 `WebGL`。
    *   点击 `Build`，将项目构建到项目根目录下的 `static` 文件夹中。**请确保输出路径正确，否则后端无法提供前端页面。**

### 3.3 访问与测试

1.  确保后端服务正在运行。
2.  打开浏览器，访问 `http://127.0.0.1:5000`。
3.  您应该能看到 Unity 的加载界面，加载完成后，机床模型会根据后端发送的数据开始运动。
    ws://192.168.0.112:8080
---




1 整合切削。
2 整合碰撞。
3 限位（和机床绑定）。
4 变色功能。左侧层级，点击变色。刀具 夹具 机床不同的颜色。
5 卧式机床or立式机床（方向对吗？）
