"""
入口文件 - 直接运行此文件启动交互式工作流
用法：python main.py

交互式流程说明：
  1. 程序自动执行：人物小传生成 → 特征提取/音色选择/生图 → 脚本生成（并行）
  2. [Checkpoint 1] 生图完成后暂停，等待用户确认图片是否满意
       - 满意 → 继续下一步
       - 不满意 → 可选择修改提示词后重新生成（支持无限次循环）
  3. [Checkpoint 2] 进入视频生成前，展示完整脚本，等待用户确认/微调
       - 直接确认 → 使用原脚本
       - 选择微调 → 逐条编辑各分镜台词
  4. [Checkpoint 3 - 仅 Omni 引擎] TTS生成后，为每段分镜选择首帧人物图片
       - 输入图片序号（从展示列表中选）
       - 或直接粘贴本地路径 / 公网 URL
       - 可选择对所有分镜使用同一张图片（快速模式）
  5. 程序执行视频生成、模卡图生成，完成后输出汇总
"""

import workflow


# ============================================================
# 在此填入你的产品信息
# ============================================================
PRODUCT_INPUT = {
    "product_name": "微证券小程序",                              # 产品名称
    "product_offer": "工作盯盘、微信提醒、免下App等",       # 功能/Offer
    "target_audience": "25-40岁上班族",              # 目标受众
    "pain_points": "上班开会用炒股App太显眼，容易错过关键行情等",   # 核心痛点
    "total_duration": 25,                                       # 视频总时长（秒）
}


if __name__ == "__main__":
    result = workflow.run(
        **PRODUCT_INPUT,
        run_id=None,       # 留空自动生成新 Run ID；填入已有 ID 可断点续跑
        # run_id="20260517_022956",   # 断点续跑示例
    )

    print("\n--- 完整脚本预览 ---")
    print(result.get("full_script", "（脚本未生成）"))

    print("\n--- 分镜列表 ---")
    for scene in result.get("scenes", []):
        print(f"  [{scene['scene_id']}] {scene['duration']}s | {scene['script']}")
        print(f"       画面：{scene.get('visual_note', '')}")

    print("\n--- 视频文件 ---")
    for i, path in enumerate(result.get("video_paths", [])):
        print(f"  分镜{i+1}: {path or '（生成失败）'}")
