## 五轴数控机床仿真系统交接说明（Handoff）

本文档面向后续开发者，概述项目能力、模块划分、主要流程、接口与扩展点，便于快速上手与持续迭代。

### 一、项目能力（Feature Overview）
- 仿真引擎：加载 FMU，执行真实 Co-Simulation；若FMU不支持则自动切换“直通模式（输出=输入）”。
- 实时通信：使用 WebSocket（Socket.IO）推送轴位置与 Unity 专用 3D 变换数据。
- 外部数据接入：支持浏览器桥接或原生 WebSocket 将第三方设备位姿实时写入仿真通道。
- 数据持久化：将会话、实时位置、状态、指令等写入 SQLite，提供查询、统计与导出。
- 可视化：Unity WebGL 实时渲染五轴机床，浏览器端 UI 控制仿真。

### 二、目录与核心模块（Where things live）
- 后端
  - `app.py`：Flask 应用入口与主要业务逻辑、Socket.IO 事件、REST API、外部 WebSocket 路由。
    - 类 `CNCMachineSimulator`：仿真核心（FMU 加载/直通、仿真线程、数据广播与命令处理）。
    - Socket.IO 事件：`connect`、`start_simulation`、`stop_simulation`、`send_command`、`external_ws_message`、`external_ws_status`。
    - REST API：会话、当前状态、历史导出等。
    - 原生 WebSocket：`/external/positions` 接收 JSON 位姿。
  - `database_manager.py`：SQLite 连接池、表结构初始化、数据读写与统计导出。
  - `database_schema.sql`：完整数据库架构（会话、实时数据、指令、统计、错误日志等）。
  - `config.py`：环境化配置（数据库、WebSocket、仿真参数、Unity 集成等）。
  - `run_server.py`：启动器（依赖检查、目录创建、示例提示，然后 run Socket.IO）。

- 前端
  - 模板与页面：`templates/index.html`（Bootstrap UI，Unity 容器与控制面板）。
  - 客户端逻辑：`static/app.js`（Socket.IO 客户端、UI 联动、数据库概览、外部WS桥接、控制指令）。
  - Unity 集成：`static/unity_integration.js`（延迟加载 Unity、桥接 Socket.IO 到 Unity、全屏/内置UI 切换）。
  - Unity 插件：`Unity_Scripts/WebGLSocketPlugin.jslib`（WebGL 下与 Socket.IO 交互的 JSlib）。

### 三、运行流程（How it works）
1) 启动
   - 通过 `python run_server.py` 或直接运行 `app.py` 末尾的 `socketio.run(...)` 启动服务。
   - 首次启动会确保 `templates/`、`static/`、`uploads/` 存在。

2) 加载 FMU 并仿真
   - 前端 `static/app.js` 发送表单至 `POST /upload_fmu`，后端 `app.py:upload_fmu()` 调用 `CNCMachineSimulator.load_fmu()`。
   - 若 FMU 可实例化，进入“真实 FMU 模式”；否则回退“直通模式”。
   - 前端点击“启动仿真”触发 `socket.emit('start_simulation')`，服务端 `handle_start_simulation()` 调 `start_simulation()`：
     - 创建会话，启动线程 `_simulation_loop()`，周期性：
       - 设置 FMU 输入（或直通/演示计算）→ 计算位置与速度。
       - 写入数据库（会话在运行时写实时表）。
       - 通过 Socket.IO 广播：
         - `axis_positions`：X/Y/Z/A/C 位置、时间戳。
         - `unity_transform_data`：Unity 友好的节点变换、速度、状态。

3) 前端渲染与交互
   - `templates/index.html` 中的 Unity 容器由 `static/unity_integration.js` 延迟加载 Unity WebGL（`/static/unity/Build/Build.*`）。
   - `static/app.js` 订阅 `axis_positions`、`simulation_status` 等以更新 UI；`unity_integration.js` 将 `unity_transform_data` 发送给 Unity 对象 `CNCMachineController`。
   - 页面顶部按钮：全屏/Unity UI 切换；新增比例按钮 `setUnityAspect('square'|'16-9')` 切换 `#unityContainer` 的 `aspect-*` 类。

4) 外部数据接入（两种方式）
   - 浏览器桥接：`static/app.js` 创建 `WebSocket(url)`，将 `message` 转发为 `socket.emit('external_ws_message')` 到后端；服务端解析后 `apply_external_positions()` 更新内部姿态并广播。
   - 原生 WebSocket：设备直接连 `ws://server:5000/external/positions`，传输 JSON；服务端 `@sock.route` 处理并广播。

### 四、关键代码节点（What to read/edit first）
- 仿真器核心：`app.py` → 类 `CNCMachineSimulator`
  - `load_fmu()` / `_create_fmu_instance()` / `_set_fmu_inputs()` / `_get_fmu_outputs()`
  - `_simulation_loop()`：周期推进、数据库写入与 Socket.IO 广播。
  - `_calculate_unity_transforms()`：将轴位姿映射为 Unity 节点 `table_x`/`table_y`/`spindle_z`/`head_a`/`table_c` 的 position/rotation。
  - `send_command()`：处理 `move_axis` 与 `set_speed`（未识别类型将返回失败）。
  - `apply_external_positions()`：解析扁平或嵌套 JSON，兼容大小写与 B→C 轴映射，并即时广播。

