import sys, re
from pathlib import Path

def parse_srt(path):
    blocks, current = [], {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.isdigit():
            if current: blocks.append(current)
            current = {"id": int(line)}
        elif "-->" in line:
            def to_sec(t):
                h,m,s = t.replace(",",".").split(":")
                return int(h)*3600+int(m)*60+float(s)
            s,e = line.split(" --> ")
            current["start"] = to_sec(s.strip())
            current["end"] = to_sec(e.strip())
        elif line and "start" in current and "text" not in current:
            current["text"] = line
    if current: blocks.append(current)
    return blocks

def wrap(text, max_len=12):
    """超过max_len个字自动换行"""
    if len(text) <= max_len:
        return text
    mid = len(text) // 2
    return text[:mid] + r"\N" + text[mid:]

def sec_to_ass(s):
    h,m = divmod(int(s),3600); m,sc = divmod(m,60)
    cs = int((s-int(s))*100)
    return f"{h}:{m:02}:{sc:02}.{cs:02}"

# 接收关键词
if len(sys.argv) > 1 and sys.argv[1].strip():
    keywords = [w.strip() for w in re.split(r'[,，\s]+', sys.argv[1]) if w.strip()]
    print(f"✅ 关键词高亮: {keywords}")
else:
    keywords = []
    print("⏭  无关键词，全部白色字幕")

srt = Path.home() / "video-pipeline/output/subtitles.srt"
ass = Path.home() / "video-pipeline/output/subtitles.ass"
subs = parse_srt(srt)

header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,STHeiti Medium,44,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,1,2,1,2,20,20,150,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

events = []
for sub in subs:
    text = wrap(sub["text"])
    s = sec_to_ass(sub["start"])
    e = sec_to_ass(sub["end"])
    styled = ""
    i = 0
    while i < len(text):
        # 跳过换行符
        if text[i:i+2] == r"\N":
            styled += r"\N"
            i += 2
            continue
        matched = False
        for kw in keywords:
            if text[i:i+len(kw)] == kw:
                styled += r"{\c&H0000FFFF&\b1}" + kw + r"{\c&H00FFFFFF&\b0}"
                i += len(kw)
                matched = True
                break
        if not matched:
            styled += text[i]
            i += 1
    events.append(f"Dialogue: 0,{s},{e},Default,,0,0,0,,{styled}")

with open(ass, "w", encoding="utf-8") as f:
    f.write(header + "\n".join(events))

print(f"✅ ASS字幕生成完成，共{len(subs)}条")
