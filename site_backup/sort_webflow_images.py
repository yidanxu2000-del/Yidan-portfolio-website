#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sort_webflow_images.py

自动把 Webflow Assets 面板下载下来的、命名很乱的图片，按它们在
yidanxu.webflow.io 各页面上实际的用途，分类拷贝到规整的文件夹里。

用法：
    python3 sort_webflow_images.py /path/to/你下载图片的文件夹

不传参数的话，默认用当前目录下的 downloaded_images 文件夹。

会在图片所在目录旁边生成一个 sorted_images/ 文件夹，结构类似：
    sorted_images/
      shared/              <- 多个页面都用到的图（logo、封面等）
      home/
      about/
      work-xiaomi-auto/
      work-huawei/
      ...
      _unsorted/           <- 没匹配上的文件，需要你自己看一眼

原文件不会被删除或移动，只是复制（copy），你原来的下载文件夹不受影响。
"""

import sys
import os
import re
import shutil
import unicodedata
from collections import defaultdict

# 每个页面实际用到的原始文件名（从网站上抓取整理，与你 Webflow Assets 里
# 下载下来的文件名基本一致，只是大小写/后缀可能有差异，脚本会做模糊匹配）
MANIFEST = {
  "home": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "download.png", "images.png", "7.png", "截屏2024-12-27 23.46.01.png", "压缩后的cps简要gif图.gif", "截屏2023-12-29 16.49.13.png", "JDAStamped_GB Urify[69].PNG", "13.png", "Frame 31.png", "hero shot 3.png", "截屏2024-01-02 10.37.46.png", "handdraw1.png"],
  "about": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "1111111-p-1600.png", "59662cbb885e8137cc2cce63e5e650cf.png", "images.png", "download.png", "截屏2024-12-27 23.46.01.png", "截屏2024-12-27 23.50.39.png", "71ABWNB-YML.png", "817bec9ede06d69fbdcf0f6e824ae37c.png", "Siemens-Logo.png", "4118000ca15d0356d201804eb0bc58b1.png", "IMG_0940.PNG", "JDAStamped_GB Urify[69].PNG"],
  "work-xiaomi-auto": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "b97e04d5fe8e1d9df01a054c5d82dcc2.webp", "IMG_5085.jpg"],
  "work-project-4": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "NFT头图.jpg", "iMac 24\"@2x-p-2000.png", "Group 1.png", "NFT线框图1-p-2000.png", "Group 1000006246.png", "33333nft动效.gif", "编组.png", "Group 1000006244-p-2000.png", "Group 2-p-2000.png", "NFT 活动发现.png", "很哇塞素材店21-p-2000.jpg", "07.png", "13-p-2000.png"],
  "work-innovate-adhd": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "Untitled3 (2).gif", "Frame 1000001865.png", "Screen Recording 2026-03-28 at 19.49.34 (3).gif", "adult-adhd-self-report-scale.jpg", "PHOTO-2026-04-13-22-21-50.jpg", "Frame 1000002004.png", "Result - low.png", "087702777dbd70ac9ee680a5e2522b8a 2.png", "Group 1000001944-p-2000.png", "Group 1000001946-p-2000.png", "Group 1000001945-p-2000.png", "color.png", "Untitled (2).gif", "Group 1-p-2000.png"],
  "work-huawei": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "Group 3-p-1600.png", "Group 1000006256-p-2000.png", "Group 1000006258-p-2000.png", "ce7e6e24ac087e362a9db62ed4fa33e6-p-2000.png"],
  "work-res": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "44-p-1600.png", "44-p-2000.png", "46.png", "4-p-2000.png", "IMG_7920.JPG", "pollen sensors current vs. new - sRGB 1-p-2000.png", "Res Logo副本 2.png", "Group 39547.png", "截屏2025-01-07 20.04.11.png", "test_image_4 1-p-2000.png", "10-p-2000.png", "copy_6463161C-59FF-4F0E-AB18-9785565A5B70.gif", "Group 39575.png", "Group 39572.png", "Group 39571.png", "1-p-2000.png", "截屏2025-01-07 20.59.12.png", "Group 39552-p-2000.png", "截屏2025-01-16 14.15.56.png"],
  "work-pulpatronics": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "Frame 31-p-1600.png", "A4 - 113-p-1600.png", "image 4-p-1600.png", "Group 1000006242.png", "Group 1000006238-p-2000.png", "Group 1000006251-p-2000.png", "American Psycho-p-2000.jpg", "20-p-2000.jpg", "IMG_0774.png", "Group 1000006254-p-2000.png"],
  "work-entropy": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "hero shot 3.png", "across rca story board横版.png", "VR 3D story board-p-2000.png", "1.jpg", "3.jpg", "2.png", "536539C3-7127-4CE6-AE9E-4540D9F797FF.GIF", "1.gif", "2.gif", "1287A8D7-A84E-4CF6-876E-76513020A91A.GIF", "C10E82E2-8FE0-4C17-A7B5-ED6237C746DB.GIF", "0B19F4B8-2991-46F3-9519-86B135FF22D6.GIF", "AF600903-A365-4E97-92EC-8553F531B529.GIF", "copy_1675612C-C17C-432D-AE35-2D4C1B4B1CB2.GIF", "copy_0BD1F61B-E7BC-4A80-A94E-A1A89748F0B0.GIF"],
  "work-project-6": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "c3407148343fced077e7255df2de95 3.gif", "c3407148343fced077e7255df2de95 (1).gif", "c3407148343fced077e7255df2de95 2.gif", "c3407148343fced077e7255df2de95 4.gif", "c3407148343fced077e7255df2de95 5.gif", "压缩后的cps简要gif图.gif", "截屏2024-04-14 00.50.05.png", "copy_271F6E1A-EBBA-4DD7-BE9F-6CED702CCC41.GIF", "截屏2024-04-14 00.02.18.png", "1.png", "2.jpeg", "4.png", "截屏2024-04-14 00.33.11.png", "截屏2024-04-14 00.32.58.png", "截屏2024-04-14 00.32.44.png", "截屏2024-04-14 00.42.37.png", "截屏2024-04-14 00.42.26.png", "截屏2024-01-02 10.30.12-p-2000.png", "截屏2024-01-02 10.35.39.jpg", "截屏2024-01-02 11.38.19-p-2000.png", "截屏2024-01-02 10.37.46-p-2000.png", "截屏2024-01-02 10.37.07.png", "截屏2024-01-02 10.37.22-p-2000.png", "截屏2024-01-02 10.38.44-p-2000.png", "截屏2024-01-02 10.32.08.png"],
  "work-project-2": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "22222副本.png", "编组 10.png", "2.png", "编组 11.png", "1.png", "编组 32.png", "编组 5.png", "编组 31.png", "1.jpeg", "3.png", "4.png", "2.jpeg", "编组 34.png", "编组 18.png", "截屏2023-12-29 16.49.13.png"],
  "work-hand-drawing": ["Yidan's Portfolio-p-500.png", "menu-icon.png", "截屏2024-09-18 23.02.08 1-p-1600.png", "IMG_9340-p-1600.jpg", "IMG_8855 1-p-1600.png", "Group 1000006239-p-1600.png", "Group 1000006240-p-1600.png", "Group 1000006241.png"],
}

# Webflow 会给同一张图生成多种尺寸/格式，这些后缀在比较文件名时先去掉
SIZE_SUFFIX_RE = re.compile(r"-p-(500|800|1000|1600|2000|3200)$", re.IGNORECASE)
# 同一张图可能同时存在多种格式（avif 是 Webflow 自动生成的现代格式副本），
# 按下面优先级只保留一份，减少重复文件
EXT_PRIORITY = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif"]


def norm_base(filename: str) -> str:
    """去掉扩展名和 Webflow 的尺寸后缀，统一大小写/全角半角，用于模糊匹配"""
    name, _ext = os.path.splitext(filename)
    name = unicodedata.normalize("NFKC", name)
    name = SIZE_SUFFIX_RE.sub("", name)
    return name.strip().lower()


def build_lookup():
    """base_name -> list of page slugs that use it"""
    lookup = defaultdict(set)
    for page, files in MANIFEST.items():
        for f in files:
            lookup[norm_base(f)].add(page)
    return lookup


def ext_rank(filename: str) -> int:
    ext = os.path.splitext(filename)[1].lower()
    return EXT_PRIORITY.index(ext) if ext in EXT_PRIORITY else len(EXT_PRIORITY)


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "downloaded_images"
    src_dir = os.path.abspath(src_dir)
    if not os.path.isdir(src_dir):
        print(f"找不到文件夹: {src_dir}")
        print("用法: python3 sort_webflow_images.py /你下载图片的文件夹路径")
        sys.exit(1)

    dest_root = os.path.join(os.path.dirname(src_dir), "sorted_images")
    os.makedirs(dest_root, exist_ok=True)

    lookup = build_lookup()

    # 按 (目标文件夹, 归一化文件名) 分组，同一组内按格式优先级只留一份
    groups = defaultdict(list)   # (target_folder, norm_name) -> [source_filenames]
    unsorted = []

    for fname in os.listdir(src_dir):
        full = os.path.join(src_dir, fname)
        if not os.path.isfile(full):
            continue
        nb = norm_base(fname)
        pages = lookup.get(nb)
        if not pages:
            unsorted.append(fname)
            continue
        target_folder = "shared" if len(pages) > 1 else next(iter(pages))
        groups[(target_folder, nb)].append(fname)

    copied = 0
    skipped_dupe = 0
    per_folder_count = defaultdict(int)

    for (folder, _nb), fnames in groups.items():
        fnames.sort(key=ext_rank)
        chosen = fnames[0]
        skipped_dupe += len(fnames) - 1
        out_dir = os.path.join(dest_root, folder)
        os.makedirs(out_dir, exist_ok=True)
        shutil.copy2(os.path.join(src_dir, chosen), os.path.join(out_dir, chosen))
        copied += 1
        per_folder_count[folder] += 1

    if unsorted:
        out_dir = os.path.join(dest_root, "_unsorted")
        os.makedirs(out_dir, exist_ok=True)
        for fname in unsorted:
            shutil.copy2(os.path.join(src_dir, fname), os.path.join(out_dir, fname))

    print(f"完成！结果在: {dest_root}\n")
    print("各文件夹图片数：")
    for folder, count in sorted(per_folder_count.items()):
        print(f"  {folder:<20} {count} 张")
    print(f"\n跳过的重复格式副本（同一张图的 avif/png 等重复文件）：{skipped_dupe} 个")
    print(f"没能自动匹配、放进 _unsorted/ 的文件：{len(unsorted)} 个")
    if unsorted:
        print("（这些大多是老草稿/没在现在网站用到的素材，扫一眼有没有想要的，剩下可以直接忽略）")


if __name__ == "__main__":
    main()
