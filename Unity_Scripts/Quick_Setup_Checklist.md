# Unity脚本快速挂载清单

## 🚀 5分钟快速设置

### 步骤1: 准备GameObject结构
```
在Unity Hierarchy中创建：

CNCMachine (空GameObject)
├── Controllers (空GameObject)
├── TableX (您的X轴移动部件)  
├── TableY (您的Y轴移动部件)
├── SpindleZ (您的Z轴主轴部件)
├── HeadA (您的A轴摆头部件)
├── TableC (您的C轴转台部件)
└── Tool (您的刀具部件)
```

### 步骤2: 挂载CNCMachineController
1. **选择** Controllers GameObject
2. **拖拽** CNCMachineController.cs 到 Controllers
3. **配置** Inspector中的引用：
   ```
   Table X    → 拖入您的X轴GameObject
   Table Y    → 拖入您的Y轴GameObject  
   Spindle Z  → 拖入您的Z轴GameObject
   Head A     → 拖入您的A轴GameObject
   Table C    → 拖入您的C轴GameObject
   Tool       → 拖入您的刀具GameObject
   ```

### 步骤3: 调整运动参数
```
Position Scale: 0.01    (如果您的模型1 Unity单位 = 100mm)
Position Scale: 0.001   (如果您的模型1 Unity单位 = 1000mm)  
Position Scale: 1.0     (如果您的模型1 Unity单位 = 1mm)

Smooth Time: 0.1        (运动平滑度，越小越快速响应)
Enable Smoothing: ✓     (推荐开启)
```

### 步骤4: 挂载MachineVisualizer (可选)
1. **创建** Canvas (UI → Canvas)
2. **挂载** MachineVisualizer.cs 到 Controllers
3. **拖拽** Canvas 到 Main Canvas 字段
4. **其他UI组件可以暂时留空**

### 步骤5: 放置WebGL插件
```
将 WebGLSocketPlugin.jslib 复制到：
Assets/Plugins/WebGL/WebGLSocketPlugin.jslib

(如果目录不存在，请创建)
```

### 步骤6: 构建设置
1. **File → Build Settings**
2. **选择 WebGL 平台**
3. **输出目录设为**: `您的项目根目录/static/unity/Build/`
4. **点击 Build**

## ⚡ 最简配置（仅核心功能）

如果您只想快速测试，可以仅进行以下最基本配置：

### 必需配置：
```
✅ CNCMachineController.cs 挂载
✅ TableX, TableY, SpindleZ, HeadA, TableC 引用配置  
✅ Position Scale 参数调整
✅ WebGLSocketPlugin.jslib 文件放置
```

### 可选配置：
```
⭕ MachineVisualizer.cs (仅用于Unity内UI控制)
⭕ Tool 引用 (仅用于刀具路径显示)
⭕ UI组件 (仅用于Unity内调试)
```

## 🔧 关键参数说明

### Position Scale 如何确定？
测试方法：
1. 在FMU仿真中设置X轴位置为100mm
2. 观察Unity中X轴移动距离
3. 如果移动了10个Unity单位，则设置Position Scale = 0.1
4. 如果移动了1个Unity单位，则设置Position Scale = 0.01

### Transform 引用对应关系：
```
FMU轴 → Unity组件 → 运动类型
X轴   → TableX    → 工作台左右移动
Y轴   → TableY    → 工作台前后移动  
Z轴   → SpindleZ  → 主轴上下移动
A轴   → HeadA     → 摆头旋转 (绕X轴)
C轴   → TableC    → 转台旋转 (绕Y轴)
```

## 🐛 快速故障排除

### 问题：脚本显示Missing
**解决**: 检查脚本文件名是否与类名完全一致

### 问题：没有运动响应  
**解决**: 
1. 检查Transform引用是否正确分配
2. 确认Position Scale参数
3. 查看Console是否有错误信息

### 问题：运动方向错误
**解决**: 调整Position Scale为负值 (如-0.01)

### 问题：WebSocket连接失败
**解决**: 确认WebGLSocketPlugin.jslib在正确路径

## 📞 测试验证

构建完成后：
1. **启动** Python服务器: `python run_server.py`  
2. **访问** http://localhost:5000
3. **观察** Unity模型是否跟随仿真数据运动
4. **测试** 手动控制是否能控制Unity模型

如果以上都正常，说明挂载成功！🎉
