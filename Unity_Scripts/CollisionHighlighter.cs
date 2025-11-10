using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Attach to each machine part (X, Y, Z, A, C, base).
/// Highlights the object in red while it is colliding or overlapping with any other collider.
/// Works with both collision and trigger interactions. Uses MaterialPropertyBlock to avoid material instancing.
/// Ensure that at least one of the two interacting objects in the scene has a Rigidbody for collision callbacks.
/// </summary>
[DisallowMultipleComponent]
public class CollisionHighlighter : MonoBehaviour
{
	[SerializeField]
	private Color highlightColor = Color.red;

	[SerializeField]
	[Tooltip("Apply highlight to renderers on this object and its children.")]
	private bool includeChildRenderers = true;

	[SerializeField]
	[Tooltip("Print debug info about collisions, triggers, and setup state.")]
	private bool debugLogging = true;

	[Header("Adjacency Ignore (屏蔽邻接件)")]
	[SerializeField]
	[Tooltip("将这些对象(及其子层级)视为相邻件，与当前对象(及其子层级)互相忽略碰撞/触发。")]
	private List<Transform> adjacentRoots = new List<Transform>();

	[SerializeField]
	[Tooltip("在 Start 阶段自动为本体与相邻件配置 Physics.IgnoreCollision。")]
	private bool configureAdjacencyAtStart = true;

	[Header("Filter (过滤)")]
	[SerializeField]
	[Tooltip("仅对这些 Layer 的对象做高亮/统计。为空时表示不过滤(全部处理)。")]
	private LayerMask reactLayerMask = ~0; // 默认全部层

	private static readonly int ColorId = Shader.PropertyToID("_Color");
	private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");

	private readonly HashSet<Collider> activeContacts = new HashSet<Collider>();
	private readonly List<Renderer> cachedRenderers = new List<Renderer>();
	private MaterialPropertyBlock propertyBlock;

	private void Awake()
	{
		propertyBlock = new MaterialPropertyBlock();
		CacheRenderers();
	}

	private void Start()
	{
		if (debugLogging)
		{
			var collidersBuffer = new List<Collider>();
			GetComponentsInChildren(true, collidersBuffer);
			int triggerCount = 0;
			for (int i = 0; i < collidersBuffer.Count; i++)
			{
				if (collidersBuffer[i] != null && collidersBuffer[i].isTrigger)
				{
					triggerCount++;
				}
			}
			var rb = GetComponentInParent<Rigidbody>();
			Debug.Log($"[CollisionHighlighter] '{name}' setup: renderers={cachedRenderers.Count}, colliders={collidersBuffer.Count} (triggers={triggerCount}), rigidbody={(rb != null ? (rb.isKinematic ? "Kinematic" : "Dynamic") : "None")}.");
			if (cachedRenderers.Count == 0)
			{
				Debug.LogWarning($"[CollisionHighlighter] '{name}' has no renderers to highlight. Check 'includeChildRenderers' or attach to object with renderers.");
			}
			if (collidersBuffer.Count == 0)
			{
				Debug.LogWarning($"[CollisionHighlighter] '{name}' has no colliders. Attach colliders or child colliders to receive collision/trigger callbacks.");
			}
			if (rb == null)
			{
				Debug.LogWarning($"[CollisionHighlighter] '{name}' has no Rigidbody in self/parents. Unity requires at least one Rigidbody on either of the interacting objects. For OnCollision, at least one must be non-kinematic; for OnTrigger, kinematic is OK.");
			}
		}

		if (configureAdjacencyAtStart)
		{
			SetupAdjacencyIgnores();
		}
	}

	private void OnEnable()
	{
		// Ensure clean visual state on enable
		ClearHighlight();
	}

	private void OnDisable()
	{
		activeContacts.Clear();
		ClearHighlight();
	}

	private void CacheRenderers()
	{
		cachedRenderers.Clear();
		if (includeChildRenderers)
		{
			GetComponentsInChildren(true, cachedRenderers);
		}
		else
		{
			var r = GetComponent<Renderer>();
			if (r != null)
			{
				cachedRenderers.Add(r);
			}
		}
	}

	private void ApplyHighlight()
	{
		propertyBlock.Clear();
		propertyBlock.SetColor(ColorId, highlightColor);
		propertyBlock.SetColor(BaseColorId, highlightColor);
		for (int i = 0; i < cachedRenderers.Count; i++)
		{
			var renderer = cachedRenderers[i];
			if (renderer != null)
			{
				renderer.SetPropertyBlock(propertyBlock);
			}
		}
		if (debugLogging)
		{
			Debug.Log($"[CollisionHighlighter] '{name}' APPLY highlight on {cachedRenderers.Count} renderer(s).");
		}
	}

