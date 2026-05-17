import sys, re
from pathlib import Path

FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
FONTSIZE = 44        # 统一字号
MARGIN_V = 150       # 统一位置
MAX_CHARS = 12       # 每行最多字数

style = sys.argv[1] if len(sys.argv) > 1 else "highlight"
keywords_raw = sys.argv[2] if len(sys.argv) > 2 else ""
keywords = [w.strip() for w in re.split(r'[,，\s]+', keywords_raw) if w.strip()]

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

def wrap(text):
    if len(text) <= MAX_CHARS:
        return text
    mid = len(text) // 2
    return text[:mid] + r"\N" + text[mid:]

def sec_to_ass(s):
    h,m = divmod(int(s),3600); m,sc = divmod(m,60)
    cs = int((s-int(s))*100)
    return f"{h}:{m:02}:{sc:02}.{cs:02}"

def highlight_text(text):
    styled = ""
    i = 0
    while i < len(text):
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
    return styled

srt = Path.home() / "video-pipeline/output/subtitles.srt"
ass = Path.home() / "video-pipeline/output/subtitles.ass"
subs = parse_srt(srt)

header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,STHeiti Medium,{FONTSIZE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,1,2,1,2,20,20,{MARGIN_V},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

events = []
for sub in subs:
    raw = sub["text"]
    text = wrap(raw)
    s = sec_to_ass(sub["start"])
    e = sec_to_ass(sub["end"])

    if style == "highlight":
        styled = highlight_text(text)

    elif style == "fade":
        dur = sub["end"] - sub["start"]
        fd = min(0.3, dur/3)
        # ASS 淡入淡出用 fad 标签
        styled = f"{{\\fad({int(fd*1000)},{int(fd*1000)})}}" + text

    elif style == "karaoke":
        # 整句黄色
        styled = r"{\c&H0000FFFF&}" + text

    else:  # normal
        styled = text

    events.append(f"Dialogue: 0,{s},{e},Default,,0,0,0,,{styled}")

with open(ass, "w", encoding="utf-8") as f:
    f.write(header + "\n".join(events))

print(f"✅ {style} 字幕生成完成，共{len(subs)}条，关键词:{keywords}")
