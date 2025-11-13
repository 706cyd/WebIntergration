using MeshVoxelizerProject;
using UnityEngine;

public class MillingManager : MonoBehaviour
{
    [Header("Control")]
    public bool isOn = false;
    public Transform cutter;              // 刀具，以 position 为圆柱中心，up 为刀具主方向（旋转轴）
    [Header("Cutter")]
    public float cutterRadius = 0.5f;     // 圆柱半径 R
    public float cutterHeight = 1.0f;     // 圆柱总高度 -> 实际 H = height/2
    public bool drawDebugGizmos = false;  // 可视化一下调试AABB框选项

    [Header("Voxel System")]
    public VoxelizerDemo voxelizerDemo;   // 体素化器的演示脚本

    [Header("Optimization")]
    public float meshUpdateInterval = 0.1f;

    [Header("Precision Settings")]
    public bool enablePrecisionMode = true; // WebGL精度模式
    public float coordinateTolerance = 0.001f; // 坐标容差

    // 常量
    private const int LINE_AABB_ITERATIONS = 3;
    private const float DISTANCE_EPSILON = 1e-10f;

    // 状态变量
    private Vector3 worldMin;
    private Vector3 worldSize;
    private Vector3 voxelSize;
    private int size;
    private float updateTimer;
    private bool isInitialized = false;

    // 调试统计
    private int totalVoxelTests = 0;
    private int successfulCuts = 0;
    private int conversionErrors = 0;

    private void Start()
    {
        InitializeVoxelSystem();
    }

    /// <summary>
    /// 初始化体素系统
    /// </summary>
    private void InitializeVoxelSystem()
    {
        if (voxelizerDemo == null || voxelizerDemo.m_voxelizer == null)
        {
            Debug.LogError("VoxelizerDemo 或 m_voxelizer 未分配！");
            return;
        }

        size = voxelizerDemo.size;

        // 获取工件网格的世界空间AABB
        MeshFilter filter = voxelizerDemo.GetComponentInChildren<MeshFilter>();
        if (filter == null)
        {
            Debug.LogError("未找到MeshFilter组件！");
            return;
        }

        CalculateWorkpieceBounds(filter);
        isInitialized = true;

        Debug.Log($"体素系统初始化完成: 尺寸={size}, 世界范围=[{worldMin} ~ {worldMin + worldSize}]");
    }

    /// <summary>
    /// 计算工件的世界空间边界
    /// </summary>
    private void CalculateWorkpieceBounds(MeshFilter filter)
    {
        var localBounds = filter.sharedMesh.bounds;
        Vector3[] localCorners = new Vector3[]
        {
            new Vector3(localBounds.min.x, localBounds.min.y, localBounds.min.z),
            new Vector3(localBounds.max.x, localBounds.min.y, localBounds.min.z),
            new Vector3(localBounds.min.x, localBounds.max.y, localBounds.min.z),
            new Vector3(localBounds.max.x, localBounds.max.y, localBounds.min.z),
            new Vector3(localBounds.min.x, localBounds.min.y, localBounds.max.z),
            new Vector3(localBounds.max.x, localBounds.min.y, localBounds.max.z),
            new Vector3(localBounds.min.x, localBounds.max.y, localBounds.max.z),
            new Vector3(localBounds.max.x, localBounds.max.y, localBounds.max.z),
        };

        Vector3 wmin = new Vector3(float.PositiveInfinity, float.PositiveInfinity, float.PositiveInfinity);
        Vector3 wmax = new Vector3(float.NegativeInfinity, float.NegativeInfinity, float.NegativeInfinity);

        for (int i = 0; i < 8; i++)
        {
            Vector3 worldCorner = filter.transform.TransformPoint(localCorners[i]);
            wmin = Vector3.Min(wmin, worldCorner);
            wmax = Vector3.Max(wmax, worldCorner);
        }

        worldMin = wmin;
        worldSize = wmax - wmin;
        voxelSize = new Vector3(worldSize.x / size, worldSize.y / size, worldSize.z / size);

        Debug.Log($"工件边界计算: Min={worldMin}, Max={wmax}, Size={worldSize}, VoxelSize={voxelSize}");
    }

