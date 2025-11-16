using UnityEngine;

/// <summary>
/// 标识一个对象为工件，并设置其显示名称和位置调整功能
/// </summary>
public class WorkpieceTool : MonoBehaviour
{
    [Tooltip("工件的显示名称，用于调试和识别")]
    public string workpieceName = "Unnamed Workpiece";
    
    [Tooltip("工件的默认激活状态")]
    public bool isDefaultWorkpiece = false;

    // 用于防止位置被其他脚本重置的标志
    private bool isPositionLocked = false;
    private Vector3 lockedPosition;
    
    // 当脚本启用时调用
    private void Awake()
    {
        // 确保工件开始时处于正确的激活状态
        // 实际激活状态将由管理器统一控制
        gameObject.SetActive(false);
    }
    
    // 在LateUpdate中检查并保持位置（防止被其他脚本重置）
    private void LateUpdate()
    {
        // 如果位置被锁定，确保位置不被其他脚本改变
        if (isPositionLocked && transform != null)
        {
            // 检查位置是否被改变
            if (Vector3.Distance(transform.position, lockedPosition) > 0.001f)
            {
                Debug.LogWarning($"WorkpieceTool [{workpieceName}]: 检测到位置被其他脚本重置！从 {transform.position} 恢复到 {lockedPosition}");
                transform.position = lockedPosition;
            }
        }
    }

    /// <summary>
    /// 设置该工件的激活状态
    /// </summary>
    public void SetActive(bool active)
    {
        gameObject.SetActive(active);
    }
    
    /// <summary>
    /// 设置工件的位置（世界坐标）
    /// </summary>
    /// <param name="position">新的位置坐标（世界坐标）</param>
    public void SetPosition(Vector3 position)
    {
        if (transform != null)
        {
            Vector3 oldWorldPosition = transform.position;
            Vector3 oldLocalPosition = transform.localPosition;
            
            // 设置世界位置
            transform.position = position;
            
            Vector3 actualWorldPosition = transform.position;
            Vector3 actualLocalPosition = transform.localPosition;
            
            Debug.Log($"WorkpieceTool [{workpieceName}]: ===== 设置位置 =====");
            Debug.Log($"  GameObject名称: {gameObject.name}");
            Debug.Log($"  GameObject激活状态: {gameObject.activeSelf}");
            Debug.Log($"  旧世界位置: {oldWorldPosition}");
            Debug.Log($"  旧本地位置: {oldLocalPosition}");
            Debug.Log($"  设置的世界位置: {position}");
            Debug.Log($"  实际世界位置: {actualWorldPosition}");
            Debug.Log($"  实际本地位置: {actualLocalPosition}");
            
            if (transform.parent != null)
            {
                Debug.Log($"  Transform父对象: {transform.parent.name}");
                Debug.Log($"  父对象世界位置: {transform.parent.position}");
                Debug.Log($"  父对象本地位置: {transform.parent.localPosition}");
                Debug.Log($"  父对象旋转: {transform.parent.rotation.eulerAngles}");
                Debug.Log($"  父对象缩放: {transform.parent.localScale}");
            }
            else
            {
                Debug.Log($"  Transform父对象: 无");
            }
            
            // 检查位置是否真的改变了
            float positionChange = Vector3.Distance(oldWorldPosition, actualWorldPosition);
            Debug.Log($"  位置变化距离: {positionChange}");
            
            if (positionChange < 0.001f)
            {
                Debug.LogWarning($"WorkpieceTool [{workpieceName}]: 警告！位置似乎没有改变！");
            }
            else
            {
                Debug.Log($"WorkpieceTool [{workpieceName}]: ✓ 位置已成功改变！");
            }
        }
        else
        {
            Debug.LogError($"WorkpieceTool [{workpieceName}]: Transform为空，无法设置位置！");
        }
    }
    
