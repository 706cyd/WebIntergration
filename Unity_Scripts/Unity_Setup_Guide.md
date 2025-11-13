# Unity五轴数控机床脚本挂载指南

## 🎯 脚本挂载步骤详解

### 1. Unity场景层次结构设置

首先，您需要按照以下建议的层次结构组织您的五轴机床模型：

```
CNCMachine (空GameObject - 根节点)
├── Controllers (空GameObject - 脚本挂载点)
│   ├── CNCMachineController (挂载 CNCMachineController.cs)
│   └── MachineVisualizer (挂载 MachineVisualizer.cs)
│
├── MachineStructure (机床结构)
│   ├── TableAssembly (工作台组件)
│   │   ├── TableBase (工作台底座 - 静态)
│   │   ├── TableX (X轴移动平台)
│   │   │   └── TableY (Y轴移动平台)
│   │   │       └── TableC (C轴转台)
│   │   │           └── Workpiece (工件)
│   │   └── XAxisGuide (X轴导轨)
│   │
│   ├── SpindleAssembly (主轴组件)
│   │   ├── SpindleBase (主轴底座 - 静态)
│   │   ├── SpindleZ (Z轴主轴)
│   │   │   └── HeadA (A轴摆头)
│   │   │       └── SpindleMotor (主轴电机)
│   │   │           └── Tool (刀具)
│   │   │               └── ToolTip (刀尖位置标记)
│   │   └── ZAxisGuide (Z轴导轨)
│   │
│   └── MachineFrame (机床框架 - 静态)
│       ├── Columns (立柱)
│       ├── Base (底座)
│       └── Guards (防护罩)
│
└── UI (用户界面)
    └── Canvas (UI画布)
        ├── ControlPanel (控制面板)
        ├── StatusDisplay (状态显示)
        └── DebugInfo (调试信息)
```

### 2. CNCMachineController.cs 挂载配置

#### 步骤A: 创建控制器GameObject
1. 在CNCMachine下创建空GameObject，命名为"CNCMachineController"
2. 将`CNCMachineController.cs`脚本拖拽到该GameObject上

#### 步骤B: 配置脚本参数
在Inspector面板中配置以下参数：

```csharp
[Header("机床组件引用")]
public Transform tableX;      // 拖拽 TableX GameObject
public Transform tableY;      // 拖拽 TableY GameObject  
public Transform spindleZ;    // 拖拽 SpindleZ GameObject
public Transform headA;       // 拖拽 HeadA GameObject
public Transform tableC;      // 拖拽 TableC GameObject
public Transform tool;        // 拖拽 Tool GameObject

[Header("运动参数")]
public float positionScale = 0.01f;    // 位置缩放 (FMU单位mm -> Unity单位)
public float smoothTime = 0.1f;        // 平滑时间
public bool enableSmoothing = true;    // 启用平滑运动
```

**重要提示**: 
- `positionScale = 0.01f` 表示FMU的1mm对应Unity的0.01单位
- 根据您的模型实际尺寸调整这个值

#### 步骤C: 拖拽配置示例
![Inspector配置示例]
```
┌─ CNCMachineController (Script) ─┐
│ 机床组件引用                     │
│ ├─ Table X     : [TableX]       │
│ ├─ Table Y     : [TableY]       │  
│ ├─ Spindle Z   : [SpindleZ]     │
│ ├─ Head A      : [HeadA]        │
│ ├─ Table C     : [TableC]       │
│ └─ Tool        : [Tool]         │
│                                 │
│ 运动参数                        │
│ ├─ Position Scale : 0.01        │
│ ├─ Smooth Time   : 0.1          │
│ └─ Enable Smoothing : ✓         │
└─────────────────────────────────┘
```

### 3. MachineVisualizer.cs 挂载配置

#### 步骤A: 创建可视化控制器
1. 在Controllers下创建空GameObject，命名为"MachineVisualizer"
2. 将`MachineVisualizer.cs`脚本拖拽到该GameObject上

#### 步骤B: 配置UI组件
首先需要创建UI组件：

```csharp
[Header("UI组件")]
public Canvas mainCanvas;           // 拖拽主UI Canvas
public TextMeshProUGUI positionText; // 位置显示文本
public TextMeshProUGUI velocityText; // 速度显示文本
public TextMeshProUGUI statusText;   // 状态显示文本
public TextMeshProUGUI timeText;     // 时间显示文本

[Header("轴位置滑块")]
public Slider xAxisSlider;          // X轴控制滑块
public Slider yAxisSlider;          // Y轴控制滑块
public Slider zAxisSlider;          // Z轴控制滑块
public Slider aAxisSlider;          // A轴控制滑块
public Slider cAxisSlider;          // C轴控制滑块

[Header("控制按钮")]
public Button startButton;          // 启动按钮
public Button stopButton;           // 停止按钮
public Button resetButton;          // 重置按钮

[Header("速度控制")]
public Slider speedSlider;          // 速度滑块
public TextMeshProUGUI speedText;   // 速度文本

[Header("可视化效果")]
public LineRenderer toolPath;      // 刀具路径线条
public Transform toolTip;          // 刀尖位置
public Material pathMaterial;      // 路径材质
public int maxPathPoints = 1000;   // 最大路径点数
```

### 4. UI组件创建和配置

#### 步骤A: 创建Canvas
1. 右键Hierarchy → UI → Canvas
2. 设置Canvas为Screen Space - Overlay
3. 将Canvas拖拽到MachineVisualizer脚本的mainCanvas字段

#### 步骤B: 创建控制面板
在Canvas下创建以下UI元素：

