using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Runtime.InteropServices;
using Newtonsoft.Json;

// Alternative: If you don't want to install Newtonsoft.Json, uncomment the line below and comment out the Newtonsoft.Json line above
// Note: This will require some code modifications to work with Unity's JsonUtility
// using System;

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
    [SerializeField] private float positionScale = 0.01f;  // 位置缩放比例
    [SerializeField] private float smoothTime = 0.1f;      // 平滑时间
    [SerializeField] private bool enableSmoothing = true;  // 启用平滑运动
    
    [Header("调试选项")]
    [SerializeField] private bool debugMode = true;
    [SerializeField] private Canvas debugUI;
    
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
        // 编辑器模式下的模拟连接
        Debug.Log("编辑器模式：模拟WebSocket连接");
        isConnected = true;
        StartCoroutine(SimulateDataInEditor());
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
            targetPositionX = new Vector3(pos.x * positionScale, pos.y * positionScale, pos.z * positionScale);
        }
        
        if (transforms.ContainsKey("table_y"))
        {
            var pos = transforms["table_y"].position;
            targetPositionY = new Vector3(pos.x * positionScale, pos.y * positionScale, pos.z * positionScale);
        }
        
        if (transforms.ContainsKey("spindle_z"))
        {
            var pos = transforms["spindle_z"].position;
            targetPositionZ = new Vector3(pos.x * positionScale, pos.y * positionScale, pos.z * positionScale);
        }
        
        if (transforms.ContainsKey("head_a"))
        {
            var rot = transforms["head_a"].rotation;
            targetRotationA = new Vector3(rot.x, rot.y, rot.z);
        }
        
        if (transforms.ContainsKey("table_c"))
        {
            var rot = transforms["table_c"].rotation;
            targetRotationC = new Vector3(rot.x, rot.y, rot.z);
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
        Debug.Log($"编辑器模式 - 发送指令: {jsonCommand}");
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
        Debug.Log($"编辑器模式 - 设置速度: {jsonCommand}");
        #endif
    }
    
    /// <summary>
    /// 更新调试信息
    /// </summary>
    private void UpdateDebugInfo()
    {
        if (!debugMode || debugUI == null) return;
        
        // 可以在这里更新UI显示当前位置、速度等信息
    }
    
    /// <summary>
    /// 编辑器模式下的数据模拟
    /// </summary>
    private IEnumerator SimulateDataInEditor()
    {
        while (true)
        {
            yield return new WaitForSeconds(0.1f);
            
            // 模拟仿真数据
            float t = Time.time;
            var simulatedData = new UnityTransformData
            {
                timestamp = t,
                transforms = new Dictionary<string, TransformInfo>
                {
                    ["table_x"] = new TransformInfo 
                    { 
                        position = new Vector3Info { x = 10 * Mathf.Sin(0.1f * t), y = 0, z = 0 }
                    },
                    ["table_y"] = new TransformInfo 
                    { 
                        position = new Vector3Info { x = 0, y = 0, z = 10 * Mathf.Cos(0.1f * t) }
                    },
                    ["spindle_z"] = new TransformInfo 
                    { 
                        position = new Vector3Info { x = 0, y = 5 * Mathf.Sin(0.05f * t), z = 0 }
                    },
                    ["head_a"] = new TransformInfo 
                    { 
                        rotation = new Vector3Info { x = 30 * Mathf.Sin(0.02f * t), y = 0, z = 0 }
                    },
                    ["table_c"] = new TransformInfo 
                    { 
                        rotation = new Vector3Info { x = 0, y = 45 * Mathf.Cos(0.03f * t), z = 0 }
                    }
                },
                velocities = new Dictionary<string, float>(),
                machine_state = new MachineState { is_running = true }
            };
            
            UpdateTargetTransforms(simulatedData.transforms);
        }
    }
    
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