    /// <summary>
    /// 设置工件的本地位置（相对于父对象）
    /// </summary>
    /// <param name="localPosition">新的本地位置坐标</param>
    public void SetLocalPosition(Vector3 localPosition)
    {
        if (transform != null)
        {
            Vector3 oldLocalPosition = transform.localPosition;
            transform.localPosition = localPosition;
            Vector3 actualLocalPosition = transform.localPosition;
            
            Debug.Log($"WorkpieceTool [{workpieceName}]: 设置本地位置");
            Debug.Log($"  旧本地位置: {oldLocalPosition}");
            Debug.Log($"  设置本地位置: {localPosition}");
            Debug.Log($"  实际本地位置: {actualLocalPosition}");
            Debug.Log($"  世界位置: {transform.position}");
        }
        else
        {
            Debug.LogError($"WorkpieceTool [{workpieceName}]: Transform为空，无法设置本地位置！");
        }
    }
    
    /// <summary>
    /// 移动工件到指定偏移位置（相对移动）
    /// 参考 FixtureTool 的实现，直接使用世界位置移动
    /// Unity 会自动处理父对象的影响
    /// </summary>
    /// <param name="offset">偏移量（世界空间）</param>
    public void MoveByOffset(Vector3 offset)
    {
        if (transform != null)
        {
            Vector3 oldPosition = transform.position;
            Vector3 oldLocalPosition = transform.localPosition;
            
            // 直接在世界空间中移动，Unity会自动处理父对象的影响
            // 这与 FixtureTool.MoveByOffset 的实现一致
            transform.position += offset;
            
            Vector3 newPosition = transform.position;
            Vector3 newLocalPosition = transform.localPosition;
            
            // 锁定新位置，防止被其他脚本重置
            isPositionLocked = true;
            lockedPosition = newPosition;
            
            Debug.Log($"WorkpieceTool [{workpieceName}]: ===== 相对移动 =====");
            Debug.Log($"  GameObject名称: {gameObject.name}");
            Debug.Log($"  旧世界位置: {oldPosition}");
            Debug.Log($"  旧本地位置: {oldLocalPosition}");
            Debug.Log($"  移动偏移: {offset}");
            Debug.Log($"  新世界位置: {newPosition}");
            Debug.Log($"  新本地位置: {newLocalPosition}");
            Debug.Log($"  位置已锁定: {isPositionLocked}");
            
            if (transform.parent != null)
            {
                Debug.Log($"  父对象: {transform.parent.name}");
                Debug.Log($"  父对象位置: {transform.parent.position}");
                Debug.Log($"  父对象旋转: {transform.parent.rotation.eulerAngles}");
            }
            
            float actualDistance = Vector3.Distance(oldPosition, newPosition);
            Debug.Log($"  实际移动距离: {actualDistance}");
            Debug.Log($"WorkpieceTool [{workpieceName}]: ✓ 移动完成");
            
            // 验证移动是否成功
            if (actualDistance < 0.001f)
            {
                Debug.LogWarning($"WorkpieceTool [{workpieceName}]: 警告！移动后位置没有变化！");
            }
        }
        else
        {
            Debug.LogError($"WorkpieceTool [{workpieceName}]: Transform为空，无法移动！");
        }
    }
    
    /// <summary>
    /// 解锁位置（允许其他脚本修改位置）
    /// </summary>
    public void UnlockPosition()
    {
        isPositionLocked = false;
        Debug.Log($"WorkpieceTool [{workpieceName}]: 位置已解锁");
    }
    
    /// <summary>
    /// 锁定当前位置
    /// </summary>
    public void LockPosition()
    {
        if (transform != null)
        {
            isPositionLocked = true;
            lockedPosition = transform.position;
            Debug.Log($"WorkpieceTool [{workpieceName}]: 位置已锁定在 {lockedPosition}");
        }
    }
    
    /// <summary>
    /// 获取当前工件的位置
    /// </summary>
    public Vector3 GetPosition()
    {
        return transform.position;
    }
}