# Node Result Contract Plan

当前阶段不全量修改节点返回结构，避免影响 `workflow.py`、断点续跑 `state.json` 和现有调用字段。

## 目标格式

后续节点逐步返回统一结构：

```python
{
    "success": bool,
    "data": dict,
    "error": str | None,
    "meta": dict,
}
```

## 兼容策略

迁移期间保留旧字段，例如：

```python
{
    "success": True,
    "data": {
        "image_paths": [...],
        "image_urls": [...],
    },
    "error": None,
    "meta": {
        "node": "model_generator",
        "model": "high_aes_general_v30l_zt2i",
    },

    # Legacy fields used by workflow.py
    "image_paths": [...],
    "image_urls": [...],
}
```

## 建议顺序

1. 新增 `nodes/result.py`，提供 `ok()` 和 `fail()` 辅助函数。
2. 新改动节点先返回 `data/error/meta`，同时保留旧字段。
3. `workflow.py` 逐步改为优先读取 `result["data"]`，缺失时回退旧字段。
4. 所有节点迁移完成后，再考虑移除旧字段。
