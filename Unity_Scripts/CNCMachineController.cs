using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Runtime.InteropServices;
using Newtonsoft.Json;

/// <summary>
/// 五轴数控机床Unity控制器
/// 通过WebSocket接收FMU仿真数据并控制3D模型运动
/// </summary>
public class CNCMachineController : MonoBehaviour
{
    [Header("机床组件引用")]
    [SerializeField] private Transform tableX;      // X轴工作台
    [SerializeField] private Transform tableY;      // Y轴工作台
    [SerializeField] private Transform spindleZ;    // Z轴主轴
    [SerializeField] private Transform headA;       // A轴摆头
    [SerializeField] private Transform tableC;      // C轴转台
    [SerializeField] private Transform tool;        // 刀具
    
    [Header("运动参数")]
    [SerializeField] private float positionScale = 1.0f;  // 位置缩放比例 (Unity与模型均按mm)
    [SerializeField] private float smoothTime = 0.1f;      // 平滑时间
    [SerializeField] private bool enableSmoothing = true;  // 启用平滑运动
    
    [Header("调试选项")]
    [SerializeField] private bool debugMode = true;
    [SerializeField] private Canvas debugUI;

    [Header("Debug Movement")]
    [Tooltip("启用后，可以使用键盘箭头来测试Z轴运动和碰撞。")]
    [SerializeField] private bool enableDebugMovement = true;
    [SerializeField] private float debugMoveSpeed = 1.0f;
    
    // 碰撞相关字段已移除
    
    // 当前位置和目标位置
    private Vector3 currentPositionX = Vector3.zero;
    private Vector3 currentPositionY = Vector3.zero;
    private Vector3 currentPositionZ = Vector3.zero;
    private Vector3 currentRotationA = Vector3.zero;
    private Vector3 currentRotationC = Vector3.zero;
    
    private Vector3 targetPositionX = Vector3.zero;
    private Vector3 targetPositionY = Vector3.zero;
    private Vector3 targetPositionZ = Vector3.zero;
    private Vector3 targetRotationA = Vector3.zero;
    private Vector3 targetRotationC = Vector3.zero;
    
    // 速度数据
    private Dictionary<string, float> axisVelocities = new Dictionary<string, float>();
    
    // 机床状态
    private MachineState machineState = new MachineState();
    
    // WebSocket通信相关
    private bool isConnected = false;
    private string lastDataTimestamp = "";
    
    #if UNITY_WEBGL && !UNITY_EDITOR
    // WebGL平台的JavaScript互操作
    [DllImport("__Internal")]
    private static extern void ConnectToWebSocket();
    
    [DllImport("__Internal")]
    private static extern void SendCommandToServer(string command);
    
    [DllImport("__Internal")]
    private static extern void RegisterUnityCallback();
    #endif
    
    void Start()
    {
        InitializeMachine();
        ConnectToSimulationServer();
    }
    
    void Update()
    {
        

        // --- DEBUG MOVEMENT ---
        if (enableDebugMovement && spindleZ != null)
        {
            float verticalInput = Input.GetAxis("Vertical"); // 上下箭头
            targetPositionZ += new Vector3(0, 0, verticalInput * debugMoveSpeed * Time.deltaTime);
        }
        // --- END DEBUG MOVEMENT ---
        
        UpdateMachineMovement();
        UpdateDebugInfo();
    }
    
    /// <summary>
    /// 初始化机床组件
    /// </summary>
    private void InitializeMachine()
    {
        // 验证所有必需的组件是否已分配
        if (tableX == null || tableY == null || spindleZ == null || 
            headA == null || tableC == null)
        {
            Debug.LogError("CNCMachineController: 缺少必需的机床组件引用！");
            enabled = false;
            return;
        }
        
        // 记录初始位置
        currentPositionX = tableX.localPosition;
        currentPositionY = tableY.localPosition;
        currentPositionZ = spindleZ.localPosition;
        currentRotationA = headA.localEulerAngles;
        currentRotationC = tableC.localEulerAngles;
        
        Debug.Log("CNCMachineController: 机床初始化完成");
    }
    
    /// <summary>
    /// 连接到仿真服务器
    /// </summary>
    private void ConnectToSimulationServer()
    {
        #if UNITY_WEBGL && !UNITY_EDITOR
        RegisterUnityCallback();
        ConnectToWebSocket();
        #else
        // 编辑器模式下的模拟连接 - 这部分将被移除
        Debug.Log("编辑器模式已被禁用");
        #endif
    }
    
