[English](README_EN.md) | 中文

# 人和 AI，终于能一起好好用浏览器了

你在前台，它在后台。你让它帮忙，它就接管你的页面——点按钮、填表单、传文件、操作富文本编辑器。你让它自己查，它悄悄开 Tab 并行调研。登录态共享，安全有边界，5 个 AI 平台通用。

---

## 先说清楚：这不是一个"网页阅读器"

大多数 AI 联网方案只能**读**网页——抓取文本、提取内容、返回摘要。

Browser Control Skill 能**操控**你的浏览器：

- 点击按钮、链接、菜单项——包括 React/Vue 等框架渲染的动态元素
- 填写表单——兼容原生 input 和 React 受控组件，值不会被框架吞掉
- 在 Notion、Slack、Gmail 的富文本编辑器里打字——通过 CDP 的 `Input.insertText`，连 contenteditable 区域也能写
- 键盘快捷键——Enter 提交、Tab 切字段、Ctrl+A 全选
- 上传文件——绕过系统文件对话框，直接把本地文件塞给 `<input type="file">`
- 操作下拉框和悬停菜单——标准 `<select>` 和自定义 dropdown 都行
- 截图 + 元素标注——给每个可交互元素编号，截图后一目了然
- 拦截 Console 日志和网络请求——调试 Web 应用时直接看到后台发生了什么

**这是完整的浏览器操控，不是只读的内容提取。**

---

## 但现在的问题是：人和 AI 没法共用一个浏览器

你已经在 Chrome 里登录了公司内网、企业后台、各种 SaaS 平台。你想让 AI 帮你做点事——

但现有方案全在某个环节掉链子：

**Playwright / Puppeteer** — 开一个全新的浏览器。你的登录态？不存在。你得重新登录一遍，或者折腾 Cookie 导出。它和你用的不是同一个 Chrome。

**Chrome DevTools MCP** — 能连你的 Chrome，但你和 AI 没法同时操作。Agent 一动，你的页面就跳。也没有安全防护——你的银行页面它也能点。

**纯 AppleScript 方案** — 只能操作「最前面的窗口」。你在看文档，AI 要填表单——它直接把你的页面抢走了。串行操作，查 5 个网站等 5 倍时间。

**WebFetch / curl** — 根本进不了登录页面。

它们的共同问题：**没有一个方案能让人和 AI 和平共处在同一个浏览器里。**

---

## 解法：前台协作，后台并行，共享一个 Chrome

Browser Control Skill 不是给 AI 单独开一个浏览器——而是让 AI 学会**和你共用一个 Chrome**。

### 两种模式，按场景自动切换

```
/browse here 帮我在这个页面上填表      ← 你看着它做，操作你眼前的页面
/browse bg 同时调研这 5 家公司的官网     ← 它在后台悄悄干，你该干嘛干嘛
/browse 帮我查一下这个公司的信息        ← 自动判断用前台还是后台
```

| 模式 | 技术原理 | 用户体验 |
|------|---------|---------|
| **前台** (here) | AppleScript，操作你的 `front window` | 你看着 AI 操作你眼前的页面，每一步都看得到 |
| **后台** (bg) | CDP 协议，通过 `targetId` 精确寻址 | AI 开自己的 Tab，你的页面纹丝不动 |

前台走 UI 层，后台走协议层。这就是为什么后台模式能做到**完全不碰你的 Tab**——它根本不通过界面操作，而是通过 Chrome 的调试协议直接和目标 Tab 通信。

### 你可以这样用

**场景 1：你在看一个页面，需要 AI 帮忙操作**

你打开了一个内部审批系统，想让 AI 帮你填写表单。

```
/browse here 帮我把这个表单里的申请人改成张三，部门填研发部，然后上传桌面上的附件.pdf
```

AI 直接操作你眼前的页面——填文本框、选下拉菜单、上传文件。你看着它一步步做，确认无误再提交。

**场景 2：你在工作，让 AI 后台帮你调研**

你在写代码，同时需要 AI 帮你查 5 家竞品的最新动态。

```
/browse bg 帮我同时调研这 5 家公司的官网，总结它们最近的产品更新
```

AI 在后台开 5 个 Tab，派 5 个子 Agent 并行调研，各查各的。你的 Chrome 界面完全不受影响。查完了它汇总结果给你。

**场景 3：操作企业后台**

