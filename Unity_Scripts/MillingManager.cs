using MeshVoxelizerProject;
using UnityEngine;

public class MillingManager : MonoBehaviour
{
    [Header("Control")]
    public bool isOn = false;
    public Transform cutter;              // ���ߣ��� position ΪԲ�����ģ�up Ϊ����֧��������ת��
    [Header("Cutter")]
    public float cutterRadius = 0.5f;     // Բ���뾶 R
    public float cutterHeight = 1.0f;     // Բ���ܸ߶� -> ��� H = height/2
    public bool drawDebugGizmos = false;  // ���ӻ�һ�´���AABB����ѡ��

    [Header("Voxel System")]
    public VoxelizerDemo voxelizerDemo;   // ���ػ����ƽű�

    [Header("Optimization")]
    public float meshUpdateInterval = 0.1f;

    // ����
    private Vector3 worldMin;
    private Vector3 worldSize;
    private Vector3 voxelSize;
    private int size;
    private float updateTimer;

    private void Start()
    {
        if (voxelizerDemo == null || voxelizerDemo.m_voxelizer == null) return;

        size = voxelizerDemo.size;

        // ���� ����ԭʼ�����ڡ��������ꡱ�µ� AABB�����ף��任8���ǵ�����min/max��
        MeshFilter filter = voxelizerDemo.GetComponentInChildren<MeshFilter>();
        if (filter == null) return;

        var lb = filter.sharedMesh.bounds; // �ֲ�
        Vector3[] localCorners = new Vector3[]
        {
            new Vector3(lb.min.x, lb.min.y, lb.min.z),
            new Vector3(lb.max.x, lb.min.y, lb.min.z),
            new Vector3(lb.min.x, lb.max.y, lb.min.z),
            new Vector3(lb.max.x, lb.max.y, lb.min.z),
            new Vector3(lb.min.x, lb.min.y, lb.max.z),
            new Vector3(lb.max.x, lb.min.y, lb.max.z),
            new Vector3(lb.min.x, lb.max.y, lb.max.z),
            new Vector3(lb.max.x, lb.max.y, lb.max.z),
        };

        Vector3 wmin = new Vector3(float.PositiveInfinity, float.PositiveInfinity, float.PositiveInfinity);
        Vector3 wmax = new Vector3(float.NegativeInfinity, float.NegativeInfinity, float.NegativeInfinity);
        for (int i = 0; i < 8; i++)
        {
            Vector3 w = filter.transform.TransformPoint(localCorners[i]);
            wmin = Vector3.Min(wmin, w);
            wmax = Vector3.Max(wmax, w);
        }

        worldMin = wmin;
        worldSize = wmax - wmin;
        voxelSize = new Vector3(worldSize.x / size, worldSize.y / size, worldSize.z / size);
    }

