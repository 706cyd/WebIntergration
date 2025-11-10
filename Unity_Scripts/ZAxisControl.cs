using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class ZAxisControl : MonoBehaviour
{
    public Vector3 startPos = new Vector3(0.0f, 0.2f, -0.15f);  // 起始位置
    public Vector3 endPos = new Vector3(0.0f, 0.2f, 0.15f);      // 目标位置
    public float moveSpeed = 0.03f;  // 固定移动速度（单位：每秒）

    public float waveAmplitude = 10f; // 波浪振幅(正弦曲线)
    public float waveFrequency = 2f; // 波浪频率(波的次数)

    private float journeyLength;  // 起始位置到目标位置的距离
    private float startTime;      // 开始时间
    private bool isMoving = false; // 是否正在运动
    
    // 静态标志，供CNCMachineController检查
    public static bool isZAxisSMotionActive = false;
    
    [Header("自动启动设置")]
    public bool autoStartInEditor = true; // 在编辑器中自动启动（方便测试）

    void Start()
    {
        // 设置初始位置
        transform.position = startPos;

        // 计算起始位置到目标位置的总距离
        journeyLength = Vector3.Distance(startPos, endPos);
        
        // 在Unity编辑器中自动启动（方便测试），WebGL中需要手动启动
        #if UNITY_EDITOR
        if (autoStartInEditor)
        {
            StartSMotion();
        }
        #endif
    }

    void Update()
    {
        if (!isMoving) return; // 如果未启动，不执行运动

        // 计算从开始到当前时间已经过的时间（受Time.timeScale影响）
        float distanceCovered = (Time.time - startTime) * moveSpeed;

        float t = Mathf.Clamp01(distanceCovered / journeyLength);

        // 直线基础插值
        Vector3 pos = Vector3.Lerp(startPos, endPos, t);

        // 在X轴添加正弦波浪轨迹（S型曲线）
        pos.x += Mathf.Sin(t * Mathf.PI * waveFrequency) * waveAmplitude;

        transform.position = pos;

        // 到达目标位置时停止
        if (t >= 1.0f)
        {
            transform.position = endPos;
            isMoving = false;
            isZAxisSMotionActive = false; // 通知其他脚本Z轴运动已完成
            Debug.Log("Z轴S型运动完成");
        }
    }
    
    // Web端调用：设置运动速度倍率
    public void SetSpeedMultiplier(float multiplier)
    {
        // 可选：通过Web直接控制运动速度
        moveSpeed = 0.03f * multiplier;
        Debug.Log("Z轴运动速度设置为: " + moveSpeed);
    }

    // Web端调用：启动S型运动
    public void StartSMotion()
    {
        Debug.Log("启动Z轴S型运动 - GameObject: " + gameObject.name);
        Debug.Log("当前位置: " + transform.position);
        Debug.Log("isMoving设置为true");
        transform.position = startPos; // 重置到起始位置
        startTime = Time.time; // 记录开始时间
        isMoving = true;
        isZAxisSMotionActive = true; // 通知其他脚本Z轴正在S型运动
        Debug.Log("启动完成，新位置: " + transform.position);
    }

    // Web端调用：停止S型运动
    public void StopSMotion()
    {
        Debug.Log("停止Z轴S型运动");
        isMoving = false;
        isZAxisSMotionActive = false; // 通知其他脚本Z轴运动已停止
    }

    // Web端调用：重置到起始位置
    public void ResetPosition()
    {
        Debug.Log("重置Z轴位置");
        isMoving = false;
        transform.position = startPos;
    }
}