    /// <summary>
    /// 更新机床运动
    /// </summary>
    private void UpdateMachineMovement()
    {
        if (!isConnected) return;
        
        float deltaTime = Time.deltaTime;
        
        if (enableSmoothing)
        {
            // 平滑插值运动
            currentPositionX = Vector3.Lerp(currentPositionX, targetPositionX, deltaTime / smoothTime);
            currentPositionY = Vector3.Lerp(currentPositionY, targetPositionY, deltaTime / smoothTime);
            currentPositionZ = Vector3.Lerp(currentPositionZ, targetPositionZ, deltaTime / smoothTime);
            currentRotationA = Vector3.Lerp(currentRotationA, targetRotationA, deltaTime / smoothTime);
            currentRotationC = Vector3.Lerp(currentRotationC, targetRotationC, deltaTime / smoothTime);
        }
        else
        {
            // 直接设置位置
            currentPositionX = targetPositionX;
            currentPositionY = targetPositionY;
            currentPositionZ = targetPositionZ;
            currentRotationA = targetRotationA;
            currentRotationC = targetRotationC;
        }
        
        // 应用变换
        ApplyTransforms();
    }
    
    /// <summary>
    /// 应用变换到机床组件
    /// </summary>
    private void ApplyTransforms()
    {
        if (tableX != null)
            tableX.localPosition = currentPositionX;
            
        if (tableY != null)
            tableY.localPosition = currentPositionY;
            
        if (spindleZ != null)
            spindleZ.localPosition = currentPositionZ;
            
        if (headA != null)
            headA.localEulerAngles = currentRotationA;
            
        if (tableC != null)
            tableC.localEulerAngles = currentRotationC;
    }

    /// <summary>
    /// 计算某个变换在给定局部轴方向上的父层级缩放（近似）。
    /// 返回该局部轴在世界空间中的整体尺度系数（只考虑缩放，不考虑旋转导致的轴混合）。
    /// </summary>
    private float GetParentAxisScale(Transform t, Vector3 localAxis)
    {
        if (t == null) return 1f;
        Transform p = t.parent;
        // 若无父级，仅返回1
        if (p == null) return 1f;

        // 将局部轴逐级映射，同时累乘对应轴向缩放的模长
        // 简化：取父级缩放在该轴方向的长度近似（忽略非均匀缩放下旋转造成的轴耦合）
        float scale = 1f;
        Vector3 axis = localAxis.normalized;
        while (p != null)
        {
            // 在父级局部坐标中，轴向会被父级旋转改变；这里采用近似：按父级的lossyScale在各分量上的投影长度
            Vector3 s = p.lossyScale;
            // 近似投影：|axis.x|*sx + |axis.y|*sy + |axis.z|*sz （上界近似）
            float projected = Mathf.Abs(axis.x) * Mathf.Max(1e-6f, s.x)
                            + Mathf.Abs(axis.y) * Mathf.Max(1e-6f, s.y)
                            + Mathf.Abs(axis.z) * Mathf.Max(1e-6f, s.z);
            scale *= projected;

            p = p.parent;
        }
        return scale;
    }
    
    /// <summary>
    /// 接收来自WebSocket的变换数据
    /// 此方法将被JavaScript调用
    /// </summary>
    /// <param name="jsonData">JSON格式的变换数据</param>
    public void ReceiveTransformData(string jsonData)
    {
        try
        {
            var data = JsonConvert.DeserializeObject<UnityTransformData>(jsonData);
            
            // 更新时间戳
            lastDataTimestamp = data.timestamp.ToString();
            
            // 更新目标位置
            UpdateTargetTransforms(data.transforms);
            
            // 更新速度数据
            axisVelocities = data.velocities;
            
            // 更新机床状态
            machineState = data.machine_state;
            
            isConnected = true;
            
            if (debugMode)
            {
                Debug.Log($"接收到变换数据: 时间戳={lastDataTimestamp}");
            }
        }
        catch (System.Exception e)
        {
            Debug.LogError($"解析变换数据失败: {e.Message}");
        }
    }
    