    private void Update()
    {
        if (!isOn || !isInitialized || cutter == null) return;

        // 验证关键坐标转换
        if (Time.frameCount % 120 == 0) // 每2秒验证一次
        {
            ValidateCoordinateSystem();
        }

        PerformMillingOperation();
    }

    /// <summary>
    /// 验证坐标系转换准确性
    /// </summary>
    private void ValidateCoordinateSystem()
    {
        Debug.Log("=== 坐标系验证 ===");
        Debug.Log($"刀具世界坐标: {cutter.position}");
        Debug.Log($"工件世界Min: {worldMin}");
        Debug.Log($"体素尺寸: {voxelSize}");

        // 测试几个关键点的转换
        Vector3[] testPoints = new Vector3[]
        {
            cutter.position,
            worldMin,
            worldMin + worldSize * 0.5f,
            worldMin + worldSize
        };

        foreach (Vector3 point in testPoints)
        {
            if (WorldToVoxelCoordinate(point, out Vector3Int voxelCoord, out string error))
            {
                Vector3 reconstructedWorld = VoxelToWorldCoordinate(voxelCoord);
                float errorDistance = Vector3.Distance(point, reconstructedWorld);
                Debug.Log($"点{point} -> 体素{voxelCoord} -> 重建世界{reconstructedWorld}, 误差: {errorDistance:F6}");

                if (errorDistance > coordinateTolerance)
                {
                    Debug.LogWarning($"坐标转换误差较大: {errorDistance}");
                }
            }
            else
            {
                Debug.LogWarning($"坐标转换失败: {point} - {error}");
            }
        }
        Debug.Log($"统计: 总测试{totalVoxelTests}, 成功切削{successfulCuts}, 转换错误{conversionErrors}");
        Debug.Log("=== 验证结束 ===");
    }

    /// <summary>
    /// 执行铣削操作
    /// </summary>
    private void PerformMillingOperation()
    {
        int[,,] voxels = voxelizerDemo.m_voxelizer.Voxels;
        if (voxels == null || size <= 0) return;

        float halfHeight = cutterHeight * 0.5f;
        float radius = cutterRadius;
        Vector3 cutterCenter = cutter.position;
        Vector3 cutterDirection = cutter.up.normalized;

        // 计算刀具的AABB用于剪枝
        CalculateCutterAABB(cutterCenter, cutterDirection, radius, halfHeight, 
            out Vector3 aabbMin, out Vector3 aabbMax);

        // 转换到体素坐标范围
        if (!WorldAABBToVoxelRange(aabbMin, aabbMax, 
            out int ixMin, out int iyMin, out int izMin, 
            out int ixMax, out int iyMax, out int izMax))
        {
            return; // 转换失败或无交集
        }

        bool modified = false;
        totalVoxelTests = 0;
        successfulCuts = 0;

        // 遍历剪枝后的体素范围
        for (int z = izMin; z <= izMax; z++)
        {
            for (int y = iyMin; y <= iyMax; y++)
            {
                for (int x = ixMin; x <= ixMax; x++)
                {
                    totalVoxelTests++;

                    // 安全检查
                    if (!IsVoxelIndexValid(x, y, z) || voxels[x, y, z] == 0)
                        continue;

                    // 获取体素的世界空间AABB
                    if (!GetVoxelWorldAABB(x, y, z, out Vector3 vmin, out Vector3 vmax))
                    {
                        conversionErrors++;
                        continue;
                    }

                    // 碰撞检测：圆柱体 vs 体素AABB
                    if (CheckCylinderVoxelCollision(cutterCenter, cutterDirection, radius, halfHeight, vmin, vmax))
                    {
                        try
                        {
                            voxels[x, y, z] = 0;
                            modified = true;
                            successfulCuts++;
                        }
                        catch (System.Exception e)
                        {
                            Debug.LogError($"体素写入异常: ({x},{y},{z}) - {e.Message}");
                        }
                    }
                }
            }
        }

        // 需要时更新网格
        if (modified)
        {
            updateTimer += Time.deltaTime;
            if (updateTimer >= meshUpdateInterval)
            {
                voxelizerDemo.GenerateVoxelMesh();
                updateTimer = 0f;
            }
        }
    }

