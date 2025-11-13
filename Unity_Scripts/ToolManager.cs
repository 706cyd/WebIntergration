using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 管理所有刀具的切换，确保同时只激活一把刀具
/// </summary>
public class ToolManager : MonoBehaviour
{
    [Header("刀具管理")]
    [Tooltip("所有可用的刀具列表")]
    public List<EndmillTool> tools = new List<EndmillTool>();
    
    [Tooltip("当前激活的刀具索引")]
    public int currentToolIndex = 0;
    
    [Header("调试")]
    [Tooltip("启用调试信息")]
    public bool debugMode = true;

    // 当前激活的刀具引用
    private EndmillTool currentTool;

    // 单例模式，便于其他脚本访问
    public static ToolManager Instance { get; private set; }

    private void Awake()
    {
        // 设置单例
        if (Instance == null)
        {
            Instance = this;
            // DontDestroyOnLoad(gameObject); // 如果需要跨场景保留，取消注释
        }
        else
        {
            Destroy(gameObject);
            return;
        }
        
        InitializeTools();
    }

    /// <summary>
    /// 初始化所有刀具
    /// </summary>
    private void InitializeTools()
    {
        if (tools.Count == 0)
        {
            Debug.LogWarning("刀具列表为空！请将刀具添加到ToolManager的tools列表中。");
            return;
        }

        // 首先禁用所有刀具
        foreach (EndmillTool tool in tools)
        {
            if (tool != null)
            {
                tool.SetActive(false);
            }
        }

        // 查找默认刀具或使用第一个刀具
        int defaultIndex = FindDefaultToolIndex();
        
        // 激活默认刀具
        SwitchToTool(defaultIndex);
    }

    /// <summary>
    /// 查找标记为默认的刀具
    /// </summary>
    private int FindDefaultToolIndex()
    {
        for (int i = 0; i < tools.Count; i++)
        {
            if (tools[i] != null && tools[i].isDefaultTool)
            {
                return i;
            }
        }
        
        // 如果没有找到默认刀具，使用第一个有效的刀具
        for (int i = 0; i < tools.Count; i++)
        {
            if (tools[i] != null)
            {
                return i;
            }
        }
        
        return 0;
    }

    /// <summary>
    /// 切换到指定索引的刀具
    /// </summary>
    /// <param name="toolIndex">刀具在列表中的索引</param>
    public void SwitchToTool(int toolIndex)
    {
        if (tools.Count == 0) return;
        
        // 检查索引是否有效
        if (toolIndex < 0 || toolIndex >= tools.Count)
        {
            Debug.LogWarning($"刀具索引 {toolIndex} 超出范围！可用索引：0-{tools.Count - 1}");
            return;
        }

        if (tools[toolIndex] == null)
        {
            Debug.LogWarning($"刀具索引 {toolIndex} 为空！");
            return;
        }

        // 禁用当前刀具
        if (currentTool != null)
        {
            currentTool.SetActive(false);
            if (debugMode) Debug.Log($"已禁用刀具: {currentTool.toolName}");
        }

        // 启用新刀具
        currentTool = tools[toolIndex];
        currentToolIndex = toolIndex;
        currentTool.SetActive(true);

        if (debugMode) Debug.Log($"已切换到刀具: {currentTool.toolName} (索引: {toolIndex})");
    }

    /// <summary>
    /// 切换到下一个刀具（循环）
    /// </summary>
    public void SwitchToNextTool()
    {
        int nextIndex = (currentToolIndex + 1) % tools.Count;
        SwitchToTool(nextIndex);
    }

    /// <summary>
    /// 切换到上一个刀具（循环）
    /// </summary>
    public void SwitchToPreviousTool()
    {
        int previousIndex = (currentToolIndex - 1 + tools.Count) % tools.Count;
        SwitchToTool(previousIndex);
    }

    /// <summary>
    /// 通过名称切换刀具
    /// </summary>
    /// <param name="toolName">刀具名称</param>
    public void SwitchToToolByName(string toolName)
    {
        for (int i = 0; i < tools.Count; i++)
        {
            if (tools[i] != null && tools[i].toolName == toolName)
            {
                SwitchToTool(i);
                return;
            }
        }
        
        Debug.LogWarning($"未找到名为 '{toolName}' 的刀具！");
    }

    /// <summary>
    /// 获取当前激活的刀具
    /// </summary>
    public EndmillTool GetCurrentTool()
    {
        return currentTool;
    }

    // 用于测试的输入处理
    private void Update()
    {
        // 使用键盘数字键切换刀具（用于测试）
        if (Input.GetKeyDown(KeyCode.Alpha1)) SwitchToTool(0);
        if (Input.GetKeyDown(KeyCode.Alpha2)) SwitchToTool(1);
        if (Input.GetKeyDown(KeyCode.Alpha3)) SwitchToTool(2);
        
        // 使用左右箭头键切换
        if (Input.GetKeyDown(KeyCode.RightArrow)) SwitchToNextTool();
        if (Input.GetKeyDown(KeyCode.LeftArrow)) SwitchToPreviousTool();
    }
}
