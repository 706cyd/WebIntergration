 ## FMU 接口与参数规范（供数字孪生 CNC 仿真与圆度分析）

本规范用于指导构建可与本 Web 服务集成的 FMU（建议 FMI 2.0/3.0 Co-Simulation）。FMU 需支持外部设参、按固定步长推进仿真，并输出用于圆度计算的轨迹数据（至少 X/Y 实际位置）。

---

### 1. 基本要求
- **FMI 版本**: 建议 2.0 Co-Simulation（支持 doStep）；可兼容 3.0。
- **步长**: 固定步长 `h`，推荐 0.5–1.0 ms；支持外部指定步长。
- **数值类型**: 轨迹输出使用 64 位浮点（Real64）。
- **单位与坐标**:
  - 直线轴: mm（`X`, `Y`, `Z`）
  - 回转轴: deg（`A`, `C`）
  - 右手坐标系、一致的正方向约定（文档中说明）。
- **复位语义**: 支持在 terminate 后重新 instantiate + setupExperiment 实现冷启动；如支持 warm reset，请说明并提供变量。

---

### 2. 变量接口（最小可行集合）

#### 2.1 输入（FMU Inputs）
- `enable` (Boolean): 伺服/仿真使能。
- `reset` (Boolean): 复位请求（可选，若不支持则通过 re-instantiate 实现）。
- `h_cmd` (Real, s): 期望步长（可选；若提供，将在 doStep 使用）。
- `x_ref`, `y_ref` (Real, mm): X/Y 轴指令位置；用于外部下发轨迹。
- `feedrate_ref` (Real, mm/s): 进给速度（可选）。
- `disturbance_enable` (Boolean): 扰动开关（可选）。

> 若 FMU 内部自带轨迹发生器，可额外提供：
> - `traj_mode` (Integer): 0=外部；1=内置圆；...
> - `circle_center_x`, `circle_center_y` (Real, mm)
> - `circle_radius` (Real, mm)
> - `circle_feedrate` (Real, mm/s)
> - `circle_direction` (Integer, 1=CCW, -1=CW)

#### 2.2 输出（FMU Outputs）
- `x_pos`, `y_pos` (Real, mm): X/Y 实际位置（圆度计算必需）。
- `x_err`, `y_err` (Real, mm): 跟踪误差（可选但推荐）。
- `x_vel`, `y_vel` (Real, mm/s): 实际速度（可选）。
- `sim_time` (Real, s): 当前仿真时间（可选，便于校验）。
- `ready` (Boolean): 就绪/健康状态。
- `fault_code` (Integer): 故障码（0=正常）。

> 若有回转/其他轴，请按同样命名规则扩展（如 `z_pos`, `a_pos`, `c_pos`）。

---

### 3. 可调参数（通过 Web API 下发）
Web 服务会向 `/api/fmu/parameters` 发送 JSON 映射到 FMU 变量名，示例：
```json
{
  "params": {
    "Kv_x": 1200.0,
    "Kv_y": 1100.0,
    "Kp_x": 8.0,
    "Ki_x": 120.0,
    "Kp_y": 7.5,
    "Ki_y": 100.0,
    "notch_freq_x": 220.0,
    "notch_zeta_x": 0.05,
    "vel_limit_x": 1000.0,
    "acc_limit_x": 8000.0,
    "Ts_controller": 0.001,
    "friction_x": 5.0,
    "stiffness_x": 1.0e6
  },
  "reinitialize": true
}
```

建议至少提供以下分组参数（按轴可带后缀 `_x`/`_y`）：
- **控制器**
  - `Kp_*`, `Ki_*`, `Kd_*`: 位置/速度环增益（根据结构定义）
  - `Kv_*`, `Ka_*`: 前馈/速度/加速度系数
  - `Ts_controller`: 控制器采样周期（s）
  - `filter_cutoff_*`, `notch_freq_*`, `notch_zeta_*`: 滤波/陷波参数
- **物理/负载**
  - `inertia_*`, `friction_*`, `viscous_*`: 转动惯量、库仑/粘性摩擦
  - `stiffness_*`, `damping_*`: 结构刚度/阻尼（用于弹性/共振建模）
  - `sensor_noise_std_*`: 传感器噪声标准差
- **约束**
  - `vel_limit_*`, `acc_limit_*`, `jerk_limit_*`: 速度/加速度/加加速度限幅
  - `pos_min_*`, `pos_max_*`: 行程极限

参数命名需与 FMU 内变量名一致；若需不同命名，请提供映射表。

---

### 4. 生命周期与时序
1. Web 端加载 FMU：`instantiate → setupExperiment(h) → enterInitializationMode → exitInitializationMode`。
2. （可选）通过 `/api/fmu/parameters` 下发参数，若 `reinitialize=true`，则重新 instantiate 以生效。
3. 运行：循环 `doStep(h)`，每步前写入 `x_ref`,`y_ref` 等输入，步后读取 `x_pos`,`y_pos` 等输出并记录。
4. 终止：`terminate → freeInstance`。

> 若支持事件模式/变步长，请在文档中说明限制与建议设置。

---

### 5. 轨迹与圆度数据要求
- 圆度计算依赖 `x_pos`,`y_pos` 的时间序列；推荐采样 ≥1 kHz。
- 位置分辨率优于 1 µm；噪声模型可调以贴近真实机床。
- 若使用内置圆轨迹：请保证一圈或多圈均匀采样，输出时间戳或统一步长。

---

### 6. 错误与诊断
- `ready=false` 或 `fault_code!=0` 时，Web 服务会中止当前轮次并返回错误。
- 建议提供以下诊断变量（可选）：
  - `saturation_*`（饱和度）、`following_error_*`（跟随误差）、`controller_state_*`。

---

### 7. 兼容性与测试清单
- 提供 `modelDescription.xml` 中完整的变量清单、单位及因果关系。
- 自测用例：
  1) 固定 `x_ref`/`y_ref` 台阶响应；
  2) 外部圆轨迹跟随（R=10 mm，F=100 mm/s，采样 1 kHz）；
  3) 设参前后对比误差带；
  4) 限幅/故障触发与恢复。

---

### 8. 命名建议（示例映射）
| Web Key | FMU Variable | Unit |
|---|---|---|
| `Kv_x` | `controller.Kv_x` | 1/s |
| `Kp_x` | `controller.Kp_x` | 1 |
| `Ki_x` | `controller.Ki_x` | 1/s |
| `vel_limit_x` | `limits.vel_x_max` | mm/s |
| `x_ref` | `command.x_ref` | mm |
| `x_pos` | `sensor.x_pos` | mm |

如命名不同，请在交付时提供完整映射表（CSV/MD）。

---

### 9. 交付物
- `YourModel.fmu`
- 变量/参数映射表（若命名不一致）
- 简短说明书：控制结构、推荐步长、已知限制

---

### 10. 快速对接流程
1) 上传 FMU → `/upload_fmu`
2) 设参 → `POST /api/fmu/parameters`（可 `reinitialize=true`）
3) 下发轨迹或启用内置轨迹
4) 运行仿真，生成 `x_pos`,`y_pos` 序列
5) 查询圆度 → `GET /api/sessions/<id>/roundness?time_range=...`



