using UnityEngine;
using UnityEngine.UI;
using TMPro;

/// <summary>
/// 机床可视化组件
/// 显示机床状态、轴位置信息等
/// </summary>
public class MachineVisualizer : MonoBehaviour
{
    [Header("UI组件")]
    [SerializeField] private Canvas mainCanvas;
    [SerializeField] private TextMeshProUGUI positionText;
    [SerializeField] private TextMeshProUGUI velocityText;
    [SerializeField] private TextMeshProUGUI statusText;
    [SerializeField] private TextMeshProUGUI timeText;
    
    [Header("轴位置滑块")]
    [SerializeField] private Slider xAxisSlider;
    [SerializeField] private Slider yAxisSlider;
    [SerializeField] private Slider zAxisSlider;
    [SerializeField] private Slider aAxisSlider;
    [SerializeField] private Slider cAxisSlider;
    
    [Header("控制按钮")]
    [SerializeField] private Button startButton;
    [SerializeField] private Button stopButton;
    [SerializeField] private Button resetButton;
    
    [Header("速度控制")]
    [SerializeField] private Slider speedSlider;
    [SerializeField] private TextMeshProUGUI speedText;
    
    [Header("可视化效果")]
    [SerializeField] private LineRenderer toolPath;
    [SerializeField] private Transform toolTip;
    [SerializeField] private Material pathMaterial;
    [SerializeField] private int maxPathPoints = 1000;
    
    private CNCMachineController machineController;
    private bool isRecordingPath = false;
    private int pathPointIndex = 0;
    
    // 轴位置范围
    private readonly float[] axisRanges = { 200f, 200f, 100f, 360f, 360f }; // X, Y, Z, A, C
    
    void Start()
    {
        InitializeUI();
        FindMachineController();
        SetupEventListeners();
    }
    
    void Update()
    {
        UpdateDisplay();
        RecordToolPath();
    }
    
    /// <summary>
    /// 初始化UI组件
    /// </summary>
    private void InitializeUI()
    {
        // 设置滑块范围
        if (xAxisSlider) { xAxisSlider.minValue = -axisRanges[0] / 2; xAxisSlider.maxValue = axisRanges[0] / 2; }
        if (yAxisSlider) { yAxisSlider.minValue = -axisRanges[1] / 2; yAxisSlider.maxValue = axisRanges[1] / 2; }
        if (zAxisSlider) { zAxisSlider.minValue = -axisRanges[2] / 2; zAxisSlider.maxValue = axisRanges[2] / 2; }
        if (aAxisSlider) { aAxisSlider.minValue = -axisRanges[3] / 2; aAxisSlider.maxValue = axisRanges[3] / 2; }
        if (cAxisSlider) { cAxisSlider.minValue = -axisRanges[4] / 2; cAxisSlider.maxValue = axisRanges[4] / 2; }
        
        // 设置速度滑块
        if (speedSlider)
        {
            speedSlider.minValue = 0.1f;
            speedSlider.maxValue = 5.0f;
            speedSlider.value = 1.0f;
        }
        
        // 初始化刀具路径
        if (toolPath)
        {
            toolPath.material = pathMaterial;
            toolPath.positionCount = 0;
            toolPath.startWidth = 0.005f;
            toolPath.endWidth = 0.005f;
        }
    }
    
    /// <summary>
    /// 查找机床控制器
    /// </summary>
    private void FindMachineController()
    {
        machineController = FindObjectOfType<CNCMachineController>();
        if (machineController == null)
        {
            Debug.LogError("MachineVisualizer: 未找到CNCMachineController组件！");
        }
    }
    
    /// <summary>
    /// 设置事件监听器
    /// </summary>
    private void SetupEventListeners()
    {
        // 轴位置滑块事件
        if (xAxisSlider) xAxisSlider.onValueChanged.AddListener(value => OnAxisSliderChanged("X", value));
        if (yAxisSlider) yAxisSlider.onValueChanged.AddListener(value => OnAxisSliderChanged("Y", value));
        if (zAxisSlider) zAxisSlider.onValueChanged.AddListener(value => OnAxisSliderChanged("Z", value));
        if (aAxisSlider) aAxisSlider.onValueChanged.AddListener(value => OnAxisSliderChanged("A", value));
        if (cAxisSlider) cAxisSlider.onValueChanged.AddListener(value => OnAxisSliderChanged("C", value));
        
        // 控制按钮事件
        if (startButton) startButton.onClick.AddListener(OnStartButtonClicked);
        if (stopButton) stopButton.onClick.AddListener(OnStopButtonClicked);
        if (resetButton) resetButton.onClick.AddListener(OnResetButtonClicked);
        
        // 速度滑块事件
        if (speedSlider) speedSlider.onValueChanged.AddListener(OnSpeedSliderChanged);
    }
    
