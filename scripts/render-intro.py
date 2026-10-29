"""用已脱敏的安卓截图生成 120 秒中文图文动画与原创配乐。

依赖 Pillow、numpy、ffmpeg、ffprobe；输出默认放入忽略的本地制品目录。
"""
import argparse
import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def font(size, bold=False):
    candidates = [Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
                  Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")]
    path = next((p for p in candidates if p.exists()), None)
    if not path:
        raise RuntimeError("请安装微软雅黑或 Noto Sans CJK 中文字体")
    return ImageFont.truetype(str(path), size)


def backdrop():
    y, x = np.mgrid[0:1080, 0:1920]
    glow = np.exp(-((x-1430)**2 / 700**2 + (y-330)**2 / 650**2))
    pixels = np.stack([12+10*glow, 22+34*glow, 39+45*glow], axis=2).astype(np.uint8)
    return Image.fromarray(pixels)


def write_card(shot, number, total, folder):
    canvas = backdrop()
    draw = ImageDraw.Draw(canvas)
    draw.text((122, 90), "RENovel", font=font(40, True), fill="#80E3D2")
    draw.rounded_rectangle((345, 96, 492, 141), radius=22, fill="#213E50")
    draw.text((371, 101), "1.0.0", font=font(25, True), fill="#E6F5F6")
    draw.text((124, 245), shot["eyebrow"], font=font(28), fill="#80E3D2")
    for index, line in enumerate(shot["title"].split("\n")):
        draw.text((118, 300+index*88), line, font=font(66, True), fill="#F4F8FC")
    top = 535
    for index, line in enumerate(shot["lines"]):
        draw.ellipse((126, top+index*70+17, 137, top+index*70+28), fill="#80E3D2")
        draw.text((160, top+index*70), line, font=font(30), fill="#C3D2E2")
    draw.text((125, 950), "原生应用实拍  ·  原创演示内容  ·  小说名称已脱敏", font=font(22), fill="#8AABBE")
    draw.rounded_rectangle((124, 1003, 1054, 1009), radius=3, fill="#284453")
    draw.rounded_rectangle((124, 1003, 124+930*(number+1)/total, 1009), radius=3, fill="#80E3D2")
    target = folder / f"card-{number:02}.png"
    canvas.save(target)
    return target


def device_image(source, target, desktop=False):
    image = Image.open(source).convert("RGB")
    bounds = (680, 480) if desktop else (420, 920)
    image.thumbnail(bounds, Image.Resampling.LANCZOS)
    size = (712, 512) if desktop else (452, 962)
    phone = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(phone)
    draw.rounded_rectangle((0, 0, size[0]-1, size[1]-1), radius=35, fill="#101A25", outline="#688896", width=3)
    x, y = (size[0]-image.width)//2, (size[1]-image.height)//2
    phone.paste(image, (x, y))
    phone.save(target)


def music(target, seconds=120):
    """自写的 96 BPM 五声音阶琶音、和弦与轻鼓点，无采样、无人声。"""
    rate = 44100
    samples = np.zeros(int(seconds*rate), dtype=np.float64)
    beat = 60/96
    rng = np.random.default_rng(1000)

    def tone(start, duration, midi, level):
        length = min(int(duration*rate), len(samples)-int(start*rate))
        if length <= 0:
            return
        t = np.arange(length)/rate
        frequency = 440*2**((midi-69)/12)
        envelope = np.minimum(t/.025, 1)*np.exp(-t/(duration*.43))
        end = np.minimum((duration-t)/.09, 1).clip(0, 1)
        voice = np.sin(2*np.pi*frequency*t)+.18*np.sin(4*np.pi*frequency*t)
        offset = int(start*rate)
        samples[offset:offset+length] += voice*envelope*end*level

    chords = [(48, 55, 60, 64), (45, 52, 57, 60), (41, 48, 53, 57), (43, 50, 55, 62)]
    for bar in range(math.ceil(seconds/(beat*4))):
        start = bar*4*beat
        chord = chords[bar % len(chords)]
        for note in chord:
            tone(start, beat*4, note, .042)
        for step in range(8):
            tone(start+step*beat/2, beat*1.1, chord[(step*3+bar)%4]+12, .052)
        for pulse in range(4):
            at = int((start+pulse*beat)*rate)
            length = min(int(.13*rate), len(samples)-at)
            if length <= 0:
                continue
            t = np.arange(length)/rate
            if pulse % 2 == 0:
                drum = np.sin(2*np.pi*(68*t-120*t*t))*np.exp(-t*33)*.07
            else:
                drum = rng.normal(0, .018, length)*np.exp(-t*50)
            samples[at:at+length] += drum
    fade = np.minimum(np.arange(len(samples))/(rate*2), 1)
    fade *= np.minimum((len(samples)-np.arange(len(samples)))/(rate*3), 1)
    samples *= fade
    samples /= max(1, np.max(np.abs(samples))/.65)
    stereo = np.stack([samples, .97*samples+.03*np.roll(samples, 700)], axis=1)
    with wave.open(str(target), "wb") as stream:
        stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(rate)
        stream.writeframes((stereo*32767).astype("<i2").tobytes())


def run(command):
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots", type=Path, default=Path("docs/images"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/private/promo"))
    parser.add_argument("--timeline", type=Path, default=Path("docs/promo/timeline.json"))
    args = parser.parse_args()
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("需要 ffmpeg 与 ffprobe")
    shots = json.loads(args.timeline.read_text(encoding="utf-8"))
    assert sum(shot["seconds"] for shot in shots) == 120
    args.output.mkdir(parents=True, exist_ok=True)
    clips = []
    for i, shot in enumerate(shots):
        print(f"渲染 {i+1}/{len(shots)}：{shot['eyebrow']}", flush=True)
        card = write_card(shot, i, len(shots), args.output)
        phases = shot.get("phases", [{"image": shot["image"], "seconds": shot["seconds"]}])
        assert sum(phase["seconds"] for phase in phases) == shot["seconds"]
        for part, phase in enumerate(phases):
            device = args.output / f"device-{i:02}-{part}.png"
            desktop = phase.get("layout") == "desktop"
            device_image(args.screenshots/phase["image"], device, desktop)
            clip = args.output/f"clip-{i:02}-{part}.mp4"
            seconds = phase["seconds"]
            x, y = (1090, 330) if desktop else (1288, 55)
            # A gentle zoom and slide introduce each real screen; short fades
            # connect the before/after views without inventing app content.
            filters = f"[1:v]scale=w='iw*(1+0.018*sin(t*0.45))':h='ih*(1+0.018*sin(t*0.45))':eval=frame[device];[0:v][device]overlay=x='{x}+80*exp(-3*t)':y='{y}+5*sin(t*0.8)':eval=frame,fade=t=in:st=0:d=0.3,fade=t=out:st={seconds-.3}:d=0.3,format=yuv420p[v]"
            run([ffmpeg,"-y","-loglevel","error","-loop","1","-framerate","30","-i",str(card),"-loop","1","-framerate","30","-i",str(device),"-filter_complex",filters,"-map","[v]","-t",str(seconds),"-r","30","-c:v","libx264","-preset","fast","-crf","22","-threads","4",str(clip)])
            clips.append(clip)
    listing = args.output/"clips.txt"
    listing.write_text("\n".join(f"file '{p.name}'" for p in clips),encoding="utf-8")
    soundtrack = args.output/"original-instrumental.wav"
    music(soundtrack)
    video = args.output/"Renovel_1.0.0_intro_zh-CN.mp4"
    run([ffmpeg,"-y","-loglevel","error","-f","concat","-safe","0","-i",str(listing),"-i",str(soundtrack),"-c:v","copy","-c:a","aac","-b:a","160k","-t","120","-movflags","+faststart",str(video)])
    details = json.loads(subprocess.check_output([ffprobe,"-v","error","-show_streams","-show_format","-of","json",str(video)]))
    stream = next(s for s in details["streams"] if s["codec_type"] == "video")
    assert (stream["width"],stream["height"],stream["r_frame_rate"]) == (1920,1080,"30/1")
    assert abs(float(details["format"]["duration"])-120)<.1
    assert video.stat().st_size <= 80*1024*1024
    (args.output/"verification.json").write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding="utf-8")
    run([ffmpeg,"-y","-loglevel","error","-ss","2","-i",str(video),"-frames:v","1","-update","1",str(args.output/"video-poster.jpg")])
    print(video.resolve())


if __name__ == "__main__":
    main()
