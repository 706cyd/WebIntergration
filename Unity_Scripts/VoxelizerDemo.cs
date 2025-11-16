using UnityEngine;
using System;
using System.Collections.Generic;
using UnityEngine.UIElements;

namespace MeshVoxelizerProject
{

    public class VoxelizerDemo : MonoBehaviour
    {

        public int size = 3;

        public bool drawAABBTree;

        [Header("Debug Options")]
        public bool outputVoxelDebugInfo = false; // 是否输出体素的调试信息

        public MeshVoxelizer m_voxelizer; // 0902修改：将该字段改为 public，以便其他脚本访问
        private MeshFilter m_voxelMeshFilter; // 0902新增的字段，用于保存体素化网格的引用
        private Mesh m_voxelMesh; // 复用的体素网格，避免频繁分配导致内存暴涨

        // void Start()
        void Awake()
        {
            // 获取当前GameObject上的MeshFilter和MeshRenderer组件
            MeshFilter filter = GetComponent<MeshFilter>();
            MeshRenderer renderer = GetComponent<MeshRenderer>();

            // 如果没有，可以获取子对象上的这些组件
            if (filter == null || renderer == null)
            {
                filter = GetComponentInChildren<MeshFilter>();
                renderer = GetComponentInChildren<MeshRenderer>();
            }

            if (filter == null || renderer == null) return; // 如果仍然没有找到组件，方法直接返回，不执行后续代码

            renderer.enabled = false; // 禁用原始模型的渲染，使其不继续显示，因为将显示体素化的网格

            // 获取原始网格的数据，获取原始网格的材料
            Mesh mesh = filter.mesh;
            Material mat = renderer.material;

            // 创建一个自定义的包围盒对象
            Box3 bounds = new Box3(mesh.bounds.min, mesh.bounds.max);

            m_voxelizer = new MeshVoxelizer(size, size, size); // 实例化 MeshVoxelizer 类，使用 size 作为网格的维度
            m_voxelizer.Voxelize(mesh.vertices, mesh.triangles, bounds); // 调用体素化的核心方法，将原始网格的顶点、三角形和包围盒传入，执行体素化处理

            GenerateVoxelMesh();
            //Vector3 scale = new Vector3(bounds.Size.x / size, bounds.Size.y / size, bounds.Size.z / size); // 计算每个体素在空间中占的实际尺寸
            //Vector3 m = new Vector3(bounds.Min.x, bounds.Min.y, bounds.Min.z); // 获取包围盒中的最小点，用于后续计算体素的起始位置
            //mesh = CreateMesh(m_voxelizer.Voxels, scale, m); // 调用 CreateMesh 方法，将体素化的数据 (m_voxelizer.Voxels)、体素尺寸和起始位置传入，生成一个新的网格

            //// 之后进行一些赋值操作
            //GameObject go = new GameObject("Voxelized");
            //go.transform.parent = transform;
            //go.transform.localPosition = Vector3.zero;
            //go.transform.localScale = Vector3.one;
            //go.transform.localRotation = Quaternion.identity;

            //filter = go.AddComponent<MeshFilter>();
            //renderer = go.AddComponent<MeshRenderer>();

            //filter.mesh = mesh;
            //renderer.material = mat;
        }