    /// <summary>
    /// 更新目标变换
    /// </summary>
    private void UpdateTargetTransforms(Dictionary<string, TransformInfo> transforms)
    {
        if (transforms.ContainsKey("table_x"))
        {
            var pos = transforms["table_x"].position;
            // 补偿父层级缩放，确保X轴与仿真尺度一致
            float invParentScaleX = 1f / Mathf.Max(1e-6f, GetParentAxisScale(tableX, Vector3.right));
            float invParentScaleY = 1f / Mathf.Max(1e-6f, GetParentAxisScale(tableX, Vector3.up));
            float invParentScaleZ = 1f / Mathf.Max(1e-6f, GetParentAxisScale(tableX, Vector3.forward));
            targetPositionX = new Vector3(
                pos.x * positionScale * invParentScaleX,
                pos.y * positionScale * invParentScaleY,
                pos.z * positionScale * invParentScaleZ
            );
        }
        
        if (transforms.ContainsKey("table_y"))
        {
            var pos = transforms["table_y"].position;
            // 补偿父层级缩放，确保Y轴与仿真尺度一致
            float invParentScaleX = 1f / Mathf.Max(1e-6f, GetParentAxisScale(tableY, Vector3.right));
            float invParentScaleY = 1f / Mathf.Max(1e-6f, GetParentAxisScale(tableY, Vector3.up));
            float invParentScaleZ = 1f / Mathf.Max(1e-6f, GetParentAxisScale(tableY, Vector3.forward));
            targetPositionY = new Vector3(
                pos.x * positionScale * invParentScaleX,
                pos.y * positionScale * invParentScaleY,
                pos.z * positionScale * invParentScaleZ
            );
        }
        
        if (transforms.ContainsKey("spindle_z"))
        {
            var pos = transforms["spindle_z"].position;
            // 按父层级缩放进行补偿，使世界位移与仿真尺度一致
            float invParentScaleX = 1f / Mathf.Max(1e-6f, GetParentAxisScale(spindleZ, Vector3.right));
            float invParentScaleY = 1f / Mathf.Max(1e-6f, GetParentAxisScale(spindleZ, Vector3.up));
            float invParentScaleZ = 1f / Mathf.Max(1e-6f, GetParentAxisScale(spindleZ, Vector3.forward));
            targetPositionZ = new Vector3(
                pos.x * positionScale * invParentScaleX,
                pos.z * positionScale * invParentScaleY,
                pos.y * positionScale * invParentScaleZ
            );
        }
        
        if (transforms.ContainsKey("head_a"))
        {
            var rot = transforms["head_a"].rotation;
            targetRotationA = new Vector3(rot.x, rot.y, rot.z);
        }
        
        if (transforms.ContainsKey("table_c")) 
        {
            var rot = transforms["table_c"].rotation;
            targetRotationC = new Vector3(rot.x, rot.z, rot.y);
        }
    }
    
    /// <summary>
    /// 发送指令到服务器
    /// </summary>
    public void SendAxisCommand(string axis, float position)
    {
        var command = new
        {
            type = "move_axis",
            axis = axis,
            position = position
        };
        
        string jsonCommand = JsonConvert.SerializeObject(command);
        
        #if UNITY_WEBGL && !UNITY_EDITOR
        SendCommandToServer(jsonCommand);
        #else
        Debug.Log($"编辑器模式已被禁用 - 指令未发送: {jsonCommand}");
        #endif
    }
    
    /// <summary>
    /// 设置仿真速度
    /// </summary>
    public void SetSimulationSpeed(float speed)
    {
        var command = new
        {
            type = "set_speed",
            speed = speed
        };
        
        string jsonCommand = JsonConvert.SerializeObject(command);
        
        #if UNITY_WEBGL && !UNITY_EDITOR
        SendCommandToServer(jsonCommand);
        #else
        Debug.Log($"编辑器模式已被禁用 - 速度设置未发送: {jsonCommand}");
        #endif
    }
    
    // 碰撞处理相关方法已移除
    
    /// <summary>
    /// 更新调试信息
    /// </summary>
    private void UpdateDebugInfo()
    {
        if (!debugMode || debugUI == null) return;
        
        // 可以在这里更新UI显示当前位置、速度等信息
    }
    
    // SimulateDataInEditor 方法将被完全删除
    
    /// <summary>
    /// 连接状态改变回调
    /// </summary>
    public void OnConnectionStatusChanged(string status)
    {
        isConnected = status == "connected";
        Debug.Log($"WebSocket连接状态: {status}");
    }
}

// 数据结构定义
[System.Serializable]
public class UnityTransformData
{
    public float timestamp;
    public Dictionary<string, TransformInfo> transforms;
    public Dictionary<string, float> velocities;
    public MachineState machine_state;
}

[System.Serializable]
public class TransformInfo
{
    public Vector3Info position = new Vector3Info();
    public Vector3Info rotation = new Vector3Info();
    public Vector3Info scale = new Vector3Info { x = 1, y = 1, z = 1 };
}

[System.Serializable]
public class Vector3Info
{
    public float x;
    public float y;
    public float z;
}

[System.Serializable]
public class MachineState
{
    public bool is_running;
    public float simulation_time;
    public float step_size;
    public bool alarm;
    public bool ready;
    public ToolInfo tool_info = new ToolInfo();
}

[System.Serializable]
public class ToolInfo
{
    public int tool_number;
    public float spindle_speed;
    public float feed_rate;
}
