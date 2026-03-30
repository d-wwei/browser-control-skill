# 5 个平台，200 个测试，1 条命令：让 AI Agent 接管你的 Chrome

给 AI 编程助手装上「真·浏览器」能力——用你已登录的 Chrome，操作公司内网、企业后台、需要认证的任何页面。

---

## 痛点：你的 AI 助手看不到你看到的网页

你在 Chrome 里打开了公司内部系统。数据就在屏幕上。你让 AI 帮你提取——

> "抱歉，我无法访问需要登录的页面。"

WebFetch 拿不到认证页面。Playwright 要重新登录。Chrome DevTools MCP 需要额外启动一个浏览器实例。

**你明明已经登录了，为什么 AI 还是看不到？**

因为它们都不用你的浏览器。

---

## 解法：直接用你的 Chrome

Browser Control Skill 让 AI Agent 直接连上你**正在用的** Chrome 浏览器。零重复登录。你的 Cookie、Session、SSO 登录态——Agent 全部继承。

```
/browse here 帮我从这个页面提取数据
/browse bg 同时调研这 5 家公司的官网
```

两种模式，一个命令：

| 模式 | 命令 | 效果 |
|------|------|------|
| **前台操作** | `/browse here` | Agent 操作你眼前的页面，你能看到每一步 |
| **后台运行** | `/browse bg` | Agent 在后台开自己的 tab，你继续工作，互不干扰 |
| **自动判断** | `/browse` | 根据你的指令自动选择前台或后台 |

---

## 和现有方案对比

|  | Browser Control Skill | Chrome DevTools MCP | Playwright | WebFetch |
|--|:----:|:----:|:----:|:----:|
| 用你已登录的 Chrome | ✅ | ❌ | ❌ | ❌ |
| 需要几步设置 | 1 步 | 3-5 步 | pip install + 代码 | 0 步（但不能登录） |
| macOS 零依赖模式 | ✅ | ❌ | ❌ | — |
| 多 Agent 并行操作 | ✅ 最多 20+ tab | ❌ | 手动 | ❌ |
| 三层安全防护 | ✅ | 部分 | ❌ | — |
| 站点经验记忆 | ✅ | ❌ | ❌ | ❌ |
| 支持几个 AI 平台 | 5 个 | 仅 Claude | 框架级 | 仅 Claude |

---

## 核心能力

### 🔍 五级通道调度

不是所有任务都需要打开浏览器。Skill 自动选最轻的工具完成任务：

```
WebSearch → WebFetch → Jina → curl → CDP 浏览器
  搜索摘要    页面提取    转Markdown   原始HTML    完整浏览器控制
```

只有轻量工具搞不定的时候，才启动浏览器。省时间，省 Token。

### 🖥️ 前台 / 后台双模式

**前台模式**（AppleScript）——Agent 操作你正在看的页面。
适合：「帮我在这个页面上填个表」「帮我点一下那个按钮」

**后台模式**（CDP Proxy）——Agent 在后台静默操作，你完全无感。
适合：「帮我同时查 5 家公司官网」「后台提取这 10 个页面的数据」

核心区别：前台走 UI 层（AppleScript），目标是你眼前的窗口；后台走协议层（Chrome DevTools Protocol），通过 targetId 精确寻址每个 tab，不碰你的任何页面。

### 🤖 子 Agent 并行分治

一个任务要查 N 个独立目标？Skill 支持派生多个子 Agent，每个子 Agent 创建自己的 tab，同时操作，互不干扰。

主 Agent 只收汇总结果，不被原始内容撑爆上下文。

```
主 Agent: "调研这 5 家竞品"
  ├─ 子 Agent 1 → 竞品 A 官网（自己的 tab）
  ├─ 子 Agent 2 → 竞品 B 官网（自己的 tab）
  ├─ 子 Agent 3 → 竞品 C 官网（自己的 tab）
  ├─ 子 Agent 4 → 竞品 D 官网（自己的 tab）
  └─ 子 Agent 5 → 竞品 E 官网（自己的 tab）
  → 各自调研，各自关闭 tab，汇总给主 Agent
```

### 🛡️ 三层安全防护

Agent 操作你的真实浏览器，安全不能妥协：

**第一层：域名黑名单** — 银行、支付、认证、云控制台页面自动切为只读，不执行任何点击或填写。

**第二层：元素级保护** — 密码框永远不填，支付按钮永远不点。中英文双语识别（「付款」「购买」「pay」「checkout」）。

**第三层：操作确认** — 提交表单、发送消息、删除操作之前，Agent 会先问你。

### 📝 结构化内容提取

不是粗暴地 `innerText` 取一堆纯文本。内置 DOM-to-Markdown 转换器，完整保留：

- 标题层级（h1-h6）
- 表格（pipe 格式）
- 代码块（带语言标记）
- 有序 / 无序列表（支持嵌套）
- 链接、图片、加粗、斜体