        // 体素网格生成和渲染逻辑封装
        public void GenerateVoxelMesh()
        {
            if (m_voxelizer == null)
            {
                Debug.LogError("Voxelizer has not been initialized.");
                return;
            }

            // 从 m_voxelizer 获取体素数据
            int[,,] voxels = m_voxelizer.Voxels;

            // 计算体素的缩放和起始位置
            MeshFilter filter = GetComponent<MeshFilter>();
            MeshRenderer renderer = GetComponent<MeshRenderer>();
            if (filter == null || renderer == null)
            {
                filter = GetComponentInChildren<MeshFilter>();
                renderer = GetComponentInChildren<MeshRenderer>();
            }
            if (filter == null || renderer == null) return;

            // 如果还没有用于显示体素化的 GameObject，就先创建（提前创建以便后续以其坐标系计算）
            if (m_voxelMeshFilter == null)
            {
                GameObject go = new GameObject("Voxelized");
                Transform srcTransform = filter.transform;
                go.transform.parent = srcTransform.parent; // 与原模型相同父级
                go.transform.localPosition = srcTransform.localPosition;
                go.transform.localRotation = srcTransform.localRotation;
                go.transform.localScale = srcTransform.localScale;

                m_voxelMeshFilter = go.AddComponent<MeshFilter>();
                MeshRenderer voxelRenderer = go.AddComponent<MeshRenderer>();
                // 使用 sharedMaterial，避免 material 属性实例化材质导致 GFX 内存增长
                var srcRenderer = renderer != null ? renderer : GetComponent<MeshRenderer>();
                if (srcRenderer != null)
                {
                    voxelRenderer.sharedMaterial = srcRenderer.sharedMaterial;
                }
                go.SetActive(true);
            }

            // 关键修复：使用与 MillingManager 完全相同的世界坐标计算方法
            // 这确保了切削检测和Mesh生成使用相同的坐标系统
            var lb = filter.sharedMesh.bounds; // 局部坐标的包围盒
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

            // 转换为世界坐标（与 MillingManager.Start() 完全相同）
            Vector3 wmin = new Vector3(float.PositiveInfinity, float.PositiveInfinity, float.PositiveInfinity);
            Vector3 wmax = new Vector3(float.NegativeInfinity, float.NegativeInfinity, float.NegativeInfinity);
            for (int i = 0; i < 8; i++)
            {
                Vector3 w = filter.transform.TransformPoint(localCorners[i]);
                wmin = Vector3.Min(wmin, w);
                wmax = Vector3.Max(wmax, w);
            }

            Vector3 worldSize = wmax - wmin;
            Vector3 voxelSize_world = new Vector3(worldSize.x / size, worldSize.y / size, worldSize.z / size);
            
            // 现在需要将世界坐标转换为生成Mesh的GameObject的局部坐标
            // 生成的GameObject会放在 filter.transform.parent 下，并且有相同的localPosition/localRotation/localScale
            // 关键：由于GameObject的Transform与原模型相同，我们需要计算相对于原模型局部坐标系统的体素位置
            // 注意：以实际用于渲染的 Voxelized 对象的变换为准，避免坐标换算误差导致提前切削
            
            Transform filterTransform = filter.transform;
            Transform dstTransform = m_voxelMeshFilter.transform;
            Vector3 m; // 局部坐标的起始点（相对于filterTransform）
            Vector3 scale; // 局部坐标下的体素尺寸
            
            // 使用 Voxelized 对象的坐标系计算最小点（与最终网格一致）
            m = dstTransform.InverseTransformPoint(wmin);
            
            // 对于缩放，我们需要考虑filterTransform的缩放
            // 但是，由于voxelSize_world是世界坐标下的尺寸，我们需要考虑从世界坐标到局部坐标的缩放
            // 实际上，由于我们使用了InverseTransformPoint，坐标已经转换了，但尺寸还需要考虑
            // 简化方法：使用原模型的局部尺寸计算scale（这样更稳定）
            Box3 localBounds = new Box3(filter.sharedMesh.bounds.min, filter.sharedMesh.bounds.max);
            scale = new Vector3(localBounds.Size.x / size, localBounds.Size.y / size, localBounds.Size.z / size);
            
            // 调试输出（已禁用，避免控制台干扰）
            // #if UNITY_EDITOR
            // Debug.Log($"[GenerateVoxelMesh] 世界坐标 - wmin: {wmin}, worldSize: {worldSize}, voxelSize_world: {voxelSize_world}");
            // Debug.Log($"[GenerateVoxelMesh] 局部坐标 - m: {m}, scale: {scale}, dstTransform: {dstTransform.name}");
            // Debug.Log($"[GenerateVoxelMesh] 验证: wmin转换回世界坐标 = {dstTransform.TransformPoint(m)} (应该等于wmin)");
            // #endif

            // 0902 新增的调试输出信息
            if (outputVoxelDebugInfo)
            {
                #if UNITY_EDITOR
                Debug.Log("====== Voxel Debug Info ======");
                Debug.Log($"WorldMin: {wmin}, WorldSize: {worldSize}, VoxelSize (world): {voxelSize_world}");
                Debug.Log($"LocalMin: {m}, Scale (local): {scale}, Dst: {dstTransform.name}");
                Debug.Log($"Dst Transform - Position: {dstTransform.position}, LocalPosition: {dstTransform.localPosition}");
                for (int z = 0; z < size; z++)
                {
                    for (int y = 0; y < size; y++)
                    {
                        for (int x = 0; x < size; x++)
                        {
                            if (voxels[x, y, z] == 1)
                            {
                                // 计算局部坐标下的位置
                                Vector3 localPos = m + new Vector3(x * scale.x, y * scale.y, z * scale.z);
                                // 转换为世界坐标用于显示
                                Vector3 worldPos = dstTransform.TransformPoint(localPos);
                                Debug.Log($"Voxel[{x},{y},{z}] -> LocalPos: {localPos}, WorldPos: {worldPos}");
                            }
                        }
                    }
                }
                Debug.Log("==============================");
                #endif
            }

            // 调用 CreateMesh 方法，将体素化的数据传入，生成一个新的网格（临时 Mesh）
            Mesh newMesh = CreateMesh(voxels, scale, m);
            
            // 检查生成的Mesh是否有效
            if (newMesh == null)
            {
                Debug.LogError("[GenerateVoxelMesh] CreateMesh 返回 null！");
                return;
            }
            
            if (newMesh.vertexCount == 0)
            {
                Debug.LogWarning("[GenerateVoxelMesh] 生成的Mesh顶点数为0！可能没有有效的体素数据。");
                Debug.LogWarning($"[GenerateVoxelMesh] 参数检查 - m: {m}, scale: {scale}, wmin: {wmin}, worldSize: {worldSize}");
            }
            else
            {
                Debug.Log($"[GenerateVoxelMesh] 成功生成Mesh - 顶点数: {newMesh.vertexCount}, 三角形数: {newMesh.triangles.Length / 3}");
            }

            // 复用单一 Mesh 实例，避免频繁分配导致 VertexData/GFX 内存上涨
            if (m_voxelMesh == null)
            {
                m_voxelMesh = new Mesh();
                m_voxelMesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
                m_voxelMesh.MarkDynamic();
            }
            // 用新生成的临时 Mesh 数据更新复用 Mesh
            m_voxelMesh.Clear(false);
            m_voxelMesh.SetVertices(newMesh.vertices);
            m_voxelMesh.SetTriangles(newMesh.triangles, 0);
            m_voxelMesh.RecalculateBounds();
            m_voxelMesh.RecalculateNormals();

            // 释放临时 Mesh，防止堆积
            UnityEngine.Object.Destroy(newMesh);

            // 将复用的 Mesh 赋值给 MeshFilter（sharedMesh 避免 .mesh 的隐式复制）
            m_voxelMeshFilter.sharedMesh = m_voxelMesh;
            
            // 确保 MeshRenderer 是启用的
            MeshRenderer mr = m_voxelMeshFilter.GetComponent<MeshRenderer>();
            if (mr != null)
            {
                mr.enabled = true;
            }
            
            Debug.Log($"[GenerateVoxelMesh] Mesh已赋值，GameObject位置: {m_voxelMeshFilter.transform.position}, 局部位置: {m_voxelMeshFilter.transform.localPosition}");

        }

