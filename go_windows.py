#!/usr/bin/env python3
"""
Windows 版视频处理流水线
用法: python go_windows.py
"""
import subprocess, sys, os
from pathlib import Path

# Windows 路径配置
HOME = Path.home()
BASE = HOME / "video-pipeline"
SOURCE = BASE / "source"
OUTPUT = BASE / "output"
TRIMMED = OUTPUT / "trimmed3"
FFMPEG = "ffmpeg"  # Windows 直接用系统 ffmpeg

def run(cmd, **kwargs):
    return subprocess.run(cmd, shell=True, check=True, **kwargs)

def main():
    print("=======================================")
    print("🎬 视频处理流水线启动 (Windows)")
    print("=======================================")

    # 创建目录
    TRIMMED.mkdir(parents=True, exist_ok=True)

    # 选择字幕风格
    print("\n🎨 选择字幕风格：")
    print("   1) 白色字幕 + 黑色描边")
    print("   2) 白色字幕 + 关键词黄色高亮（推荐）")
    print("   3) 淡入淡出动态效果")
    print("   4) 卡拉OK变色效果")
    style_num = input("\n输入数字 [1-4，默认2]: ").strip() or "2"
    style_map = {"1": "normal", "2": "highlight", "3": "fade", "4": "karaoke"}
    style = style_map.get(style_num, "highlight")
    print(f"✅ 已选择: {style}")

    # 关键词
    keywords = ""
    if style == "highlight":
        print("\n🔑 输入本期视频重点关键词")
        print("   多个词用空格或逗号分隔")
        keywords = input("关键词：").strip()
        print(f"✅ 关键词: {keywords}")

    # 语言选择
    print("\n🌐 选择字幕语言：")
    print("   1) 中文")
    print("   2) 英文")
    print("   3) 中英双语")
    lang_num = input("输入数字 [1-3，默认1]: ").strip() or "1"
    lang_map = {"1": "zh", "2": "en", "3": "zh+en"}
    lang = lang_map.get(lang_num, "zh")

    # STEP 1: 去气口
    print("\n✂️  STEP 1: 去除气口...")
    script_dir = Path(__file__).parent
    run(f'python "{script_dir}/remove_silence.py"')
    print("✅ 完成")

    # STEP 2: 拼接
    print("🔗 STEP 2: 拼接合成...")
    cuts = sorted(TRIMMED.glob("*_cut.mp4"))
    list_file = OUTPUT / "filelist.txt"
    with open(list_file, "w") as f:
        for c in cuts:
            f.write(f"file '{c}'\n")
    merged = OUTPUT / "merged_temp.mp4"
    run(f'{FFMPEG} -f concat -safe 0 -i "{list_file}" -c:v libx264 -preset fast -crf 23 -c:a aac "{merged}" -y')
    print("✅ 完成")

    # STEP 3: 字幕
    print("📝 STEP 3: 生成字幕...")
    run(f'python "{script_dir}/make_srt.py" {lang}')
    print("✅ 完成")

    # STEP 4: 字幕样式
    print("🎨 STEP 4: 生成字幕样式...")
    run(f'python "{script_dir}/make_subtitle.py" {style} "{keywords}"')

    # STEP 5: 烧录
    print("🎞️  STEP 5: 烧录字幕...")
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    final = OUTPUT / f"final_{style}_{ts}.mp4"
    ass = OUTPUT / "subtitles.ass"
    run(f'{FFMPEG} -i "{merged}" -vf "ass={ass}" -c:v libx264 -preset fast -crf 23 -c:a copy "{final}" -y')

    print(f"\n=======================================")
    print(f"🎉 完成！输出: {final}")
    print(f"=======================================")
    os.startfile(OUTPUT)  # 自动打开输出文件夹

if __name__ == "__main__":
    main()
