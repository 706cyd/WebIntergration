# Unity WebGL与FMU仿真集成指南

## 项目概述

本指南介绍如何将Unity五轴数控机床3D模型集成到基于Flask和FMPy的仿真系统中，实现实时的3D可视化效果。

## 集成架构

```
FMU仿真服务器 (Python/Flask)
    ↓ WebSocket通信
Web界面 (HTML/JavaScript)
    ↓ Unity WebGL
Unity 3D模型 (C#脚本)
```

## Unity项目设置

### 1. 项目配置

#### Build Settings
- **Platform**: WebGL
- **Scenes**: 确保包含机床场景
- **Player Settings**:
  - Company Name: CNCSimulator
  - Product Name: 五轴数控机床仿真器
  - WebGL Template: Default
  - Color Space: Linear

#### WebGL设置
- **Compression Format**: Gzip
- **Memory Size**: 512 MB (根据模型复杂度调整)
- **Enable Exceptions**: None
- **Strip Engine Code**: 启用 (减小构建大小)

### 2. 场景层次结构

建议的Unity场景层次结构：

```
CNCMachine (空GameObject)
├── TableAssembly (X/Y轴组件)
│   ├── TableX (X轴移动平台)
│   │   └── TableY (Y轴移动平台)
│   │       └── TableC (C轴转台)
│   │           └── Workpiece (工件)
│   └── TableBase (工作台底座)
├── SpindleAssembly (主轴组件)
│   ├── SpindleZ (Z轴主轴)
│   │   └── HeadA (A轴摆头)
│   │       └── Tool (刀具)
│   │           └── ToolTip (刀尖位置)
│   └── SpindleBase (主轴底座)
├── MachineFrame (机床框架)
├── UI (用户界面)
│   └── Canvas (UI画布)
└── Controllers (控制器)
    ├── CNCMachineController (主控制器)
    └── MachineVisualizer (可视化控制器)
```

### 3. 脚本配置

#### CNCMachineController配置
```csharp
[Header("机床组件引用")]
public Transform tableX;      // 拖拽TableX GameObject
public Transform tableY;      // 拖拽TableY GameObject  
public Transform spindleZ;    // 拖拽SpindleZ GameObject
public Transform headA;       // 拖拽HeadA GameObject
public Transform tableC;      // 拖拽TableC GameObject
public Transform tool;        // 拖拽Tool GameObject

[Header("运动参数")]
public float positionScale = 0.01f;  // 位置缩放比例 (mm to Unity units)
public float smoothTime = 0.1f;      // 平滑时间
public bool enableSmoothing = true;  // 启用平滑运动
```

#### MachineVisualizer配置
```csharp
[Header("UI组件")]
public Canvas mainCanvas;           // 拖拽主UI Canvas
public TextMeshProUGUI positionText; // 位置显示文本
public TextMeshProUGUI velocityText; // 速度显示文本
public Slider xAxisSlider;          // X轴控制滑块
// ... 其他UI组件
```

### 4. 材质和效果

#### 建议的材质设置
- **机床框架**: 金属材质，使用Standard Shader
- **工作台**: 灰色金属材质，带轻微反射
- **主轴**: 深灰色金属，高光度较高
- **刀具**: 银色金属，高反射
- **刀具路径**: LineRenderer，明亮颜色(如绿色或蓝色)

#### 光照设置
- **Main Light**: Directional Light，模拟车间照明
- **Fill Light**: 添加额外光源消除阴影过深
- **Environment**: 简单的Skybox或纯色背景

## WebGL构建和部署

### 1. 构建步骤

1. **设置构建目录**
   ```
   项目根目录/static/unity/
   ```

2. **Unity构建**
   - File → Build Settings
   - 选择WebGL平台
   - Build到 `static/unity/Build/` 目录
   - 确保生成以下文件：
     - webgl.data
     - webgl.framework.js
     - webgl.loader.js
     - webgl.wasm

3. **验证文件结构**
   ```
   static/
   ├── unity/
   │   └── Build/
   │       ├── webgl.data
   │       ├── webgl.framework.js
   │       ├── webgl.loader.js
   │       └── webgl.wasm
   ├── unity_integration.js
   └── app.js
   ```

### 2. 文件大小优化

#### Unity构建优化
- **Stripping Level**: High
- **Managed Stripping Level**: High  
- **Script Call Optimization**: IL2CPP
- **Api Compatibility Level**: .NET Standard 2.1

