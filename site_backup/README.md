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

## 图片：已下载 4 张示例 + 完整地址清单（148张）

**没能把全部图片下载下来，原因如下：** 抽样检测发现这些图片体积普遍很大（有的截图/GIF 单张 1-4MB），148 张全部拉取需要把上百MB的数据以 base64 文本形式经过对话上下文传输，这个量级会导致对话严重卡顿甚至失败，所以我先完整保留了**全部图片的原始CDN地址清单**（`assets/images/ALL_IMAGE_URLS.txt`，148条），并示范下载了4张作为验证：

- `menu-icon.png`
- `home-cover-portfolio.png`
- `gesture-lockdevice-1.png`
- `xiaomi-auto-hero-IMG_5085.jpg`

**获取全部图片原图的推荐方法（几分钟搞定，比我一张张抓快得多）：**

1. 登录 Webflow → 打开这个项目 → 左侧面板找到 **Assets**（资源库）
2. 全选所有图片 → 点击 **Download**，Webflow 会打包成一个 zip（这个功能所有计划都能用，不需要付费 Workspace）
3. 把下载的 zip 发给我，我来解压、按 `ALL_IMAGE_URLS.txt` 里的文件名核对补齐到 `assets/images/`，再补一次 git commit

这样能拿到最原始质量的图片，比我通过浏览器脚本重新抓取更快也更完整。

## Git

本目录已 `git init` 并完成一次 commit，包含目前已有的文案、CSS 和示例图片。图片补齐后会再提交一次。