```
Canvas
├── ControlPanel (Panel)
│   ├── PositionDisplay (Panel)
│   │   └── PositionText (TextMeshPro - UI)
│   ├── VelocityDisplay (Panel)  
│   │   └── VelocityText (TextMeshPro - UI)
│   ├── StatusDisplay (Panel)
│   │   └── StatusText (TextMeshPro - UI)
│   └── TimeDisplay (Panel)
│       └── TimeText (TextMeshPro - UI)
│
├── AxisControls (Panel)
│   ├── XAxisControl (Panel)
│   │   ├── XLabel (Text)
│   │   └── XAxisSlider (Slider)
│   ├── YAxisControl (Panel)
│   │   ├── YLabel (Text)  
│   │   └── YAxisSlider (Slider)
│   └── ... (其他轴类似)
│
└── ButtonPanel (Panel)
    ├── StartButton (Button)
    ├── StopButton (Button)
    ├── ResetButton (Button)
    └── SpeedControl (Panel)
        ├── SpeedSlider (Slider)
        └── SpeedText (TextMeshPro - UI)
```

#### 步骤C: 配置滑块范围
在Inspector中设置每个滑块的范围：

```csharp
// X、Y、Z轴 (线性轴，单位：mm)
xAxisSlider.minValue = -100f;
xAxisSlider.maxValue = 100f;

// A、C轴 (旋转轴，单位：度)
aAxisSlider.minValue = -180f;
aAxisSlider.maxValue = 180f;

// 速度滑块
speedSlider.minValue = 0.1f;
speedSlider.maxValue = 5.0f;
speedSlider.value = 1.0f;
```

### 5. 刀具路径可视化配置

#### 步骤A: 创建LineRenderer
1. 在场景中创建空GameObject，命名为"ToolPath"
2. 添加LineRenderer组件
3. 配置LineRenderer属性：

```csharp
LineRenderer设置:
├─ Material: 创建新材质 (亮绿色，发光)
├─ Width: Start=0.005, End=0.005
├─ Position Count: 0 (动态设置)
├─ Use World Space: true
└─ Color: 绿色渐变
```

#### 步骤B: 创建刀尖标记
1. 在Tool下创建空GameObject，命名为"ToolTip"
2. 添加小球体作为可视化标记
3. 将ToolTip拖拽到MachineVisualizer的toolTip字段

### 6. WebGL插件配置

#### 步骤A: 放置插件文件
将`WebGLSocketPlugin.jslib`放在以下路径：
```
Assets/Plugins/WebGL/WebGLSocketPlugin.jslib
```

#### 步骤B: 验证插件配置
在Unity Editor中：
1. 选择WebGLSocketPlugin.jslib文件
2. 在Inspector中确认Platform为WebGL
3. 确认Auto Referenced为勾选状态

### 7. 构建设置配置

#### 步骤A: Player Settings配置
```
File → Build Settings → Player Settings

Company Name: CNCSimulator
Product Name: 五轴数控机床仿真器

Resolution and Presentation:
├─ Run In Background: ✓
├─ Display Resolution Dialog: Disabled
└─ Default Screen Width: 1920, Height: 1080

WebGL Settings:
├─ Compression Format: Gzip
├─ Memory Size: 512 MB
├─ Enable Exceptions: None
└─ Optimization Level: Size
```

#### 步骤B: Quality Settings
```
Edit → Project Settings → Quality

Level: Medium
├─ Texture Quality: Half Res  
├─ Anti Aliasing: 2x Multi Sampling
├─ Soft Particles: ✓
└─ Realtime Reflection Probes: ✓
```

### 8. 测试和调试

#### 步骤A: Editor模式测试
1. 运行场景，检查Console是否有错误
2. 验证CNCMachineController是否正确初始化
3. 检查UI组件是否正确连接

#### 步骤B: WebGL构建测试
1. Build Settings → Build
2. 选择输出目录：`项目根目录/static/unity/Build/`
3. 构建完成后，通过Web服务器访问测试

### 9. 常见问题和解决方案

#### 问题1: 脚本组件显示Missing
**解决方案**: 
- 确认脚本文件名与类名一致
- 检查脚本语法错误，查看Console面板

#### 问题2: Transform引用为空
**解决方案**:
- 确认GameObject名称正确
- 重新拖拽分配Transform引用
- 检查GameObject层次结构

#### 问题3: WebSocket连接失败
**解决方案**:
- 确认WebGLSocketPlugin.jslib正确放置
- 检查JavaScript Console错误信息
- 验证服务器地址和端口

#### 问题4: 动画不流畅
**解决方案**:
- 调整positionScale参数
- 增加smoothTime值
- 检查帧率和性能

### 10. 性能优化建议

#### 模型优化
```csharp
建议设置:
├─ 总面数: < 50,000 三角面
├─ 材质数量: < 10个
├─ 纹理分辨率: 512x512 或 1024x1024
└─ LOD系统: 启用多级细节
```

#### 脚本优化
```csharp
性能配置:
├─ enableSmoothing: 根据需要启用
├─ maxPathPoints: 根据性能调整 (500-2000)
├─ 更新频率: 考虑降低Update频率
└─ 缓存引用: 避免重复查找组件
```

## 🎯 挂载检查清单

- [ ] CNCMachineController.cs 已挂载到正确GameObject
- [ ] 所有Transform引用已正确分配 (tableX, tableY, spindleZ, headA, tableC, tool)
- [ ] positionScale参数已根据模型调整
- [ ] MachineVisualizer.cs 已挂载并配置UI组件
- [ ] Canvas和UI元素已创建并连接
- [ ] LineRenderer已配置用于刀具路径显示
- [ ] WebGLSocketPlugin.jslib已放置在正确目录
- [ ] WebGL构建设置已正确配置
- [ ] 脚本无语法错误，Console无报错

完成以上步骤后，您的Unity五轴机床模型就可以与FMU仿真系统实时通信了！