    /// <summary>
    /// 世界坐标转换为体素坐标（高精度版本）
    /// </summary>
    private bool WorldToVoxelCoordinate(Vector3 worldPos, out Vector3Int voxelCoord, out string error)
    {
        voxelCoord = Vector3Int.zero;
        error = null;

        // 检查是否在工件范围内
        if (worldPos.x < worldMin.x - coordinateTolerance || worldPos.x > worldMin.x + worldSize.x + coordinateTolerance ||
            worldPos.y < worldMin.y - coordinateTolerance || worldPos.y > worldMin.y + worldSize.y + coordinateTolerance ||
            worldPos.z < worldMin.z - coordinateTolerance || worldPos.z > worldMin.z + worldSize.z + coordinateTolerance)
        {
            error = "坐标超出工件范围";
            return false;
        }

        try
        {
            // 使用更精确的转换方法
            Vector3 localPos = worldPos - worldMin;
            
            if (enablePrecisionMode)
            {
                // WebGL精度模式：使用更稳定的计算方法
                voxelCoord.x = Mathf.Clamp(Mathf.FloorToInt(localPos.x / voxelSize.x + 0.0001f), 0, size - 1);
                voxelCoord.y = Mathf.Clamp(Mathf.FloorToInt(localPos.y / voxelSize.y + 0.0001f), 0, size - 1);
                voxelCoord.z = Mathf.Clamp(Mathf.FloorToInt(localPos.z / voxelSize.z + 0.0001f), 0, size - 1);
            }
            else
            {
                // 标准模式
                voxelCoord.x = Mathf.Clamp(Mathf.FloorToInt(localPos.x / voxelSize.x), 0, size - 1);
                voxelCoord.y = Mathf.Clamp(Mathf.FloorToInt(localPos.y / voxelSize.y), 0, size - 1);
                voxelCoord.z = Mathf.Clamp(Mathf.FloorToInt(localPos.z / voxelSize.z), 0, size - 1);
            }

            return true;
        }
        catch (System.Exception e)
        {
            error = $"转换异常: {e.Message}";
            return false;
        }
    }

    /// <summary>
    /// 体素坐标转换回世界坐标（用于验证）
    /// </summary>
    private Vector3 VoxelToWorldCoordinate(Vector3Int voxelCoord)
    {
        Vector3 localPos = new Vector3(
            (voxelCoord.x + 0.5f) * voxelSize.x,  // 使用体素中心点
            (voxelCoord.y + 0.5f) * voxelSize.y,
            (voxelCoord.z + 0.5f) * voxelSize.z
        );
        return worldMin + localPos;
    }

    /// <summary>
    /// 世界空间AABB转换为体素索引范围
    /// </summary>
    private bool WorldAABBToVoxelRange(Vector3 worldMinAABB, Vector3 worldMaxAABB,
        out int xMin, out int yMin, out int zMin, out int xMax, out int yMax, out int zMax)
    {
        xMin = yMin = zMin = 0;
        xMax = yMax = zMax = 0;

        string minError = null;
        string maxError = null;
        
        if (!WorldToVoxelCoordinate(worldMinAABB, out Vector3Int minCoord, out minError) ||
            !WorldToVoxelCoordinate(worldMaxAABB, out Vector3Int maxCoord, out maxError))
        {
            Debug.LogWarning($"AABB转换失败: MinError={minError}, MaxError={maxError}");
            return false;
        }

        // 扩展1个体素以确保边界情况
        xMin = Mathf.Clamp(minCoord.x - 1, 0, size - 1);
        yMin = Mathf.Clamp(minCoord.y - 1, 0, size - 1);
        zMin = Mathf.Clamp(minCoord.z - 1, 0, size - 1);
        xMax = Mathf.Clamp(maxCoord.x + 1, 0, size - 1);
        yMax = Mathf.Clamp(maxCoord.y + 1, 0, size - 1);
        zMax = Mathf.Clamp(maxCoord.z + 1, 0, size - 1);

        return true;
    }

