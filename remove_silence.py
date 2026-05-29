import subprocess, json, os, sys
from pathlib import Path

def get_silence_segments(video_path, min_silence=0.2, threshold=-30):
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-af", f"silencedetect=noise={threshold}dB:d={min_silence}",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stderr
    
    silences = []
    start = None
    for line in output.split('\n'):
        if 'silence_start' in line:
            start = float(line.split('silence_start: ')[1])
        if 'silence_end' in line and start is not None:
            end = float(line.split('silence_end: ')[1].split(' ')[0])
            silences.append((start, end))
            start = None
    return silences

def get_duration(video_path):
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
           "-of", "csv=p=0", str(video_path)]
    return float(subprocess.run(cmd, capture_output=True, text=True).stdout.strip())

def remove_silence(input_path, output_path, min_silence=0.2, threshold=-30):
    print(f"\n处理: {Path(input_path).name}")
    duration = get_duration(input_path)
    silences = get_silence_segments(input_path, min_silence, threshold)
    print(f"  总时长: {duration:.1f}s，检测到 {len(silences)} 段静音")
    
    # 计算需要保留的片段
    keep = []
    prev_end = 0
    for s_start, s_end in silences:
        if s_start > prev_end + 0.1:
            keep.append((prev_end, s_start))
        prev_end = s_end
    if prev_end < duration - 0.1:
        keep.append((prev_end, duration))
    
    print(f"  保留 {len(keep)} 段，预计时长: {sum(e-s for s,e in keep):.1f}s")
    
    # 生成 filter_complex
    n = len(keep)
    filter_parts = []
    for i, (s, e) in enumerate(keep):
        filter_parts.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}];")
        filter_parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}];")
    
    v_concat = "".join(f"[v{i}]" for i in range(n))
    a_concat = "".join(f"[a{i}]" for i in range(n))
    filter_parts.append(f"{v_concat}concat=n={n}:v=1:a=0[vout];")
    filter_parts.append(f"{a_concat}concat=n={n}:v=0:a=1[aout]")
    
    filter_complex = "".join(filter_parts)
    
    cmd = [
        "ffmpeg", "-i", str(input_path),
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path), "-y"
    ]
    subprocess.run(cmd, check=True)
    print(f"  ✅ 输出: {output_path}")

# 处理所有素材
source_dir = Path.home() / "video-pipeline/source"
out_dir = Path.home() / "video-pipeline/output/trimmed3"
out_dir.mkdir(parents=True, exist_ok=True)

for f in sorted(source_dir.glob("*.MP4")):
    out = out_dir / f"{f.stem}_cut.mp4"
    remove_silence(f, out, min_silence=0.2, threshold=-30)

print("\n✅ 全部处理完成！")