    /// <summary>
    /// 更新显示内容
    /// </summary>
    private void UpdateDisplay()
    {
        if (machineController == null) return;
        
        // 更新位置显示
        if (positionText)
        {
            positionText.text = $"当前位置:\n" +
                               $"X: {GetAxisPosition("X"):F2} mm\n" +
                               $"Y: {GetAxisPosition("Y"):F2} mm\n" +
                               $"Z: {GetAxisPosition("Z"):F2} mm\n" +
                               $"A: {GetAxisPosition("A"):F2}°\n" +
                               $"C: {GetAxisPosition("C"):F2}°";
        }
        
        // 更新速度显示
        if (velocityText)
        {
            velocityText.text = $"轴速度:\n" +
                               $"X: {GetAxisVelocity("X"):F1} mm/min\n" +
                               $"Y: {GetAxisVelocity("Y"):F1} mm/min\n" +
                               $"Z: {GetAxisVelocity("Z"):F1} mm/min\n" +
                               $"A: {GetAxisVelocity("A"):F1} °/min\n" +
                               $"C: {GetAxisVelocity("C"):F1} °/min";
        }
        
        // 更新状态显示
        if (statusText)
        {
            var state = GetMachineState();
            statusText.text = $"机床状态: {(state.is_running ? "运行中" : "停止")}\n" +
                             $"就绪: {(state.ready ? "是" : "否")}\n" +
                             $"报警: {(state.alarm ? "是" : "否")}\n" +
                             $"刀具号: {state.tool_info.tool_number}";
        }
        
        // 更新时间显示
        if (timeText)
        {
            var state = GetMachineState();
            timeText.text = $"仿真时间: {state.simulation_time:F2} s";
        }
        
        // 更新速度显示
        if (speedText && speedSlider)
        {
            speedText.text = $"速度: {speedSlider.value:F1}x";
        }
    }
    
    /// <summary>
    /// 记录刀具路径
    /// </summary>
    private void RecordToolPath()
    {
        if (!isRecordingPath || toolPath == null || toolTip == null) return;
        
        // 添加当前刀具位置到路径
        if (pathPointIndex < maxPathPoints)
        {
            toolPath.positionCount = pathPointIndex + 1;
            toolPath.SetPosition(pathPointIndex, toolTip.position);
            pathPointIndex++;
        }
        else
        {
            // 路径点数达到最大值，清除旧的点
            ClearToolPath();
        }
    }
    
    /// <summary>
    /// 轴位置滑块改变事件
    /// </summary>
    private void OnAxisSliderChanged(string axis, float value)
    {
        if (machineController != null)
        {
            machineController.SendAxisCommand(axis, value);
        }
    }
    
    /// <summary>
    /// 启动按钮点击事件
    /// </summary>
    private void OnStartButtonClicked()
    {
        // 启动仿真
        #if UNITY_WEBGL && !UNITY_EDITOR
        Application.ExternalCall("startSimulation");
        #endif
        
        // 开始记录刀具路径
        StartRecordingToolPath();
        
        Debug.Log("启动仿真");
    }
    
    /// <summary>
    /// 停止按钮点击事件
    /// </summary>
    private void OnStopButtonClicked()
    {
        // 停止仿真
        #if UNITY_WEBGL && !UNITY_EDITOR
        Application.ExternalCall("stopSimulation");
        #endif
        
        // 停止记录刀具路径
        StopRecordingToolPath();
        
        Debug.Log("停止仿真");
    }
    
    /// <summary>
    /// 重置按钮点击事件
    /// </summary>
    private void OnResetButtonClicked()
    {
        // 重置所有滑块到中心位置
        if (xAxisSlider) xAxisSlider.value = 0;
        if (yAxisSlider) yAxisSlider.value = 0;
        if (zAxisSlider) zAxisSlider.value = 0;
        if (aAxisSlider) aAxisSlider.value = 0;
        if (cAxisSlider) cAxisSlider.value = 0;
        
        // 清除刀具路径
        ClearToolPath();
        
        Debug.Log("重置机床位置");
    }
    
    /// <summary>
    /// 速度滑块改变事件
    /// </summary>
    private void OnSpeedSliderChanged(float value)
    {
        if (machineController != null)
        {
            machineController.SetSimulationSpeed(value);
        }
        
        #if UNITY_WEBGL && !UNITY_EDITOR
        Application.ExternalCall("setSimulationSpeed", value);
        #endif
    }
    
    /// <summary>
    /// 开始记录刀具路径
    /// </summary>
    public void StartRecordingToolPath()
    {
        isRecordingPath = true;
        pathPointIndex = 0;
        if (toolPath) toolPath.positionCount = 0;
    }
    
    /// <summary>
    /// 停止记录刀具路径
    /// </summary>
    public void StopRecordingToolPath()
    {
        isRecordingPath = false;
    }
    
    /// <summary>
    /// 清除刀具路径
    /// </summary>
    public void ClearToolPath()
    {
        if (toolPath)
        {
            toolPath.positionCount = 0;
            pathPointIndex = 0;
        }
    }
    
    /// <summary>
    /// 获取轴位置（模拟方法，实际应从machineController获取）
    /// </summary>
    private float GetAxisPosition(string axis)
    {
        // 这里应该从machineController获取实际位置
        // 目前返回模拟值
        switch (axis)
        {
            case "X": return xAxisSlider ? xAxisSlider.value : 0f;
            case "Y": return yAxisSlider ? yAxisSlider.value : 0f;
            case "Z": return zAxisSlider ? zAxisSlider.value : 0f;
            case "A": return aAxisSlider ? aAxisSlider.value : 0f;
            case "C": return cAxisSlider ? cAxisSlider.value : 0f;
            default: return 0f;
        }
    }
    
    /// <summary>
    /// 获取轴速度（模拟方法）
    /// </summary>
    private float GetAxisVelocity(string axis)
    {
        // 这里应该从machineController获取实际速度
        return Random.Range(0f, 100f);
    }
    
    /// <summary>
    /// 获取机床状态（模拟方法）
    /// </summary>
    private MachineState GetMachineState()
    {
        return new MachineState
        {
            is_running = true,
            simulation_time = Time.time,
            ready = true,
            alarm = false,
            tool_info = new ToolInfo
            {
                tool_number = 1,
                spindle_speed = 1000,
                feed_rate = 100
            }
        };
    }
    
    /// <summary>
    /// 切换UI显示
    /// </summary>
    public void ToggleUI()
    {
        if (mainCanvas)
        {
            mainCanvas.gameObject.SetActive(!mainCanvas.gameObject.activeSelf);
        }
    }
}