        // 修改指定体素的值
        public void ModifyVoxel(int x, int y, int z, int value) // 修改体素数据的方法
        {
            if (m_voxelizer == null)
            {
                Debug.LogError("Voxelizer has not been initialized.");
                return;
            }

            // 确保体素坐标在有效范围内
            if (x >= 0 && x < size && y >= 0 && y < size && z >= 0 && z < size)
            {
                // 直接修改体素数组中的值
                m_voxelizer.Voxels[x, y, z] = value;

                // 重新生成和渲染体素化的网格
                GenerateVoxelMesh();
            }
            else
            {
                Debug.LogWarning("Voxel coordinates are out of bounds.");
            }
        }

        private void OnRenderObject() // Unity在渲染物体时调用，用于绘制包围盒
        {
            var camera = Camera.current;

            if (drawAABBTree && m_voxelizer != null)
            {
                Matrix4x4 m = transform.localToWorldMatrix;

                foreach (Box3 box in m_voxelizer.Bounds) // 遍历 m_voxelizer 中存储的所有包围盒
                {
                    DrawLines.DrawBounds(camera, Color.red, box, m); // 调用自定义的DrawLine工具来绘制形状
                }
            }

        }

        private Mesh CreateMesh(int[,,] voxels, Vector3 scale, Vector3 min) // int[,,] voxels: 一个三维整数数组，表示体素数据。1 表示体素被占用，0 表示体素为空。
        {
            List<Vector3> verts = new List<Vector3>(); // 存储生成的顶点
            List<int> indices = new List<int>(); // 存储生成的三角形索引

            // 使用嵌套循环遍历所有体素
            for (int z = 0; z < size; z++)
            {
                for (int y = 0; y < size; y++)
                {
                    for (int x = 0; x < size; x++)
                    {
                        if (voxels[x, y, z] != 1) continue; // 如果当前体素是空的，跳过

                        Vector3 pos = min + new Vector3(x * scale.x, y * scale.y, z * scale.z); // 计算当前体素的起始世界坐标

                        // 检查当前体素的相邻体素是否为空或是否在边界上
                        // 如果相邻体素为空或在边界上
                        // 说明当前体素的该面是暴露的
                        // 需要创建一个四边形来表示该面
                        if (x == size - 1 || voxels[x + 1, y, z] == 0)
                            AddRightQuad(verts, indices, scale, pos);

                        if (x == 0 || voxels[x - 1, y, z] == 0)
                            AddLeftQuad(verts, indices, scale, pos);

                        if (y == size - 1 || voxels[x, y + 1, z] == 0)
                            AddTopQuad(verts, indices, scale, pos);

                        if (y == 0 || voxels[x, y - 1, z] == 0)
                            AddBottomQuad(verts, indices, scale, pos);

                        if (z == size - 1 || voxels[x, y, z + 1] == 0)
                            AddFrontQuad(verts, indices, scale, pos);

                        if (z == 0 || voxels[x, y, z - 1] == 0)
                            AddBackQuad(verts, indices, scale, pos);
                    }
                }
            }

            if (verts.Count > 65000)
            {
                Debug.Log("Mesh has too many verts. You need to add code to split it up.");
                Debug.Log("verts.Count: " + verts.Count);
                // return new Mesh();
            }

            // 给mesh设置一些属性
            Mesh mesh = new Mesh();

            mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32; // 默认16位索引，这里改为32位索引

            mesh.SetVertices(verts);
            mesh.SetTriangles(indices, 0);

            mesh.RecalculateBounds();
            mesh.RecalculateNormals();

            return mesh;
        }