    /// <summary>
    /// 计算刀具的包围盒AABB
    /// </summary>
    private void CalculateCutterAABB(Vector3 center, Vector3 direction, float radius, float halfHeight,
        out Vector3 aabbMin, out Vector3 aabbMax)
    {
        Vector3 ext = new Vector3(
            radius * Mathf.Sqrt(Mathf.Max(0f, 1f - direction.x * direction.x)) + halfHeight * Mathf.Abs(direction.x),
            radius * Mathf.Sqrt(Mathf.Max(0f, 1f - direction.y * direction.y)) + halfHeight * Mathf.Abs(direction.y),
            radius * Mathf.Sqrt(Mathf.Max(0f, 1f - direction.z * direction.z)) + halfHeight * Mathf.Abs(direction.z)
        );

        aabbMin = center - ext;
        aabbMax = center + ext;
    }

    /// <summary>
    /// 获取体素的世界空间AABB
    /// </summary>
    private bool GetVoxelWorldAABB(int x, int y, int z, out Vector3 vmin, out Vector3 vmax)
    {
        vmin = worldMin + new Vector3(x * voxelSize.x, y * voxelSize.y, z * voxelSize.z);
        vmax = vmin + voxelSize;
        return true;
    }

    /// <summary>
    /// 检查圆柱体与体素AABB的碰撞
    /// </summary>
    private bool CheckCylinderVoxelCollision(Vector3 C, Vector3 N, float R, float H, Vector3 vmin, Vector3 vmax)
    {
        Vector3 bCenter = (vmin + vmax) * 0.5f;
        Vector3 bHalf = (vmax - vmin) * 0.5f;

        // 高度方向投影检测
        float projCenter = Vector3.Dot(N, bCenter - C);
        float projRadius = Mathf.Abs(N.x) * bHalf.x + Mathf.Abs(N.y) * bHalf.y + Mathf.Abs(N.z) * bHalf.z;
        
        if (Mathf.Abs(projCenter) > (H + projRadius))
            return false;

        // 距离检测
        float sqrDist = SqrDistanceLineAABB(C, N, vmin, vmax);
        return sqrDist <= R * R;
    }

    /// <summary>
    /// 验证体素索引是否有效
    /// </summary>
    private bool IsVoxelIndexValid(int x, int y, int z)
    {
        return x >= 0 && x < size && y >= 0 && y < size && z >= 0 && z < size;
    }

    /// <summary>
    /// 计算直线与AABB的最短距离平方
    /// </summary>
    private static float SqrDistanceLineAABB(Vector3 linePoint, Vector3 lineDir, Vector3 aabbMin, Vector3 aabbMax)
    {
        Vector3 p = new Vector3(
            Mathf.Clamp(linePoint.x, aabbMin.x, aabbMax.x),
            Mathf.Clamp(linePoint.y, aabbMin.y, aabbMax.y),
            Mathf.Clamp(linePoint.z, aabbMin.z, aabbMax.z)
        );

        float t = Vector3.Dot(lineDir, p - linePoint);
        Vector3 q = linePoint + lineDir * t;

        for (int i = 0; i < LINE_AABB_ITERATIONS; i++)
        {
            p = new Vector3(
                Mathf.Clamp(q.x, aabbMin.x, aabbMax.x),
                Mathf.Clamp(q.y, aabbMin.y, aabbMax.y),
                Mathf.Clamp(q.z, aabbMin.z, aabbMax.z)
            );
            t = Vector3.Dot(lineDir, p - linePoint);
            q = linePoint + lineDir * t;

            if ((p - q).sqrMagnitude < DISTANCE_EPSILON)
                break;
        }

        return (q - p).sqrMagnitude;
    }

#if UNITY_EDITOR
    private void OnDrawGizmos()
    {
        if (!drawDebugGizmos || cutter == null || !isInitialized) return;

        float halfHeight = cutterHeight * 0.5f;
        float radius = cutterRadius;
        Vector3 center = cutter.position;
        Vector3 direction = cutter.up.normalized;

        CalculateCutterAABB(center, direction, radius, halfHeight, out Vector3 aabbMin, out Vector3 aabbMax);

        // 绘制刀具AABB
        Gizmos.color = Color.cyan;
        Vector3 aabbCenter = (aabbMin + aabbMax) * 0.5f;
        Vector3 aabbSize = aabbMax - aabbMin;
        Gizmos.DrawWireCube(aabbCenter, aabbSize);

        // 绘制工件边界
        Gizmos.color = Color.yellow;
        Gizmos.DrawWireCube(worldMin + worldSize * 0.5f, worldSize);
    }
#endif
}
