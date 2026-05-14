"""
入口文件 - 直接运行此文件启动工作流
用法：python main.py
"""

import workflow


# ============================================================
# 在此填入你的产品信息
# ============================================================
PRODUCT_INPUT = {
    "product_name": "XX助眠软糖",                         # 产品名称
    "product_offer": "含植物提取成分，睡前嚼1粒，30分钟帮助入睡，无依赖感",  # 功能/Offer
    "target_audience": "25-40岁上班族，长期睡眠质量差",         # 目标受众
    "pain_points": "压力大难以入睡、睡前刷手机停不下来、白天犯困精神不好",  # 核心痛点
    "total_duration": 30,                                  # 视频总时长（秒）
}


if __name__ == "__main__":
    result = workflow.run(**PRODUCT_INPUT)

    print("\n--- 完整脚本预览 ---")
    print(result.get("full_script", "（脚本未生成）"))

    print("\n--- 分镜列表 ---")
    for scene in result.get("scenes", []):
        print(f"  [{scene['scene_id']}] {scene['duration']}s | {scene['script']}")
        print(f"       画面：{scene.get('visual_note', '')}")

    print("\n--- 视频文件 ---")
    for i, path in enumerate(result.get("video_paths", [])):
        print(f"  分镜{i+1}: {path or '（生成失败）'}")
