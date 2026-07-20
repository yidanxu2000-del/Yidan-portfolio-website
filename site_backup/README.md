# yidanxu.webflow.io 网站备份

备份时间：2026-07-19
来源网站：https://yidanxu.webflow.io/ （Webflow 免费/学生 Workspace 计划，无官方 Export code 权限，本备份通过浏览器抓取生成）

## 已完整备份的内容

### 页面文案（13页，`pages/`）
每个页面的正文文字已完整提取，逐字无误：

- `home.md` — 首页
- `about.md` — About
- `work-xiaomi-auto.md`
- `work-project-4.md`
- `work-innovate-adhd.md`
- `work-huawei.md`
- `work-res.md`
- `work-pulpatronics.md`
- `work-entropy.md`
- `work-project-6.md`
- `work-project-2.md`
- `work-hand-drawing.md`

### 自定义样式（`assets/css/yidanxu.webflow.shared.css`）
这是网站真正承载视觉设计的 CSS 文件（58.6KB），已完整下载，可作为重设计时的参考基准（颜色、字体、间距等原始设定都在里面）。

未下载的第三方/通用文件（不是你的自定义设计内容，不影响重建）：
- Google Fonts (Montserrat, Changa One)
- Microsoft Clarity 用户行为分析埋点脚本
- jQuery、Webflow 运行时 JS（`webflow.schunk...js` 等，这是 Webflow 平台自己的通用交互引擎代码，React 重写时不会用到）

### 图片：已全部下载并分类整理完毕

后续通过 Webflow 后台 Assets 面板导出了全部原图（约400个文件，含同一张图的 avif/png 等重复格式），存放在 `webflow image/` 原始文件夹里。又写了 `sort_webflow_images.py` 脚本，按图片在网站各页面的实际用途自动分类，运行后生成：

```
sorted_images/
  shared/              多个页面共用的图（logo、封面等）
  home/
  about/
  work-xiaomi-auto/
  work-huawei/
  work-res/
  work-pulpatronics/
  work-entropy/
  work-innovate-adhd/
  work-project-2/
  work-project-4/
  work-project-6/
  work-hand-drawing/
  _unsorted/           没能自动匹配上的老素材/草稿图，多为网站现在没用到的文件
```

同一张图的 avif/png 重复格式脚本会自动去重只保留一份。`assets/images/ALL_IMAGE_URLS.txt` 里原来记录的148条 CDN 地址仍保留作为交叉核对参考，但现在实际使用的是 `sorted_images/` 里的本地文件。

## Git

本仓库已推送到正式的 GitHub 仓库：https://github.com/yidanxu2000-del/Yidan-portfolio-website 。目前 `site_backup/` 是原网站的存档，新的 React 版本正在仓库根目录的 `site/` 文件夹里由 Claude Code 搭建和迭代，两者互不影响——`site_backup/` 保持只读存档，不会再改动。