    private void Update()
    {
        if (!isOn || voxelizerDemo == null || voxelizerDemo.m_voxelizer == null || cutter == null) return;

        //Debug.Log($"Cutter世界坐标: {cutter.position}");
        //Debug.Log($"Workpiece世界Min: {worldMin}");
        //Debug.Log($"Workpiece世界Size: {worldSize}");
        //Debug.Log($"VoxelSize: {voxelSize}");

        int[,,] voxels = voxelizerDemo.m_voxelizer.Voxels;
        float H = cutterHeight * 0.5f;
        float R = cutterRadius;
        //Vector3 C = cutter.position;          // Բ�����ģ����磩
        //Vector3 N = cutter.up.normalized;     // Բ���������磬������̬��

        Vector3 C = cutter.position;          // 刀具中心（世界坐标）
        Vector3 N = cutter.up.normalized;     // 刀具方向（世界坐标，经过归一化）

        // 调试输出：对比Unity编辑器和WebGL的坐标值（用于定位位置偏移问题）
        #if UNITY_EDITOR || UNITY_WEBGL
        if (Time.frameCount % 60 == 0) // 每60帧输出一次，避免日志过多
        {
            Debug.Log($"[MillingManager坐标调试] Cutter世界坐标: {C}, Workpiece世界Min: {worldMin}, Workpiece世界Size: {worldSize}, VoxelSize: {voxelSize}");
        }
        #endif

        // 步骤 1) 刀具的"包围盒" AABB计算，用于剪枝范围

        // ���� 1) ���ߵġ����� AABB������������Χ��֦
        Vector3 ext; // ��ߴ�
        ext.x = R * Mathf.Sqrt(Mathf.Max(0f, 1f - N.x * N.x)) + H * Mathf.Abs(N.x);
        ext.y = R * Mathf.Sqrt(Mathf.Max(0f, 1f - N.y * N.y)) + H * Mathf.Abs(N.y);
        ext.z = R * Mathf.Sqrt(Mathf.Max(0f, 1f - N.z * N.z)) + H * Mathf.Abs(N.z);
        Vector3 cutterAabbMin = C - ext;
        Vector3 cutterAabbMax = C + ext;

        // ת������������Χ
        int ixMin = Mathf.FloorToInt((cutterAabbMin.x - worldMin.x) / voxelSize.x);
        int iyMin = Mathf.FloorToInt((cutterAabbMin.y - worldMin.y) / voxelSize.y);
        int izMin = Mathf.FloorToInt((cutterAabbMin.z - worldMin.z) / voxelSize.z);
        int ixMax = Mathf.FloorToInt((cutterAabbMax.x - worldMin.x) / voxelSize.x);
        int iyMax = Mathf.FloorToInt((cutterAabbMax.y - worldMin.y) / voxelSize.y);
        int izMax = Mathf.FloorToInt((cutterAabbMax.z - worldMin.z) / voxelSize.z);

        ixMin = Mathf.Clamp(ixMin, 0, size - 1);
        iyMin = Mathf.Clamp(iyMin, 0, size - 1);
        izMin = Mathf.Clamp(izMin, 0, size - 1);
        ixMax = Mathf.Clamp(ixMax, 0, size - 1);
        iyMax = Mathf.Clamp(iyMax, 0, size - 1);
        izMax = Mathf.Clamp(izMax, 0, size - 1);

        bool modified = false;

        // WebGL内存安全：确保所有索引都在有效范围内
        if (voxels == null || size <= 0) return;

        // ���� 2) ������֦��Χ�ڵ����أ�����ƽͷԲ�� vs AABB�������׶��ж�
        for (int z = izMin; z <= izMax; z++)
        {
            for (int y = iyMin; y <= iyMax; y++)
            {
                for (int x = ixMin; x <= ixMax; x++)
                {
                    //if (voxels[x, y, z] == 0) continue; 
                    // 双重边界检查：防止WebGL内存越界
                    if (x < 0 || x >= size || y < 0 || y >= size || z < 0 || z >= size) 
                    {
                        continue;
                    }

                    try
                    {
                        if (voxels[x, y, z] == 0) continue;
                    }
                    catch (System.Exception e)
                    {
                        Debug.LogError($"Voxel访问异常: x={x}, y={y}, z={z}, size={size}, 错误: {e.Message}");
                        continue;
                    }

                    // ��ǰ���ص�����AABB
                    Vector3 vmin = worldMin + new Vector3(x * voxelSize.x, y * voxelSize.y, z * voxelSize.z);
                    Vector3 vmax = vmin + voxelSize;
                    Vector3 bCenter = (vmin + vmax) * 0.5f;
                    Vector3 bHalf = (vmax - vmin) * 0.5f;

                    // (a) �����ص�����AABBͶӰ��N��
                    float projCenter = Vector3.Dot(N, bCenter - C);
                    float projRadius = Mathf.Abs(N.x) * bHalf.x + Mathf.Abs(N.y) * bHalf.y + Mathf.Abs(N.z) * bHalf.z;
                    if (Mathf.Abs(projCenter) > (H + projRadius))
                        continue; // ��Բ���ĸ߶ȷ�Χ���ص�

                    // (b) ������룺����ֱ��(C + tN) �� AABB ���������
                    float sqrDist = SqrDistanceLineAABB(C, N, vmin, vmax);
                    if (sqrDist <= R * R)
                    {
                        // 调试输出：记录切削时的体素坐标和世界坐标
                        #if UNITY_EDITOR || UNITY_WEBGL
                        if (!modified) // 只在第一次切削时输出，避免日志过多
                        {
                            Debug.Log($"[切削检测] 体素索引({x},{y},{z}), 体素世界坐标vmin={vmin}, vmax={vmax}, 刀具世界坐标C={C}, 距离sqrDist={sqrDist}");
                        }
                        #endif
                        
                        try
                        {
                            voxels[x, y, z] = 0;
                            modified = true;
                        }
                        catch (System.Exception e)
                        {
                            Debug.LogError($"Voxel写入异常: x={x}, y={y}, z={z}, 错误: {e.Message}");
                            break; // 如果写入失败，退出内层循环
                        }
                    }
                }
            }
        }

        // ���� 3) ֻ���޸ķ����ҵ���ϲ����ʱ�ؽ�����
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
    /// ����ֱ�� (P = C + t*N, t��R) �� AABB([bmin,bmax]) ���������ƽ����
    /// ������ͶӰ-��ȡ������3���ڷǳ��ȡ�
    /// </summary>
    private static float SqrDistanceLineAABB(Vector3 C, Vector3 N, Vector3 bmin, Vector3 bmax)
    {
        // ��ʼ���Ȱ����ϵ�ĳ�㣨������C����ȡ�������ϵõ�p
        Vector3 p = new Vector3(
            Mathf.Clamp(C.x, bmin.x, bmax.x),
            Mathf.Clamp(C.y, bmin.y, bmax.y),
            Mathf.Clamp(C.z, bmin.z, bmax.z)
        );

        float t = Vector3.Dot(N, p - C);
        Vector3 q = C + N * t; // ���ϵ�����㣨��Ե�ǰp��

        // ����������3~4���㹻��
        for (int i = 0; i < 3; i++)
        {
            p = new Vector3(
                Mathf.Clamp(q.x, bmin.x, bmax.x),
                Mathf.Clamp(q.y, bmin.y, bmax.y),
                Mathf.Clamp(q.z, bmin.z, bmax.z)
            );
            t = Vector3.Dot(N, p - C);
            q = C + N * t;

            // ��ѡ����ǰ�����ж�
            // if ((p - q).sqrMagnitude < 1e-10f) break;
        }

        return (q - p).sqrMagnitude;
    }

#if UNITY_EDITOR
    private void OnDrawGizmos()
    {
        if (!drawDebugGizmos || cutter == null) return;
        float H = cutterHeight * 0.5f;
        float R = cutterRadius;
        Vector3 C = cutter.position;
        Vector3 N = cutter.up.normalized;

        Vector3 ext;
        ext.x = R * Mathf.Sqrt(Mathf.Max(0f, 1f - N.x * N.x)) + H * Mathf.Abs(N.x);
        ext.y = R * Mathf.Sqrt(Mathf.Max(0f, 1f - N.y * N.y)) + H * Mathf.Abs(N.y);
        ext.z = R * Mathf.Sqrt(Mathf.Max(0f, 1f - N.z * N.z)) + H * Mathf.Abs(N.z);

        Gizmos.color = Color.cyan;
        // ������AABB��������+��ߴ续һ���߿�У�
        Vector3 aabbMin = C - ext;
        Vector3 aabbMax = C + ext;
        Vector3 center = (aabbMin + aabbMax) * 0.5f;
        Vector3 size = (aabbMax - aabbMin);
        Gizmos.DrawWireCube(center, size);
    }
#endif
}