	private void ClearHighlight()
	{
		for (int i = 0; i < cachedRenderers.Count; i++)
		{
			var renderer = cachedRenderers[i];
			if (renderer != null)
			{
				// Passing null clears the block and restores original material appearance
				renderer.SetPropertyBlock(null);
			}
		}
		if (debugLogging)
		{
			Debug.Log($"[CollisionHighlighter] '{name}' CLEAR highlight.");
		}
	}

	/// <summary>
	/// 在运行时基于 <see cref="adjacentRoots"/> 为当前对象(含子层级)与相邻件(含子层级)调用 Physics.IgnoreCollision。
	/// 这会屏蔽内部邻接零件之间的碰撞与触发回调，避免自碰/假阳性。
	/// </summary>
	public void SetupAdjacencyIgnores()
	{
		// 收集本体全部 Collider
		var selfColliders = new List<Collider>();
		GetComponentsInChildren(true, selfColliders);
		int totalPairs = 0;
		int totalOthers = 0;
		for (int i = 0; i < adjacentRoots.Count; i++)
		{
			var root = adjacentRoots[i];
			if (root == null) continue;
			// 收集相邻件全部 Collider
			var otherColliders = new List<Collider>();
			root.GetComponentsInChildren(true, otherColliders);
			totalOthers += otherColliders.Count;
			// 逐对屏蔽
			for (int a = 0; a < selfColliders.Count; a++)
			{
				var ca = selfColliders[a];
				if (ca == null) continue;
				for (int b = 0; b < otherColliders.Count; b++)
				{
					var cb = otherColliders[b];
					if (cb == null) continue;
					// 忽略自身或同一 Collider
					if (ReferenceEquals(ca, cb)) continue;
					Physics.IgnoreCollision(ca, cb, true);
					totalPairs++;
				}
			}
		}
		if (debugLogging)
		{
			Debug.Log($"[CollisionHighlighter] '{name}' adjacency configured: selfColliders={selfColliders.Count}, otherColliders={totalOthers}, ignoredPairs={totalPairs}.");
		}
	}

	private void RegisterContact(Collider other)
	{
		if (other == null)
		{
			return;
		}

		// Layer 过滤
		if ((reactLayerMask.value & (1 << other.gameObject.layer)) == 0)
		{
			if (debugLogging)
			{
				Debug.Log($"[CollisionHighlighter] '{name}' ignore contact (layer filtered) with '{other.name}'.");
			}
			return;
		}

		if (activeContacts.Add(other))
		{
			if (activeContacts.Count == 1)
			{
				ApplyHighlight();
			}
		}
	}

	private void UnregisterContact(Collider other)
	{
		if (other == null)
		{
			return;
		}
		if (activeContacts.Remove(other))
		{
			if (activeContacts.Count == 0)
			{
				ClearHighlight();
			}
		}
	}

	private void OnCollisionEnter(Collision collision)
	{
		if (debugLogging)
		{
			Debug.Log($"[CollisionHighlighter] '{name}' OnCollisionEnter with '{(collision != null && collision.collider != null ? collision.collider.name : "null")}'.");
		}
		RegisterContact(collision != null ? collision.collider : null);
	}

	private void OnCollisionExit(Collision collision)
	{
		if (debugLogging)
		{
			Debug.Log($"[CollisionHighlighter] '{name}' OnCollisionExit with '{(collision != null && collision.collider != null ? collision.collider.name : "null")}'.");
		}
		UnregisterContact(collision != null ? collision.collider : null);
	}

	private void OnTriggerEnter(Collider other)
	{
		if (debugLogging)
		{
			Debug.Log($"[CollisionHighlighter] '{name}' OnTriggerEnter with '{(other != null ? other.name : "null")}'.");
		}
		RegisterContact(other);
	}

	private void OnTriggerExit(Collider other)
	{
		if (debugLogging)
		{
			Debug.Log($"[CollisionHighlighter] '{name}' OnTriggerExit with '{(other != null ? other.name : "null")}'.");
		}
		UnregisterContact(other);
	}

	#if UNITY_EDITOR
	private void OnValidate()
	{
		// Refresh renderer cache in editor when properties change
		if (!Application.isPlaying)
		{
			CacheRenderers();
		}
	}
	#endif
}


