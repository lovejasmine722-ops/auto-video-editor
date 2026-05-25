#!/usr/bin/env python3
"""
对标视频复刻完整流程：
1. 下载对标视频
2. Whisper 提取文案
3. AI 改写文案
4. Edge TTS 合成配音
5. 下载免费素材
6. ffmpeg 合成新视频
"""
import subprocess, sys, os, json, re
from pathlib import Path

BASE = Path.home() / "video-pipeline"
OUTPUT = BASE / "output"
SOURCE = BASE / "source"
OUTPUT.mkdir(parents=True, exist_ok=True)

# ===== 配音声音选择 =====
VOICES = {
    "1": ("zh-CN-XiaoxiaoNeural", "中文活泼女声（带货推荐）"),
    "2": ("zh-CN-YunxiNeural",    "中文年轻男声"),
    "3": ("zh-CN-XiaoyiNeural",   "中文活泼少女声"),
    "4": ("zh-CN-YunjianNeural",  "中文成熟男声"),
    "5": ("en-US-JennyNeural",    "英文活泼女声（TikTok推荐）"),
    "6": ("en-US-GuyNeural",      "英文男声"),
    "7": ("en-GB-SoniaNeural",    "英式女声"),
    "8": ("ja-JP-NanamiNeural",   "日语女声"),
    "9": ("ko-KR-SunHiNeural",    "韩语女声"),
}

def step1_download(url):
    print(f"\n📥 STEP 1: 下载对标视频...")
    out = str(BASE / "reference/%(title)s.%(ext)s")
    cmd = [
        "yt-dlp", "-o", out,
        "--write-info-json",
        "--no-playlist",
        "--merge-output-format", "mp4",
    ]
    # 自动尝试用 Chrome cookies
    import shutil
    cmd += ["--cookies-from-browser", "chrome"]
    cmd.append(url)
    subprocess.run(cmd, check=True)
    videos = list((BASE / "reference").glob("*.mp4"))
    print(f"✅ 下载完成: {videos[-1].name}")
    return videos[-1]

def step2_transcribe(video_path):
    print(f"\n📝 STEP 2: 提取文案...")
    import whisper
    model = whisper.load_model("medium")
    result = model.transcribe(
        str(video_path), language=None,
        fp16=False,
        initial_prompt="以下是视频内容："
    )
    text = result["text"]
    lang = result["language"]
    print(f"✅ 提取完成，语言: {lang}")
    print(f"   文案预览: {text[:100]}...")
    return text, lang