对于虚拟滚动页面（X/Twitter、React Virtualized），内置滚动爬取器，边滚边收集 DOM 数据。

### 🧠 站点经验记忆

操作过的站点，Skill 会记住平台特征、有效策略、已知陷阱。下次操作同一站点时自动加载经验，避免重复踩坑。

预置 8 个高频站点的冷启动经验包：小红书、微信公众号、Twitter、LinkedIn、GitHub、Notion、Google、知乎。

### ✍️ 完整写操作支持

不只是读页面——可以写：

| 操作 | 怎么实现 |
|------|---------|
| 填表单（React/Vue 兼容） | 事件派发 + React state setter |
| 富文本编辑器（Notion、Slack、Gmail） | CDP `Input.insertText` |
| 键盘快捷键 | CDP `Input.dispatchKeyEvent` |
| 文件上传 | CDP `DOM.setFileInputFiles` |
| 下拉框选择 | 标准 `<select>` + 自定义 dropdown |
| 悬停触发菜单 | CDP `Input.dispatchMouseEvent` |

---

## 支持平台

### AI Agent 平台

| 平台 | 适配文件 | 状态 |
|------|---------|:----:|
| Claude Code | `skills/browse/SKILL.md` | ✅ `/browse` 命令可用 |
| OpenAI Codex | `adapters/codex/AGENTS.md` | ✅ |
| Google Gemini CLI | `adapters/gemini/GEMINI.md` | ✅ |
| Cursor | `adapters/cursor/.cursorrules` | ✅ |
| Windsurf | `adapters/windsurf/.windsurfrules` | ✅ |

### 操作系统

| 平台 | 基础模式 | CDP 模式 |
|------|:--------:|:--------:|
| macOS | AppleScript（零依赖） | CDP Proxy + Helper |
| Linux | — | CDP Proxy + Helper |
| Windows | — | CDP Proxy + Helper |

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

完成。现在可以用 `/browse` 了。

### Codex / Gemini / Cursor / Windsurf

把对应 `adapters/` 目录下的适配文件复制到你的项目根目录即可。

---

## 架构

```
skills/
  browse/SKILL.md                     # /browse 命令入口（模式路由）
  browser-control/
    SKILL.md                          # 核心能力定义（384 行 + 10 个按需加载模块）
    modules/                          # 按需加载模块
      applescript-commands.md         #   AppleScript 完整命令参考
      cdp-proxy-api.md               #   CDP Proxy API 参考
      cdp-write-ops.md               #   CDP 写操作（键盘/上传/下拉/悬停）
      dom-extraction.md              #   DOM-to-Markdown + 虚拟滚动
      interactive-elements.md         #   元素索引 + 标注截图
      console-network.md             #   Console/Network 拦截
      parallel-dispatch.md           #   子 Agent 并行分治
      safety-system.md               #   三层安全系统完整实现
      site-experience.md             #   站点经验记忆
      advanced-applescript.md         #   JXA + 智能等待
    scripts/
      cdp-proxy.mjs                   # HTTP-to-CDP 桥接代理（Node.js）
      cdp-helper.py                   # Python CDP 客户端（零依赖）
      browse-cmd.sh                   # 统一 CLI 入口
      check-deps.sh                   # 环境检测 + 代理自启动
      match-site.sh                   # 站点经验匹配
    references/
      cdp-api.md                      # CDP API 文档
      site-patterns/                  # 站点经验文件（8 个预置 + 运行时累积）
adapters/                             # 多平台适配器（5 个）
tests/                                # 200 个自动化测试
.github/workflows/test.yml           # CI 自动测试
```

---

## 测试覆盖

200 个自动化测试，192 个不需要 Chrome 即可运行：

| 测试套件 | 用例数 | 覆盖 |
|---------|:------:|------|
| test_cdp_helper.py (pytest) | 109 | WebSocket 帧、CDP 消息、CLI 解析、键映射、坐标 |
| test_safety.mjs (node) | 33 | 域名黑名单、元素保护、边界情况 |
| test_dom_to_markdown.mjs (node) | 28 | HTML 转 Markdown 所有元素类型 |
| test_scripts.sh (bash) | 22 | Shell 脚本逻辑 |
| test_integration.sh (bash) | 8 | 端到端浏览器操作（需要 Chrome） |

GitHub Actions CI 自动运行全部测试。

---

## 依赖

| 组件 | 最低要求 | 用途 |
|------|---------|------|
| Chrome | 任意现代版本 | 被操控的浏览器 |
| Node.js 22+ | 可选 | CDP Proxy（后台模式） |
| Python 3.6+ | 可选 | CDP Helper（高级写操作） |
| macOS | 可选 | AppleScript 零依赖模式 |

macOS 基础模式**零额外依赖**——只需要 Chrome 本身。

---

## License

MIT

---

**一个 Skill，五个平台，真实登录态。** GitHub 链接：[github.com/d-wwei/browser-control-skill](https://github.com/d-wwei/browser-control-skill)
