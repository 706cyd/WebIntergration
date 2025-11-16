using UnityEngine;

/// <summary>
/// 标识一个对象为夹具，并设置其显示名称和位置调整功能
/// </summary>
public class FixtureTool : MonoBehaviour
{
    [Tooltip("夹具的显示名称，用于调试和识别")]
    public string fixtureName = "Unnamed Fixture";
    
    [Tooltip("夹具的默认激活状态")]
    public bool isDefaultFixture = false;

    // 当脚本启用时调用
    private void Awake()
    {
        // 确保夹具开始时处于正确的激活状态
        // 实际激活状态将由管理器统一控制
        gameObject.SetActive(false);
    }

    /// <summary>
    /// 设置该夹具的激活状态
    /// </summary>
    public void SetActive(bool active)
    {
        gameObject.SetActive(active);
    }
    
    /// <summary>
    /// 设置夹具的位置
    /// </summary>
    /// <param name="position">新的位置坐标</param>
    public void SetPosition(Vector3 position)
    {
        if (transform != null)
        {
            transform.position = position;
            Debug.Log($"FixtureTool [{fixtureName}]: 位置已设置为: {position}");
        }
        else
        {
            Debug.LogError($"FixtureTool [{fixtureName}]: Transform为空，无法设置位置！");
        }
    }
    
    /// <summary>
    /// 移动夹具到指定偏移位置
    /// </summary>
    /// <param name="offset">偏移量</param>
    public void MoveByOffset(Vector3 offset)
    {
        transform.position += offset;
        Debug.Log($"夹具 {fixtureName} 已移动偏移量: {offset}，当前位置: {transform.position}");
    }
    
    /// <summary>
    /// 获取当前夹具的位置
    /// </summary>
    public Vector3 GetPosition()
    {
        return transform.position;
    }
}