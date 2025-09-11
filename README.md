# 五轴数控机床FMU仿真器

这是一个基于Flask和FMPy的五轴数控机床仿真服务器，支持通过WebSocket进行实时通信。

## 功能特性

- **FMU文件加载**: 支持上传和解析FMU (Functional Mock-up Unit) 文件
- **变量识别**: 自动识别FMU文件中的输入和输出变量
- **实时仿真**: 五轴（X、Y、Z、A、C）位置实时更新和显示
- **WebSocket通信**: 实时双向通信，支持发送控制指令和接收状态数据
- **Web界面**: 现代化的响应式Web界面，支持：
  - FMU文件上传和管理
  - 变量信息查看
  - 轴位置实时监控
  - 手动控制面板
  - 仿真控制
  - 系统日志显示

## 系统要求

- Python 3.7+
- 支持FMU 2.0标准的模型文件

## 安装步骤

1. **克隆或下载项目**
   ```bash
   git clone <repository-url>
   cd webserver-cnctwin
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行服务器**
   ```bash
   python app.py
   ```

4. **访问Web界面**
   打开浏览器访问: http://localhost:5000

## 使用说明

### 1. 上传FMU文件
- 在左侧面板点击"选择FMU文件"
- 选择您的.fmu文件
- 点击"上传并加载"按钮
- 系统会自动解析FMU文件并显示变量信息

### 2. 启动仿真
- 确保FMU文件已成功加载
- 点击右侧面板的"启动仿真"按钮
- 观察轴位置的实时变化

### 3. 手动控制
- 在中间面板选择要控制的轴（X、Y、Z、A、C）
- 输入目标位置
- 点击"移动"按钮发送控制指令
- 使用速度滑块调整仿真速度

### 4. 监控状态
- 连接状态显示在顶部导航栏
- 轴位置实时显示在中间面板
- 系统日志显示在右下角

## API接口

### WebSocket事件

#### 客户端发送事件
- `start_simulation`: 启动仿真
- `stop_simulation`: 停止仿真
- `send_command`: 发送控制指令

#### 服务器发送事件
- `variable_info`: 变量信息
- `axis_positions`: 轴位置数据
- `simulation_status`: 仿真状态
- `command_response`: 指令响应

### HTTP接口
- `POST /upload_fmu`: 上传FMU文件

## 控制指令格式

### 轴移动指令
```json
{
  "type": "move_axis",
  "axis": "X",
  "position": 10.5
}
```

### 速度设置指令
```json
{
  "type": "set_speed",
  "speed": 2.0
}
```

## 项目结构

```
webserver-cnctwin/
├── app.py                 # 主服务器文件
├── requirements.txt       # Python依赖
├── README.md             # 说明文档
├── templates/
│   └── index.html        # Web界面模板
├── static/
│   └── app.js           # 前端JavaScript
└── uploads/             # FMU文件上传目录
```

## 技术架构

- **后端**: Flask + Flask-SocketIO
- **FMU处理**: FMPy库
- **前端**: Bootstrap 5 + Socket.IO客户端
- **通信**: WebSocket实时双向通信

## 注意事项

1. 确保您的FMU文件符合FMU 2.0标准
2. 大型FMU文件可能需要较长的加载时间
3. 仿真精度取决于FMU模型的质量
4. 建议在局域网环境中使用以获得最佳性能

## 故障排除

### 常见问题

1. **FMU文件加载失败**
   - 检查文件是否为有效的.fmu格式
   - 确认文件未损坏
   - 查看系统日志获取详细错误信息

2. **WebSocket连接失败**
   - 检查防火墙设置
   - 确认端口5000未被占用
   - 尝试刷新页面重新连接

3. **仿真不响应**
   - 确保已成功加载FMU文件
   - 检查FMU模型是否支持实时仿真
   - 查看服务器控制台输出

## 开发扩展

如需扩展功能，可以：

1. 修改`CNCMachineSimulator`类添加新的仿真逻辑
2. 在Web界面添加新的控制面板
3. 扩展WebSocket事件处理
4. 集成更多的FMU功能

## 许可证

本项目采用MIT许可证。

## 联系方式

如有问题或建议，请通过GitHub Issues联系。