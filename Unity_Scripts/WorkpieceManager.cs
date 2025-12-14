using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 管理所有工件的切换，确保同时只激活一个工件，并提供位置调整功能
/// </summary>
public class WorkpieceManager : MonoBehaviour
{
    [Header("工件管理")]
    [Tooltip("所有可用的工件列表")]
    public List<WorkpieceTool> workpieces = new List<WorkpieceTool>();
    
    [Tooltip("当前激活的工件索引")]
    public int currentWorkpieceIndex = 0;
    
    [Header("调试")]
    [Tooltip("启用调试信息")]
    public bool debugMode = true;

    // 当前激活的工件引用
    private WorkpieceTool currentWorkpiece;

    // 单例模式，便于其他脚本访问
    public static WorkpieceManager Instance { get; private set; }

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
        
        InitializeWorkpieces();
    }

    /// <summary>
    /// 初始化所有工件
    /// </summary>
    private void InitializeWorkpieces()
    {        
        if (workpieces.Count == 0)
        {            
            Debug.LogWarning("工件列表为空！请将工件添加到WorkpieceManager的workpieces列表中。");
            return;
        }

        // 首先禁用所有工件
        foreach (WorkpieceTool workpiece in workpieces)
        {            
            if (workpiece != null)
            {                
                workpiece.SetActive(false);
            }
        }

        // 查找默认工件或使用第一个工件
        int defaultIndex = FindDefaultWorkpieceIndex();
        
        // 激活默认工件
        SwitchToWorkpiece(defaultIndex);
    }

    /// <summary>
    /// 查找标记为默认的工件
    /// </summary>
    private int FindDefaultWorkpieceIndex()
    {        
        for (int i = 0; i < workpieces.Count; i++)
        {            
            if (workpieces[i] != null && workpieces[i].isDefaultWorkpiece)
            {                
                return i;
            }
        }
        
        // 如果没有找到默认工件，使用第一个有效的工件
        for (int i = 0; i < workpieces.Count; i++)
        {            
            if (workpieces[i] != null)
            {                
                return i;
            }
        }
        
        return 0;
    }

    /// <summary>
    /// 切换到指定索引的工件
    /// </summary>
    /// <param name="workpieceIndex">工件在列表中的索引</param>
    public void SwitchToWorkpiece(int workpieceIndex)
    {        
        if (workpieces.Count == 0) return;
        
        // 检查索引是否有效
        if (workpieceIndex < 0 || workpieceIndex >= workpieces.Count)
        {            
            Debug.LogWarning($"工件索引 {workpieceIndex} 超出范围！可用索引：0-{workpieces.Count - 1}");
            return;
        }

        if (workpieces[workpieceIndex] == null)
        {            
            Debug.LogWarning($"工件索引 {workpieceIndex} 为空！");
            return;
        }

        // 禁用当前工件
        if (currentWorkpiece != null)
        {            
            currentWorkpiece.SetActive(false);
            if (debugMode) Debug.Log($"已禁用工件: {currentWorkpiece.workpieceName}");
        }

        // 启用新工件
        currentWorkpiece = workpieces[workpieceIndex];
        currentWorkpieceIndex = workpieceIndex;
        currentWorkpiece.SetActive(true);

        if (debugMode) Debug.Log($"已切换到工件: {currentWorkpiece.workpieceName} (索引: {workpieceIndex})");
    }

    /// <summary>
    /// 通过名称切换工件
    /// </summary>
    /// <param name="workpieceName">工件名称</param>
    public void SwitchToWorkpieceByName(string workpieceName)
    {        
        for (int i = 0; i < workpieces.Count; i++)
        {            
            if (workpieces[i] != null && workpieces[i].workpieceName == workpieceName)
            {                
                SwitchToWorkpiece(i);
                return;
            }
        }
        
        Debug.LogWarning($"未找到名为 '{workpieceName}' 的工件！");
    }

    /// <summary>
    /// 获取当前激活的工件
    /// </summary>
    public WorkpieceTool GetCurrentWorkpiece()
    {        
        return currentWorkpiece;
    }

    /// <summary>
    /// 设置当前工件的位置
    /// </summary>
    /// <param name="x">X坐标</param>
    /// <param name="y">Y坐标</param>
    /// <param name="z">Z坐标</param>
    public void SetCurrentWorkpiecePosition(float x, float y, float z)
    {        
        if (currentWorkpiece != null)
        {            
            Vector3 oldPosition = currentWorkpiece.GetPosition();
            Vector3 newPosition = new Vector3(x, y, z);
            
            if (debugMode) 
            {
                Debug.Log($"WorkpieceManager: 准备设置工件位置");
                Debug.Log($"  当前工件: {currentWorkpiece.workpieceName}");
                Debug.Log($"  旧位置: {oldPosition}");
                Debug.Log($"  新位置: {newPosition}");
            }
            
            currentWorkpiece.SetPosition(newPosition);
            
            // 等待一帧，确保位置设置生效
            Vector3 actualPosition = currentWorkpiece.GetPosition();
            if (debugMode) 
            {
                Debug.Log($"WorkpieceManager: 位置设置完成，实际位置: {actualPosition}");
                Debug.Log($"WorkpieceManager: 位置差异: {Vector3.Distance(newPosition, actualPosition)}");
            }
            
            // 验证位置是否真的改变了
            if (Vector3.Distance(oldPosition, actualPosition) < 0.001f)
            {
                Debug.LogWarning($"WorkpieceManager: 警告！位置设置后没有变化！可能是被其他脚本重置了。");
            }
        }
        else
        {            
            Debug.LogWarning("WorkpieceManager: 没有活动的工件！无法设置位置。");
            Debug.LogWarning($"WorkpieceManager: 当前工件索引: {currentWorkpieceIndex}, 工件列表数量: {workpieces.Count}");
        }
    }
    
    /// <summary>
    /// 获取当前工件的位置
    /// </summary>
    public Vector3 GetCurrentWorkpiecePosition()
    {        
        if (currentWorkpiece != null)
        {            
            return currentWorkpiece.GetPosition();
        }
        Debug.LogWarning("没有活动的工件！");
        return Vector3.zero;
    }
    
    /// <summary>
    /// 移动当前工件（相对移动）
    /// </summary>
    /// <param name="offsetX">X轴偏移量</param>
    /// <param name="offsetY">Y轴偏移量</param>
    /// <param name="offsetZ">Z轴偏移量</param>
    public void MoveCurrentWorkpiece(float offsetX, float offsetY, float offsetZ)
    {
        if (currentWorkpiece != null)
        {
            Vector3 oldPosition = currentWorkpiece.GetPosition();
            Vector3 offset = new Vector3(offsetX, offsetY, offsetZ);
            
            if (debugMode)
            {
                Debug.Log($"WorkpieceManager: 准备移动工件");
                Debug.Log($"  当前工件: {currentWorkpiece.workpieceName}");
                Debug.Log($"  当前位置: {oldPosition}");
                Debug.Log($"  移动偏移: {offset}");
            }
            
            currentWorkpiece.MoveByOffset(offset);
            
            Vector3 newPosition = currentWorkpiece.GetPosition();
            if (debugMode)
            {
                Debug.Log($"WorkpieceManager: 移动完成，新位置: {newPosition}");
                Debug.Log($"WorkpieceManager: 实际移动距离: {Vector3.Distance(oldPosition, newPosition)}");
            }
        }
        else
        {
            Debug.LogWarning("WorkpieceManager: 没有活动的工件！无法移动。");
            Debug.LogWarning($"WorkpieceManager: 当前工件索引: {currentWorkpieceIndex}, 工件列表数量: {workpieces.Count}");
        }
    }
    
    /// <summary>
    /// 旋转当前工件（相对旋转）
    /// </summary>
    /// <param name="rotationX">X轴旋转角度</param>
    /// <param name="rotationY">Y轴旋转角度</param>
    /// <param name="rotationZ">Z轴旋转角度</param>
    public void RotateCurrentWorkpiece(float rotationX, float rotationY, float rotationZ)
    {
        if (currentWorkpiece != null)
        {
            Vector3 rotationOffset = new Vector3(rotationX, rotationY, rotationZ);
            
            if (debugMode)
            {
                Debug.Log($"WorkpieceManager: 准备旋转工件");
                Debug.Log($"  当前工件: {currentWorkpiece.workpieceName}");
                Debug.Log($"  旋转偏移: {rotationOffset}");
            }
            
            currentWorkpiece.RotateByOffset(rotationOffset);
            
            if (debugMode)
            {
                Debug.Log($"WorkpieceManager: 旋转完成");
            }
        }
        else
        {
            Debug.LogWarning("WorkpieceManager: 没有活动的工件！无法旋转。");
            Debug.LogWarning($"WorkpieceManager: 当前工件索引: {currentWorkpieceIndex}, 工件列表数量: {workpieces.Count}");
        }
    }
    
    // 用于WebGL调用的方法
    public void WebGL_SetWorkpiecePosition(string positionString)
    {
        Debug.Log($"WorkpieceManager: ===== 收到WebGL位置设置请求 =====");
        Debug.Log($"WorkpieceManager: 接收到的字符串: '{positionString}'");
        Debug.Log($"WorkpieceManager: 当前工件索引: {currentWorkpieceIndex}");
        Debug.Log($"WorkpieceManager: 工件列表数量: {workpieces.Count}");
        Debug.Log($"WorkpieceManager: 当前工件对象: {(currentWorkpiece != null ? currentWorkpiece.workpieceName : "NULL")}");
        
        // 解析格式为 "x,y,z" 的字符串
        string[] positionParts = positionString.Split(',');
        Debug.Log($"WorkpieceManager: 分割后的部分数量: {positionParts.Length}");
        
        if (positionParts.Length == 3)
        {
            float xPos, yPos, zPos;
            bool xOk = float.TryParse(positionParts[0].Trim(), out xPos);
            bool yOk = float.TryParse(positionParts[1].Trim(), out yPos);
            bool zOk = float.TryParse(positionParts[2].Trim(), out zPos);
            
            Debug.Log($"WorkpieceManager: 解析结果 - X: {xPos} (成功: {xOk}), Y: {yPos} (成功: {yOk}), Z: {zPos} (成功: {zOk})");
            
            if (xOk && yOk && zOk)
            {
                SetCurrentWorkpiecePosition(xPos, yPos, zPos);
                Debug.Log($"WorkpieceManager: ===== 从WebGL设置工件位置完成 =====");
            }
            else
            {
                Debug.LogWarning($"WorkpieceManager: 无效的坐标数值格式！无法解析: {positionString}");
                Debug.LogWarning($"WorkpieceManager: X解析: {xOk}, Y解析: {yOk}, Z解析: {zOk}");
            }
        }
        else
        {
            Debug.LogWarning($"WorkpieceManager: 无效的坐标字符串格式！预期格式: x,y,z，收到: {positionString}");
            Debug.LogWarning($"WorkpieceManager: 分割后的部分: [{string.Join(", ", positionParts)}]");
        }
    }
    
    public void WebGL_SwitchToWorkpiece(string index)
    {
        if (debugMode) Debug.Log($"WorkpieceManager: 收到WebGL切换工件请求: {index}");
        
        int workpieceIndex;
        if (int.TryParse(index, out workpieceIndex))
        {
            SwitchToWorkpiece(workpieceIndex);
            if (debugMode) Debug.Log($"WorkpieceManager: WebGL切换工件成功，索引: {workpieceIndex}");
        }
        else
        {
            Debug.LogWarning($"WorkpieceManager: 无效的工件索引格式！无法解析: {index}");
        }
    }
    
    // 用于WebGL调用的移动方法
    public void WebGL_MoveWorkpiece(string offsetString)
    {
        if (debugMode) Debug.Log($"WorkpieceManager: 收到WebGL移动工件请求: {offsetString}");
        
        // 解析格式为 "x,y,z" 的字符串
        string[] offsetParts = offsetString.Split(',');
        if (offsetParts.Length == 3)
        {
            float offsetX, offsetY, offsetZ;
            if (float.TryParse(offsetParts[0].Trim(), out offsetX) && 
                float.TryParse(offsetParts[1].Trim(), out offsetY) && 
                float.TryParse(offsetParts[2].Trim(), out offsetZ))
            {
                MoveCurrentWorkpiece(offsetX, offsetY, offsetZ);
                if (debugMode) Debug.Log($"WorkpieceManager: 从WebGL移动工件成功: X偏移={offsetX}, Y偏移={offsetY}, Z偏移={offsetZ}");
            }
            else
            {
                Debug.LogWarning($"WorkpieceManager: 无效的偏移量数值格式！无法解析: {offsetString}");
            }
        }
        else
        {
            Debug.LogWarning($"WorkpieceManager: 无效的偏移量字符串格式！预期格式: x,y,z，收到: {offsetString}");
        }
    }
    
    // 用于WebGL调用的旋转方法
    public void WebGL_RotateWorkpiece(string rotationString)
    {
        if (debugMode) Debug.Log($"WorkpieceManager: 收到WebGL旋转工件请求: {rotationString}");
        
        // 解析格式为 "x,y,z" 的字符串
        string[] rotationParts = rotationString.Split(',');
        if (rotationParts.Length == 3)
        {
            float rotationX, rotationY, rotationZ;
            if (float.TryParse(rotationParts[0].Trim(), out rotationX) && 
                float.TryParse(rotationParts[1].Trim(), out rotationY) && 
                float.TryParse(rotationParts[2].Trim(), out rotationZ))
            {
                RotateCurrentWorkpiece(rotationX, rotationY, rotationZ);
                if (debugMode) Debug.Log($"WorkpieceManager: 从WebGL旋转工件成功: X旋转={rotationX}, Y旋转={rotationY}, Z旋转={rotationZ}");
            }
            else
            {
                Debug.LogWarning($"WorkpieceManager: 无效的旋转角度数值格式！无法解析: {rotationString}");
            }
        }
        else
        {
            Debug.LogWarning($"WorkpieceManager: 无效的旋转角度字符串格式！预期格式: x,y,z，收到: {rotationString}");
        }
    }
}