        // 下面定义一些私有的辅助函数，用于生成体素各个面的四边形，这些函数分别生成不同的面
        private void AddRightQuad(List<Vector3> verts, List<int> indices, Vector3 scale, Vector3 pos)
        {
            int count = verts.Count;

            verts.Add(pos + new Vector3(1 * scale.x, 0 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 1 * scale.y, 0 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 0 * scale.y, 0 * scale.z));

            verts.Add(pos + new Vector3(1 * scale.x, 0 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 1 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 1 * scale.y, 0 * scale.z));

            indices.Add(count + 2); indices.Add(count + 1); indices.Add(count + 0);
            indices.Add(count + 5); indices.Add(count + 4); indices.Add(count + 3);
        }

        private void AddLeftQuad(List<Vector3> verts, List<int> indices, Vector3 scale, Vector3 pos)
        {
            int count = verts.Count;

            verts.Add(pos + new Vector3(0 * scale.x, 0 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(0 * scale.x, 1 * scale.y, 0 * scale.z));
            verts.Add(pos + new Vector3(0 * scale.x, 0 * scale.y, 0 * scale.z));

            verts.Add(pos + new Vector3(0 * scale.x, 0 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(0 * scale.x, 1 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(0 * scale.x, 1 * scale.y, 0 * scale.z));

            indices.Add(count + 0); indices.Add(count + 1); indices.Add(count + 2);
            indices.Add(count + 3); indices.Add(count + 4); indices.Add(count + 5);
        }

        private void AddTopQuad(List<Vector3> verts, List<int> indices, Vector3 scale, Vector3 pos)
        {
            int count = verts.Count;

            verts.Add(pos + new Vector3(0 * scale.x, 1 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 1 * scale.y, 0 * scale.z));
            verts.Add(pos + new Vector3(0 * scale.x, 1 * scale.y, 0 * scale.z));

            verts.Add(pos + new Vector3(0 * scale.x, 1 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 1 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 1 * scale.y, 0 * scale.z));

            indices.Add(count + 0); indices.Add(count + 1); indices.Add(count + 2);
            indices.Add(count + 3); indices.Add(count + 4); indices.Add(count + 5);
        }

        private void AddBottomQuad(List<Vector3> verts, List<int> indices, Vector3 scale, Vector3 pos)
        {
            int count = verts.Count;

            verts.Add(pos + new Vector3(0 * scale.x, 0 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 0 * scale.y, 0 * scale.z));
            verts.Add(pos + new Vector3(0 * scale.x, 0 * scale.y, 0 * scale.z));

            verts.Add(pos + new Vector3(0 * scale.x, 0 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 0 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 0 * scale.y, 0 * scale.z));

            indices.Add(count + 2); indices.Add(count + 1); indices.Add(count + 0);
            indices.Add(count + 5); indices.Add(count + 4); indices.Add(count + 3);
        }

        private void AddFrontQuad(List<Vector3> verts, List<int> indices, Vector3 scale, Vector3 pos)
        {
            int count = verts.Count;

            verts.Add(pos + new Vector3(0 * scale.x, 1 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 0 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(0 * scale.x, 0 * scale.y, 1 * scale.z));

            verts.Add(pos + new Vector3(0 * scale.x, 1 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 1 * scale.y, 1 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 0 * scale.y, 1 * scale.z));

            indices.Add(count + 2); indices.Add(count + 1); indices.Add(count + 0);
            indices.Add(count + 5); indices.Add(count + 4); indices.Add(count + 3);
        }

        private void AddBackQuad(List<Vector3> verts, List<int> indices, Vector3 scale, Vector3 pos)
        {
            int count = verts.Count;

            verts.Add(pos + new Vector3(0 * scale.x, 1 * scale.y, 0 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 0 * scale.y, 0 * scale.z));
            verts.Add(pos + new Vector3(0 * scale.x, 0 * scale.y, 0 * scale.z));

            verts.Add(pos + new Vector3(0 * scale.x, 1 * scale.y, 0 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 1 * scale.y, 0 * scale.z));
            verts.Add(pos + new Vector3(1 * scale.x, 0 * scale.y, 0 * scale.z));

            indices.Add(count + 0); indices.Add(count + 1); indices.Add(count + 2);
            indices.Add(count + 3); indices.Add(count + 4); indices.Add(count + 5);
        }

    }

}