#### 资源优化
- 纹理压缩: ETC1/ETC2 或 DXT
- 网格优化: 减少面数，合并网格
- 音频压缩: Vorbis格式

## 通信协议

### 1. 服务器到Unity数据格式

```json
{
  "timestamp": 1234567890.123,
  "transforms": {
    "table_x": {
      "position": {"x": 10.5, "y": 0, "z": 0},
      "rotation": {"x": 0, "y": 0, "z": 0},
      "scale": {"x": 1, "y": 1, "z": 1}
    },
    "table_y": {
      "position": {"x": 0, "y": 0, "z": -5.2},
      "rotation": {"x": 0, "y": 0, "z": 0},
      "scale": {"x": 1, "y": 1, "z": 1}
    },
    "spindle_z": {
      "position": {"x": 0, "y": 8.7, "z": 0},
      "rotation": {"x": 0, "y": 0, "z": 0},
      "scale": {"x": 1, "y": 1, "z": 1}
    },
    "head_a": {
      "position": {"x": 0, "y": 0, "z": 0},
      "rotation": {"x": 15.3, "y": 0, "z": 0},
      "scale": {"x": 1, "y": 1, "z": 1}
    },
    "table_c": {
      "position": {"x": 0, "y": 0, "z": 0},
      "rotation": {"x": 0, "y": 45.7, "z": 0},
      "scale": {"x": 1, "y": 1, "z": 1}
    }
  },
  "velocities": {
    "X": 100.5,
    "Y": 85.2,
    "Z": 50.0,
    "A": 30.8,
    "C": 25.4
  },
  "machine_state": {
    "is_running": true,
    "simulation_time": 45.67,
    "step_size": 0.1,
    "alarm": false,
    "ready": true,
    "tool_info": {
      "tool_number": 1,
      "spindle_speed": 1000,
      "feed_rate": 500
    }
  }
}
```

### 2. Unity到服务器指令格式

```json
{
  "type": "move_axis",
  "axis": "X",
  "position": 25.6
}

{
  "type": "set_speed", 
  "speed": 2.5
}
```

## 使用说明

### 1. 开发环境设置

1. **启动服务器**
   ```bash
   python run_server.py
   ```

2. **访问Web界面**
   ```
   http://localhost:5000
   ```

3. **Unity开发**
   - 在Unity Editor中测试脚本逻辑
   - 使用模拟数据验证功能
   - 构建为WebGL进行集成测试

### 2. 生产环境部署

1. **服务器配置**
   - 确保WebSocket端口开放
   - 配置适当的CORS设置
   - 优化文件服务性能

2. **Web服务器设置**
   - 配置静态文件缓存
   - 启用Gzip压缩
   - 设置适当的MIME类型

### 3. 用户操作

1. **加载3D模型**
   - 页面自动加载Unity WebGL
   - 显示加载进度

2. **控制机床**
   - 使用Web界面控制面板
   - 或直接在Unity场景中交互
   - 观察实时动画效果

3. **监控状态**
   - 查看轴位置和速度
   - 监控机床状态
   - 观察刀具路径

## 故障排除

### 常见问题

1. **Unity WebGL不加载**
   - 检查构建文件是否完整
   - 验证文件路径正确性
   - 检查浏览器控制台错误

2. **WebSocket连接失败**
   - 确认服务器正常运行
   - 检查网络连接
   - 验证端口配置

3. **动画不流畅**
   - 调整smoothTime参数
   - 检查帧率设置
   - 优化模型复杂度

4. **数据同步问题**
   - 验证JSON数据格式
   - 检查时间戳同步
   - 调试WebSocket消息

### 性能优化建议

1. **Unity优化**
   - 减少Draw Calls
   - 优化材质数量
   - 使用LOD系统
   - 启用GPU Instancing

2. **网络优化**
   - 减少数据传输频率
   - 压缩JSON数据
   - 使用二进制协议

3. **Web优化**
   - 启用资源缓存
   - 优化加载策略
   - 减少DOM操作

## 扩展功能

### 高级特性

1. **交互控制**
   - 鼠标拖拽控制
   - 键盘快捷键
   - 触摸手势支持

2. **可视化增强**
   - 材质变化反馈
   - 粒子效果
   - 声音反馈

3. **数据分析**
   - 性能图表
   - 历史数据回放
   - 统计信息显示

4. **多视角支持**
   - 自由相机
   - 预设视角
   - VR/AR支持

这个集成方案提供了完整的Unity WebGL与FMU仿真系统的连接，实现了真正的实时3D可视化效果。