你已经登录了 Salesforce / Jira / 飞书后台。AI 直接继承你的登录态——不只是读数据，还能操作：

```
/browse here 在飞书多维表格里新建一行，填上这些字段
/browse bg 从 Jira 上把这个 Sprint 的所有 ticket 标题和状态提取出来
/browse here 帮我在 Notion 里写一段会议纪要
```

读取、点击、填写、上传——都在你已认证的会话里完成，不需要 API Token。

---

## 安全：共享浏览器，但有明确的规矩

AI 操作的是你的真实浏览器、你的真实登录态。所以安全边界必须够硬：

**第一层：域名黑名单** — 银行（Chase、招商银行）、支付（PayPal、支付宝）、认证页面（accounts.google.com、okta）、云控制台（AWS、GCP、Azure）→ 自动切为只读，Agent 不执行任何点击或填写。

**第二层：元素级保护** — 密码框永远不填。支付按钮永远不点。中英文双语识别：「付款」「购买」「pay」「checkout」全部拦截。

**第三层：操作确认** — 提交表单、发送消息、删除操作——Agent 做之前先问你。

共享浏览器 ≠ 无限制。AI 有手，但你定规矩。

---

## 不只是浏览器控制：五级通道，只在必要时才开浏览器

不是所有联网任务都需要打开浏览器。Skill 会自动选最轻量的方式完成：

```
WebSearch → WebFetch → Jina → curl → CDP 浏览器
  搜索摘要    页面提取    转Markdown   原始HTML    完整浏览器控制
```

简单搜索用 WebSearch，提取公开页面用 WebFetch，需要省 Token 用 Jina 转 Markdown。只有需要登录态、需要交互、或者轻量工具搞不定的时候，才启动浏览器。

### 搭档：Omni Search Skill（可选）

