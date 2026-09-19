#!/usr/bin/env python3
"""
build_contact_sheet.py — 把多张页面截图拼成一张对比图（跨页面一致性检查用）

为什么需要：单页 UI-SPEC 看不出「A 页的主操作按钮到了 B 页变成次要样式」。
把所有页面截图拼在一张图上，人和大模型都能横向扫一眼找出不一致。

用法:
    python3 build_contact_sheet.py shots/*.png --out contact-sheet.png
    python3 build_contact_sheet.py shots/ --cols 3 --label --width 380 --outline-error

依赖: Pillow（可选，没装也能跑降级版）
      pip install pillow
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
except ImportError:
    Image = None  # type: ignore


def collect_images(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for i in inputs:
        p = Path(i)
        if p.is_dir():
            files += sorted([x for x in p.iterdir()
                             if x.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}])
        elif p.exists():
            files.append(p)
        elif any(ch in i for ch in "*?["):
            import glob
            files += [Path(x) for x in sorted(glob.glob(i))]
    # 去重保序
    seen, out = set(), []
    for f in files:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            out.append(f)
    return out


def outlines_of_red(img) -> tuple[int, int, int, int]:
    """粗略找白色/空洞区域占比，用于提示「可能是空白渲染失败」"""
    small = img.convert("RGB").resize((64, 64))
    pixels = list(small.getdata())
    white = sum(1 for p in pixels if p[0] > 245 and p[1] > 245 and p[2] > 245)
    return len(pixels), white, 0, 0


def main() -> int:
    ap = argparse.ArgumentParser(description="拼接截图 contact sheet")
    ap.add_argument("inputs", nargs="*", default=["shots"])
    ap.add_argument("--out", default="contact-sheet.png")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--width", type=int, default=420, help="每格宽度 px")
    ap.add_argument("--label", action="store_true", help="在每格下方标注文件名")
    ap.add_argument("--check-blank", action="store_true", help="同时报告疑似空白/渲染失败的图")
    args = ap.parse_args()

    files = collect_images(args.inputs)
    if not files:
        print("没找到任何图片。示例：python3 build_contact_sheet.py shots/*.png", file=sys.stderr)
        return 2

    if Image is None:
        print("未安装 Pillow，改用系统 sips 做降级拼接…")
        # macOS 降级路径：先统一宽度再纵向拼接
        cmd = [str(f) for f in files]
        subprocess.run(["sips", "--resampleWidth", str(args.width)] + cmd, check=False)
        print("已统一宽度，但仍需手工拼接。建议安装 Pillow：pip install pillow")
        return 1

    thumb_h = int(args.width * 0.75)
    label_h = 26 if args.label else 0
    pad = 16
    cols = max(1, args.cols)
    rows = (len(files) + cols - 1) // cols
    sheet_w = cols * (args.width + pad) + pad
    sheet_h = rows * (thumb_h + label_h + pad) + pad

    sheet = Image.new("RGB", (sheet_w, sheet_h), (245, 245, 244))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 13)
    except Exception:
        font = ImageFont.load_default()

    warnings: list[str] = []
    for idx, f in enumerate(files):
        try:
            img = Image.open(f).convert("RGB")
        except Exception as e:
            warnings.append(f"{f.name}: 无法打开 ({e})")
            continue
        total, white, _, _ = outlines_of_red(img)
        if args.check_blank and white / total > 0.97:
            warnings.append(f"{f.name}: 几乎全白，可能是渲染失败或空白页")
        img.thumbnail((args.width, thumb_h))
        r, c = divmod(idx, cols)
        x = pad + c * (args.width + pad)
        y = pad + r * (thumb_h + label_h + pad)
        sheet.paste(img, (x, y))
        draw.rectangle([x - 1, y - 1, x + args.width, y + thumb_h], outline=(200, 200, 198))
        if args.label:
            draw.text((x, y + thumb_h + 6), f.name, fill=(60, 60, 58), font=font)

    sheet.save(args.out)
    print(f"✅ contact sheet 已生成：{args.out}  （{len(files)} 张，{cols} 列）")
    if warnings:
        print("\n⚠️  需要人工确认：")
        for w in warnings:
            print(f"   - {w}")
    print("\n下一步：把这张图丢给大模型，用 prompts.md 里的 P12 做跨页面一致性检查。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