def step3_rewrite(original_text, style):
    print(f"\n✍️  STEP 3: AI改写文案...")
    import urllib.request
    
    prompt = f"""你是一个专业的短视频文案改写专家。
    
原文案：
{original_text}

要求：
1. 保留核心信息和节奏结构
2. 改写成{style}风格
3. 开头要有强力钩子吸引注意
4. 结尾要有明确CTA（关注/点赞）
5. 字数控制在原文80%以内
6. 完全原创，不能和原文相似

直接输出改写后的文案，不要任何解释："""

    data = json.dumps({
        "model": "gemma4-64k:latest",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }).encode()
    
    req = urllib.request.Request(
        "http://127.0.0.1:11434/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
    
    new_text = result["choices"][0]["message"]["content"]
    print(f"✅ 改写完成")
    print(f"   改写预览: {new_text[:100]}...")
    return new_text

def step4_tts(text, voice, output_path, speed="+15%", pitch="+5Hz"):
    print(f"\n🎙️  STEP 4: 合成配音 ({voice})...")
    subprocess.run([
        "edge-tts",
        "--voice", voice,
        "--rate", speed,
        "--pitch", pitch,
        "--text", text,
        "--write-media", str(output_path)
    ], check=True)
    print(f"✅ 配音完成: {output_path}")

def step5_download_footage(keywords):
    print(f"\n🎬 STEP 5: 下载免费素材...")
    # 用 yt-dlp 从 Pixabay/Pexels 搜索免费素材
    search_query = f"ytsearch3:{keywords} stock footage no copyright"
    out = str(SOURCE / "%(title)s.%(ext)s")
    subprocess.run([
        "yt-dlp", "-o", out,
        "--no-playlist",
        "-f", "mp4[height<=1080]",
        search_query
    ], check=True)
    clips = list(SOURCE.glob("*.mp4"))
    print(f"✅ 下载了 {len(clips)} 段素材")
    return clips

def step6_compose(audio_path, video_clips, output_path):
    print(f"\n🎞️  STEP 6: 合成新视频...")
    
    # 获取音频时长
    r = subprocess.run([
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", str(audio_path)
    ], capture_output=True, text=True)
    audio_dur = float(r.stdout.strip())
    
    # 生成素材列表（循环填满音频时长）
    list_file = OUTPUT / "footage_list.txt"
    with open(list_file, "w") as f:
        total = 0
        i = 0
        while total < audio_dur:
            clip = video_clips[i % len(video_clips)]
            r2 = subprocess.run([
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0", str(clip)
            ], capture_output=True, text=True)
            dur = float(r2.stdout.strip())
            f.write(f"file '{clip}'\n")
            total += dur
            i += 1
    
    # 合成视频+新配音
    merged_video = OUTPUT / "merged_footage.mp4"
    subprocess.run([
        "/usr/local/bin/ffmpeg-full",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-i", str(audio_path),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac",
        "-shortest",
        str(merged_video), "-y"
    ], check=True)
    
    print(f"✅ 合成完成: {merged_video}")
    return merged_video

def main():
    print("=" * 50)
    print("🎬 对标视频复刻流水线")
    print("=" * 50)
    
    # 输入对标视频
    url = input("\n📎 输入对标视频URL: ").strip()
    
    # 选择改写风格
    print("\n✍️  选择改写风格：")
    print("   1) 美妆带货（活泼、种草感）")
    print("   2) 情绪疗愈（温柔、治愈感）")
    print("   3) 知识分享（专业、干货感）")
    print("   4) 搞笑娱乐（幽默、反差感）")
    style_map = {
        "1": "美妆带货，活泼种草",
        "2": "情绪疗愈，温柔治愈",
        "3": "知识分享，专业干货",
        "4": "搞笑娱乐，幽默反差"
    }
    style_num = input("选择 [1-4，默认1]: ").strip() or "1"
    style = style_map.get(style_num, style_map["1"])
    
    # 选择配音
    print("\n🎙️  选择配音声音：")
    for k, (v, desc) in VOICES.items():
        print(f"   {k}) {desc}")
    voice_num = input("选择 [1-9，默认1]: ").strip() or "1"
    voice, voice_desc = VOICES.get(voice_num, VOICES["1"])
    print(f"✅ 已选择: {voice_desc}")
    
    # 素材关键词
    keywords = input("\n🔍 输入素材搜索关键词（英文效果更好）: ").strip()
    if not keywords:
        keywords = "beauty makeup lifestyle"
    
    # 执行流程
    try:
        # STEP 1: 下载
        video = step1_download(url)
        
        # STEP 2: 提取文案
        text, lang = step2_transcribe(video)
        
        # STEP 3: 改写
        new_text = step3_rewrite(text, style)
        
        # 保存改写文案
        script_path = OUTPUT / "new_script.txt"
        with open(script_path, "w") as f:
            f.write(new_text)
        print(f"\n📄 改写文案已保存: {script_path}")
        
        # 人工确认文案
        print("\n" + "="*50)
        print("📋 改写后文案：")
        print(new_text)
        print("="*50)
        confirm = input("\n✅ 文案是否满意？直接回车继续，输入e修改: ").strip()
        if confirm.lower() == "e":
            print("请打开文件修改后按回车继续:")
            subprocess.run(["open", str(script_path)])
            input("修改完成后按回车继续...")
            new_text = open(script_path).read()
        
        # STEP 4: 配音
        audio_path = OUTPUT / "new_voice.mp3"
        step4_tts(new_text, voice, audio_path)
        
        # STEP 5: 下载素材
        clips = step5_download_footage(keywords)
        if not clips:
            print("⚠️  未找到素材，使用原视频画面")
            clips = [video]
        
        # STEP 6: 合成
        final = step6_compose(audio_path, clips, OUTPUT / "final_remake.mp4")
        
        # STEP 7: 加字幕
        print("\n📝 STEP 7: 加字幕...")
        subprocess.run([
            "python3",
            str(Path.home() / "video-pipeline-STABLE/make_srt.py")
        ])
        subprocess.run([
            "python3",
            str(Path.home() / "video-pipeline-STABLE/make_subtitle.py"),
            "highlight", ""
        ])
        
        timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
        final_with_sub = str(OUTPUT / f"remake_{timestamp}.mp4")
        subprocess.run([
            "/usr/local/bin/ffmpeg-full",
            "-i", str(final),
            "-vf", f"ass={OUTPUT}/subtitles.ass",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "copy",
            final_with_sub, "-y"
        ])
        
        print(f"\n{'='*50}")
        print(f"🎉 全流程完成！")
        print(f"   输出: {final_with_sub}")
        print(f"{'='*50}")
        
        os.system(f"open {OUTPUT}")
        
    except Exception as e:
        print(f"❌ 出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
