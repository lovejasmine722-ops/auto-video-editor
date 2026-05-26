import subprocess, json
from pathlib import Path

SOURCE = Path.home() / "video-pipeline/source"
TRIMMED = Path.home() / "video-pipeline/output/trimmed3"
TRIMMED.mkdir(parents=True, exist_ok=True)

SILENCE_THRESHOLD = -30
MIN_SILENCE = 0.15

def get_duration(path):
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]
    return float(subprocess.run(cmd, capture_output=True, text=True).stdout.strip())

def get_silence_segments(path):
    cmd = ["ffmpeg", "-i", str(path), "-af", f"silencedetect=noise={SILENCE_THRESHOLD}dB:d={MIN_SILENCE}", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    silences, start = [], None
    for line in result.stderr.split('\n'):
        if 'silence_start' in line:
            start = float(line.split('silence_start: ')[1])
        if 'silence_end' in line and start is not None:
            end = float(line.split('silence_end: ')[1].split(' ')[0])
            silences.append((start, end))
            start = None
    return silences

def remove_silence(input_path, output_path):
    print(f"✂️  处理: {Path(input_path).name}")
    duration = get_duration(input_path)
    silences = get_silence_segments(input_path)

    keep, prev_end = [], 0
    for s_start, s_end in silences:
        if s_start > prev_end + 0.1:
            keep.append((prev_end, s_start))
        prev_end = s_end
    if prev_end < duration - 0.1:
        keep.append((prev_end, duration))

    if not keep:
        print(f"   ⚠️  没有检测到气口，直接复制")
        subprocess.run(["cp", str(input_path), str(output_path)])
        return

    n = len(keep)
    filter_parts = []
    for i, (s, e) in enumerate(keep):
        filter_parts.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}];")
        filter_parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}];")
    v_concat = "".join(f"[v{i}]" for i in range(n))
    a_concat = "".join(f"[a{i}]" for i in range(n))
    filter_parts.append(f"{v_concat}concat=n={n}:v=1:a=0[vout];")
    filter_parts.append(f"{a_concat}concat=n={n}:v=0:a=1[aout]")

    subprocess.run([
        "ffmpeg", "-i", str(input_path),
        "-filter_complex", "".join(filter_parts),
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path), "-y"
    ], check=True, capture_output=True)
    print(f"   ✅ 完成: {Path(output_path).name}")

for f in sorted(SOURCE.glob("*.MP4")) + sorted(SOURCE.glob("*.mp4")):
    out = TRIMMED / f"{f.stem}_cut.mp4"
    remove_silence(f, out)

print("✅ 去气口全部完成")
