using UnityEngine;

/// <summary>
/// 支持WebGL下多摄像机切换的脚本
/// </summary>
public class CameraSwitcher : MonoBehaviour
{
    [Header("可切换的摄像机列表（请在Inspector面板拖入）")]
    public Camera[] cameras;

    void Start()
    {
        SetActiveCamera(0); // 默认激活第一个
    }

    // JS端会用SendMessage调用本方法
    public void SwitchToCamera(int idx)
    {
        Debug.Log("切换摄像机收到调用 idx=" + idx);
        if (cameras == null || cameras.Length == 0) return;
        if (idx < 0 || idx >= cameras.Length) return;
        SetActiveCamera(idx);
    }

    // 仅内部用—切换激活状态
    private void SetActiveCamera(int idx)
    {
        for (int i = 0; i < cameras.Length; i++)
        {
            cameras[i].gameObject.SetActive(i == idx);
        }
    }
}