五级通道中的搜索和抓取能力还可以进一步增强。[omni-search-skill](https://github.com/d-wwei/omni-search-skill) 是一个独立的全栈搜索技能，支持 12 个搜索引擎、智能路由、自动抓取，可以作为 Browser Control Skill 的可选搭档子技能。

- **解耦设计** — 独立仓库，单独安装、单独 `git pull` 更新，Browser Control Skill 不包含它的任何代码
- **自动检测** — Agent 首次使用时自动检测本地是否已安装，未安装则建议一次，不阻塞
- **优雅降级** — 未安装时退回使用 WebSearch / WebFetch 等内置工具

```bash
git clone https://github.com/d-wwei/omni-search-skill.git
cd omni-search-skill && python3 -m pip install -r requirements.txt
```

| 场景 | 工具 |
|---|---|
| 多引擎深度搜索 | omni-search-skill `search` |
| 抓取公开 URL 转 Markdown | omni-search-skill `fetch` |
| 搜索 + 自动抓取 Top 结果 | omni-search-skill `resolve` |
| 爬取文档站点 | omni-search-skill `crawl` |
| 访问需登录的页面 | Browser Control（CDP / AppleScript） |
| 先搜索，再访问登录态结果 | omni-search `search` → Browser Control 导航 + 读取 |

---

## 并行调研：5 个目标同时查

后台模式下，Skill 可以派生多个子 Agent，每个开自己的 Tab，同时操作：

```
主 Agent: "调研这 5 家竞品"
  ├─ 子 Agent 1 → 竞品 A 官网（自己的 Tab）
  ├─ 子 Agent 2 → 竞品 B 官网（自己的 Tab）
  ├─ 子 Agent 3 → 竞品 C 官网（自己的 Tab）
  ├─ 子 Agent 4 → 竞品 D 官网（自己的 Tab）
  └─ 子 Agent 5 → 竞品 E 官网（自己的 Tab）
  → 各自调研，各自关闭 Tab，汇总给主 Agent
```

所有子 Agent 共享你的一个 Chrome 和一个代理进程，通过不同的 `targetId` 操作不同的 Tab。你的页面不受任何影响。

---

## 站点经验记忆

操作过的站点，Skill 会记住平台特征、有效策略、已知陷阱。预置 8 个高频站点经验：小红书、微信公众号、Twitter、LinkedIn、GitHub、Notion、Google、知乎。

---

## 和现有方案对比

|  | Browser Control Skill | Chrome DevTools MCP | Playwright | WebFetch |
|--|:----:|:----:|:----:|:----:|
| 完整浏览器操控（点击/填写/上传/键盘） | ✅ | ✅ | ✅ | ❌ 只能读 |
| 用你已登录的 Chrome | ✅ | ❌ | ❌ | ❌ |
| 人和 AI 能同时用 | ✅ 前台/后台分离 | ❌ 互相干扰 | ❌ 独立浏览器 | — |
| 后台并行操作 | ✅ 多 Tab 同时 | ❌ | 手动编排 | ❌ |
| 三层安全防护 | ✅ | 部分 | ❌ | — |
| 五级通道调度 | ✅ | ❌ | ❌ | 仅 fetch |
| 站点经验记忆 | ✅ | ❌ | ❌ | ❌ |
| 支持的 AI 平台 | 5 个 | 仅 Claude | 框架级 | 仅 Claude |
| macOS 零依赖 | ✅ | ❌ | ❌ | — |

---

## 支持 5 个 AI 平台

| 平台 | 适配文件 |
|------|---------|
| Claude Code | `skills/browse/SKILL.md`（`/browse` 命令直接可用） |
| OpenAI Codex | `adapters/codex/AGENTS.md` |
| Google Gemini CLI | `adapters/gemini/GEMINI.md` |
| Cursor | `adapters/cursor/.cursorrules` |
| Windsurf | `adapters/windsurf/.windsurfrules` |

macOS / Linux / Windows 三个操作系统均支持。macOS 额外支持零依赖的 AppleScript 前台模式。

---

## 3 分钟上手

### Claude Code

```bash
# 1. 克隆到 skills 目录
git clone https://github.com/d-wwei/browser-control-skill.git ~/.claude/skills/browser-control

# 2. 建立 /browse 命令的软链接
ln -sf ~/.claude/skills/browser-control/skills/browse ~/.claude/skills/browse

# 3. Chrome 设置（一次性）
#    打开 chrome://inspect/#remote-debugging
#    勾选 "Allow remote debugging for this browser instance"
#    macOS 还需要：Chrome → 查看 → 开发者 → 允许 Apple 事件中的 JavaScript
```

完成。试一下：

```
/browse here 读一下当前页面的标题
/browse bg 帮我打开 example.com 看看里面写了什么
```

### 其他平台

把 `adapters/` 目录下对应的适配文件复制到你的项目根目录即可。

---

## 架构

```
skills/
  browse/SKILL.md                     # /browse 命令入口（前台/后台模式路由）
  browser-control/
    SKILL.md                          # 核心能力定义（384 行 + 10 个按需加载模块）
    modules/                          # 按需加载（Agent 用到哪个读哪个）
    scripts/
      cdp-proxy.mjs                   # HTTP-to-CDP 桥接代理（后台模式核心）
      cdp-helper.py                   # CDP 写操作客户端（键盘/上传/悬停）
      browse-cmd.sh                   # 统一 CLI 入口
      check-deps.sh                   # 环境检测 + 代理自启动
      match-site.sh                   # 站点经验匹配
    references/
      site-patterns/                  # 8 个预置站点经验 + 运行时累积
adapters/                             # 5 个平台的适配文件
tests/                                # 200 个自动化测试
.github/workflows/test.yml           # GitHub Actions CI
```

---

## 依赖

| 组件 | 要求 | 用途 |
|------|------|------|
| Chrome | 任意现代版本 | 你日常使用的浏览器 |
| Node.js 22+ | 后台模式需要 | CDP Proxy |
| Python 3.6+ | 高级写操作需要 | CDP Helper |
| macOS | 前台模式需要 | AppleScript 零依赖 |

后台模式需要 Node.js。前台模式在 macOS 上零额外依赖——只要有 Chrome 就行。

---

## 自动更新

内置 [update-kit](https://github.com/d-wwei/update-kit) 自动更新检测。Skill 每次加载时静默检查（<5ms，从缓存读取），有新版本时提示一行：

```
Browser Control Skill update available: 3.1.0 — run: cd ~/.claude/skills/browser-control && npx update-kit apply
```

- 默认 `manual` 策略——只提示，不自动升级，由你决定
- 升级方式：`cd ~/.claude/skills/browser-control && npx update-kit apply`
- 回滚：`npx update-kit rollback`

---

## License

MIT

---

**人和 AI 共享一个 Chrome，前台协作后台并行。** GitHub 链接：[github.com/d-wwei/browser-control-skill](https://github.com/d-wwei/browser-control-skill)
