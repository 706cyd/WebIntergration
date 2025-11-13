# FMU真实仿真功能使用指南

## 🎯 功能概述

现在系统支持真实FMU仿真计算，不再只是"直通模式"。当上传FMU文件后，系统会：

1. **解析FMU模型**：读取模型描述，识别输入/输出变量
2. **创建FMU实例**：实例化FMU并初始化
3. **变量映射**：自动映射FMU变量到CNC轴（X/Y/Z/A/C）
4. **真实计算**：调用FMU的`doStep`方法进行仿真计算
5. **结果存储**：将FMU输出存入数据库并驱动WebGL

## 🔄 工作流程

```
前端位置指令 → FMU输入变量 → FMU.doStep() → FMU输出变量 → CNC轴位置 → 数据库 → WebGL渲染
```

## 📋 使用步骤

### 1. 上传FMU文件
- 在前端"FMU文件管理"区域选择`.fmu`文件
- 点击"上传并加载"
- 系统会自动：
  - 解压FMU文件
  - 读取模型描述
  - 创建FMU实例
  - 建立变量映射

### 2. 启动仿真
- 点击"启动仿真"按钮
- 系统进入真实FMU仿真模式（如果FMU实例化成功）
- 否则回退到直通模式

### 3. 发送位置指令
- 在前端输入X/Y/Z/A/C轴的目标位置
- 指令会被映射到FMU的输入变量
- FMU计算后输出新的轴位置
- 结果自动存储到数据库并更新WebGL

## 🔧 技术实现

### FMU变量映射

系统会自动识别以下变量名模式：

```python
axis_patterns = {
    'X': ['x', 'X', 'x_pos', 'X_position', 'x_axis', 'table_x'],
    'Y': ['y', 'Y', 'y_pos', 'Y_position', 'y_axis', 'table_y'],
    'Z': ['z', 'Z', 'z_pos', 'Z_position', 'z_axis', 'spindle_z'],
    'A': ['a', 'A', 'a_rot', 'A_rotation', 'a_axis', 'head_a'],
    'C': ['c', 'C', 'c_rot', 'C_rotation', 'c_axis', 'table_c']
}
```

### 仿真模式

1. **真实FMU模式**（`use_fmu_passthrough = False`）
   - 调用`FMU2Slave.doStep()`进行计算
   - 使用FMU的输出作为轴位置

2. **直通模式**（`use_fmu_passthrough = True`）
   - 输出直接等于输入
   - 用于FMU实例化失败时的回退

3. **演示模式**（无FMU时）
   - 生成正弦波信号用于演示

### 异常处理

- **FMU加载失败**：回退到直通模式
- **FMU实例化失败**：回退到直通模式
- **doStep执行失败**：动态切换到直通模式
- **变量映射失败**：记录警告但继续运行

## 📊 日志和调试

### 关键日志信息

```
INFO - 成功加载并实例化FMU文件: example.fmu
INFO - 映射输入变量: X -> x_position
INFO - 映射输出变量: x_output -> X
INFO - FMU实例创建成功
DEBUG - FMU计算完成，时间: 1.234s
WARNING - FMU doStep失败，状态码: 1，切换到直通模式
```

### 调试方法

1. **查看变量映射**：
   ```python
   var_info = simulator.get_variable_info()
   print(var_info['input_variables'])
   print(var_info['output_variables'])
   ```

2. **检查FMU状态**：
   ```python
   print(f"FMU实例: {simulator.fmu_instance is not None}")
   print(f"直通模式: {simulator.use_fmu_passthrough}")
   print(f"输入映射: {simulator.input_variable_mapping}")
   print(f"输出映射: {simulator.output_variable_mapping}")
   ```

## 🧪 测试方法

运行集成测试脚本：

```bash
python test_fmu_integration.py
```

测试内容包括：
- FMU文件加载
- 变量映射检查
- 位置指令测试
- 仿真运行验证

## ⚠️ 注意事项

### FMU要求
- 必须是FMI 2.0 Co-Simulation格式
- 包含可执行的二进制文件
- 变量名符合映射模式

### 性能考虑
- FMU计算可能比直通模式慢
- 建议调整`step_size`以平衡精度和性能
- 大型FMU可能需要更多内存

### 错误处理
- 系统会自动回退到安全模式
- 不会因FMU错误导致整个系统崩溃
- 所有错误都会记录在日志中

## 🔍 故障排除

### 常见问题

1. **FMU加载失败**
   - 检查FMU文件格式
   - 确认FMI版本兼容性
   - 查看详细错误日志

2. **变量映射失败**
   - 检查FMU变量名是否符合模式
   - 手动检查模型描述文件
   - 考虑自定义映射规则

3. **仿真计算错误**
   - 检查输入值范围
   - 验证FMU初始化参数
   - 调整仿真步长

4. **性能问题**
   - 增大仿真步长`step_size`
   - 检查FMU计算复杂度
   - 监控系统资源使用

## 📈 未来扩展

- [ ] 支持自定义变量映射配置
- [ ] 添加FMU性能监控
- [ ] 支持参数动态调整
- [ ] 集成更多FMI标准功能
- [ ] 支持Model Exchange模式

---

通过这个真实FMU仿真功能，您现在可以：
- 上传任何兼容的FMU文件
- 获得真实的物理仿真结果
- 将结果自动存储到数据库
- 在WebGL中实时可视化

系统会智能处理各种异常情况，确保稳定可靠的运行。



