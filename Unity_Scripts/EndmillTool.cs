using UnityEngine;

/// <summary>
/// 标识一个对象为刀具，并设置其显示名称
/// </summary>
public class EndmillTool : MonoBehaviour
{
    [Tooltip("刀具的显示名称，用于调试和识别")]
    public string toolName = "Unnamed Tool";
    
    [Tooltip("刀具的默认激活状态")]
    public bool isDefaultTool = false;

    // 当脚本启用时调用
    private void Awake()
    {
        // 确保刀具开始时处于正确的激活状态
        // 实际激活状态将由管理器统一控制
        gameObject.SetActive(false);
    }

    /// <summary>
    /// 设置该刀具的激活状态
    /// </summary>
    public void SetActive(bool active)
    {
        gameObject.SetActive(active);
    }
}