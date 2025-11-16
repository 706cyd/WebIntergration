using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 管理所有夹具的切换，确保同时只激活一个夹具，并提供位置调整功能
/// </summary>
public class FixtureManager : MonoBehaviour
{
    [Header("夹具管理")]
    [Tooltip("所有可用的夹具列表")]
    public List<FixtureTool> fixtures = new List<FixtureTool>();
    
    [Tooltip("当前激活的夹具索引")]
    public int currentFixtureIndex = 0;
    
    [Header("调试")]
    [Tooltip("启用调试信息")]
    public bool debugMode = true;

    // 当前激活的夹具引用
    private FixtureTool currentFixture;

    // 单例模式，便于其他脚本访问
    public static FixtureManager Instance { get; private set; }

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
        
        InitializeFixtures();
    }

    /// <summary>
    /// 初始化所有夹具
    /// </summary>
    private void InitializeFixtures()
    {        
        if (fixtures.Count == 0)
        {            
            Debug.LogWarning("夹具列表为空！请将夹具添加到FixtureManager的fixtures列表中。");
            return;
        }

        // 首先禁用所有夹具
        foreach (FixtureTool fixture in fixtures)
        {            
            if (fixture != null)
            {                
                fixture.SetActive(false);
            }
        }

        // 查找默认夹具或使用第一个夹具
        int defaultIndex = FindDefaultFixtureIndex();
        
        // 激活默认夹具
        SwitchToFixture(defaultIndex);
    }

    /// <summary>
    /// 查找标记为默认的夹具
    /// </summary>
    private int FindDefaultFixtureIndex()
    {        
        for (int i = 0; i < fixtures.Count; i++)
        {            
            if (fixtures[i] != null && fixtures[i].isDefaultFixture)
            {                
                return i;
            }
        }
        
        // 如果没有找到默认夹具，使用第一个有效的夹具
        for (int i = 0; i < fixtures.Count; i++)
        {            
            if (fixtures[i] != null)
            {                
                return i;
            }
        }
        
        return 0;
    }

    /// <summary>
    /// 切换到指定索引的夹具
    /// </summary>
    /// <param name="fixtureIndex">夹具在列表中的索引</param>
    public void SwitchToFixture(int fixtureIndex)
    {        
        if (fixtures.Count == 0) return;
        
        // 检查索引是否有效
        if (fixtureIndex < 0 || fixtureIndex >= fixtures.Count)
        {            
            Debug.LogWarning($"夹具索引 {fixtureIndex} 超出范围！可用索引：0-{fixtures.Count - 1}");
            return;
        }

        if (fixtures[fixtureIndex] == null)
        {            
            Debug.LogWarning($"夹具索引 {fixtureIndex} 为空！");
            return;
        }

        // 禁用当前夹具
        if (currentFixture != null)
        {            
            currentFixture.SetActive(false);
            if (debugMode) Debug.Log($"已禁用夹具: {currentFixture.fixtureName}");
        }

        // 启用新夹具
        currentFixture = fixtures[fixtureIndex];
        currentFixtureIndex = fixtureIndex;
        currentFixture.SetActive(true);

        if (debugMode) Debug.Log($"已切换到夹具: {currentFixture.fixtureName} (索引: {fixtureIndex})");
    }

    /// <summary>
    /// 通过名称切换夹具
    /// </summary>
    /// <param name="fixtureName">夹具名称</param>
    public void SwitchToFixtureByName(string fixtureName)
    {        
        for (int i = 0; i < fixtures.Count; i++)
        {            
            if (fixtures[i] != null && fixtures[i].fixtureName == fixtureName)
            {                
                SwitchToFixture(i);
                return;
            }
        }
        
        Debug.LogWarning($"未找到名为 '{fixtureName}' 的夹具！");
    }

    /// <summary>
    /// 获取当前激活的夹具
    /// </summary>
    public FixtureTool GetCurrentFixture()
    {        
        return currentFixture;
    }

    /// <summary>
    /// 设置当前夹具的位置
    /// </summary>
    /// <param name="x">X坐标</param>
    /// <param name="y">Y坐标</param>
    /// <param name="z">Z坐标</param>
    public void SetCurrentFixturePosition(float x, float y, float z)
    {        
        if (currentFixture != null)
        {            
            Vector3 newPosition = new Vector3(x, y, z);
            currentFixture.SetPosition(newPosition);
            if (debugMode) Debug.Log($"FixtureManager: 设置夹具位置到 {newPosition}");
        }
        else
        {            
            Debug.LogWarning("FixtureManager: 没有活动的夹具！无法设置位置。");
        }
    }
    
    /// <summary>
    /// 获取当前夹具的位置
    /// </summary>
    public Vector3 GetCurrentFixturePosition()
    {        
        if (currentFixture != null)
        {            
            return currentFixture.GetPosition();
        }
        Debug.LogWarning("没有活动的夹具！");
        return Vector3.zero;
    }
    
    // 用于WebGL调用的方法
    public void WebGL_SetFixturePosition(string positionString)
    {        
        if (debugMode) Debug.Log($"FixtureManager: 收到WebGL位置设置请求: {positionString}");
        
        // 解析格式为 "x,y,z" 的字符串
        string[] positionParts = positionString.Split(',');
        if (positionParts.Length == 3)
        {            
            float xPos, yPos, zPos;
            if (float.TryParse(positionParts[0].Trim(), out xPos) && 
                float.TryParse(positionParts[1].Trim(), out yPos) && 
                float.TryParse(positionParts[2].Trim(), out zPos))
            {                
                SetCurrentFixturePosition(xPos, yPos, zPos);
                if (debugMode) Debug.Log($"FixtureManager: 从WebGL设置夹具位置成功: X={xPos}, Y={yPos}, Z={zPos}");
            }
            else
            {                
                Debug.LogWarning($"FixtureManager: 无效的坐标数值格式！无法解析: {positionString}");
            }
        }
        else
        {            
            Debug.LogWarning($"FixtureManager: 无效的坐标字符串格式！预期格式: x,y,z，收到: {positionString}");
        }
    }
    
    public void WebGL_SwitchToFixture(string index)
    {        
        if (debugMode) Debug.Log($"FixtureManager: 收到WebGL切换夹具请求: {index}");
        
        int fixtureIndex;
        if (int.TryParse(index, out fixtureIndex))
        {            
            SwitchToFixture(fixtureIndex);
            if (debugMode) Debug.Log($"FixtureManager: WebGL切换夹具成功，索引: {fixtureIndex}");
        }
        else
        {            
            Debug.LogWarning($"FixtureManager: 无效的夹具索引格式！无法解析: {index}");
        }
    }
}