- WebSocket 事件：`app.py`
  - `@socketio.on('start_simulation')`、`@socketio.on('stop_simulation')`、`@socketio.on('send_command')`
  - 外部桥接：`@socketio.on('external_ws_message')`、`@socketio.on('external_ws_status')`
  - 原生 WS：`@sock.route('/external/positions')`

- 数据层：`database_manager.py` / `database_schema.sql`
  - 会话表、实时位置表、状态表、指令表等；`get_session_statistics()`、`get_latest_positions()`、导出 `export_session_data()`。

- 前端交互：
  - `static/app.js`：`CNCSimulatorClient` 负责 Socket.IO 连接、UI 更新、按钮事件、外部 WS 桥接、数据库概览（右侧面板）。
  - `static/unity_integration.js`：加载 Unity、桥接 Socket.IO→Unity、全屏与内置 UI 切换。
  - `templates/index.html`：Bootstrap 布局、`#unityContainer` 居中与 `aspect-ratio` 控制（`aspect-square` / `aspect-16-9`）。

### 五、接口说明（APIs）
- WebSocket（Socket.IO）事件（客户端→服务端）
  - `start_simulation` / `stop_simulation`
  - `send_command`：示例 `{ "type":"move_axis", "axis":"X", "position":10.5 }` 或 `{ "type":"set_speed", "speed":2.0 }`
  - `external_ws_message`：浏览器桥接外部原生 WS 的消息（文本或已解析 JSON）。
  - `external_ws_status`：`{ connected:true|false }` 切换 `external_mode`。

- WebSocket（Socket.IO）事件（服务端→客户端）
  - `variable_info`、`simulation_status`、`axis_positions`、`unity_transform_data`、`command_response`。

- REST API（HTTP）
  - `POST /upload_fmu`：上传 `.fmu`。
  - `GET /api/sessions`、`GET /api/sessions/<id>/statistics`、`GET /api/sessions/<id>/positions`、`GET /api/sessions/<id>/export?format=json`。
  - `GET /api/current/positions`：当前（缓存/实时）数据。
  - `POST /api/database/cleanup`：按 `retention_days` 清理历史。

- 原生 WebSocket（外部设备）
  - `ws://<host>:5000/external/positions`，载荷示例：
    - 扁平：`{"X":1.2,"Y":0.3,"Z":-2.1,"A":10.5,"C":-30}`
    - 嵌套：`{"positions":{"x":{"pos_cmd":1.2,"vel_cmd":0.1},"y":{...}}}`

### 六、配置（Configuration）
- 参考 `config.py`：
  - `DATABASE_CONFIG.path` 设置 SQLite 文件路径；`retention_days` 数据保留；`pool_size` 连接池大小。
  - `WEBSOCKET_CONFIG.cors_allowed_origins`、`ping_*`；
  - `SIMULATION_CONFIG.default_step_size`、`position_scale`；
  - `UNITY_CONFIG.unity_build_path`（默认 `static/unity/Build`）。

### 七、开发与调试（Dev Notes）
- 启动：`python run_server.py`
- 前端静态资源：`templates/index.html`、`static/app.js`、`static/unity_integration.js`
- Unity 构建：放置于 `static/unity/Build/Build.*`，页面已按此路径加载。
- 样式与布局：`index.html` 中的内联 CSS 控制 Unity 画布的居中与比例切换。

### 八、扩展点（Extension Points）
- 仿真指令：在 `app.py:send_command()` 增加新指令类型（如 `home_axis`、`jog`、`load_program`），并在前端 `static/app.js` 添加对应按钮与 payload。
- 数据模型：按需扩展 `database_schema.sql` 与 `database_manager.py` 的写入/查询方法。
- Unity 通信：在 `unity_integration.js` 增加新消息路由，或在 `WebGLSocketPlugin.jslib` 对接 Unity C# 脚本的新回调。
- 外部数据：在 `apply_external_positions()` 添加更多字段兼容或坐标系转换；可加入滤波与限幅。
- 性能：调整 `config.py` 中的步长、缓存、连接池与监控阈值；必要时接入 Redis 或 PostgreSQL。

### 九、已知边界与建议
- FMU 实例化失败会自动转直通模式，若需严格校验可在 `load_fmu()` 强制失败时返回错误。
- `send_command()` 当前仅处理 `move_axis` 和 `set_speed`，其他类型需自行扩展。
- 外部模式开启时（`external_mode=true`）会屏蔽本地启动仿真与控制，避免数据竞争。

### 十、快速定位（文件与函数）
- 后端入口与仿真：`app.py` → `CNCMachineSimulator._simulation_loop()`、`_calculate_unity_transforms()`、`send_command()`、`apply_external_positions()`。
- 数据层：`database_manager.py` → `save_axis_positions()`、`save_machine_status()`、`get_session_statistics()`。
- 前端入口：`static/app.js` → `CNCSimulatorClient.connectWebSocket()`、`updateAxisPositions()`、`connectExternalWs()`。
- Unity 集成：`static/unity_integration.js` → `loadUnity()`、`setupUnityWebSocketBridge()`；`Unity_Scripts/WebGLSocketPlugin.jslib`。

—— 以上即为交接所需的核心信息。建议从 `app.py` 与 `static/app.js` 入手，熟悉事件与数据格式后，再进入 Unity 侧联调。


