# Chrome Control — AI 编程助手的浏览器控制能力

[English README](./README.md)

让 AI 编程助手直接操控你的 Chrome 浏览器，访问任何你能访问的页面——包括需要登录认证的内网页面（SSO、MFA、安全网关）。

支持 **macOS** 和 **Windows**，自动检测平台并选择对应方案。

兼容 **Claude Code**、**Codex**、**Cursor**、**Gemini CLI**、**Windsurf** 及任何可执行 shell 命令的 AI agent。

## 这个 Skill 的独特之处

这个 skill 不是为了成为“功能最全”的浏览器自动化框架，而是为了解决一个更具体的问题：让 AI 编程助手以尽可能低的接入成本，直接借用用户真实的 Chrome 登录态去访问和操作受认证页面。

- **优先复用真实 Chrome 登录态**：核心思路不是新开一个自动化浏览器，而是直接继承用户已经登录的 Chrome session。
- **把内网/认证页面当成主要场景**：SSO、MFA、企业安全网关不是边缘情况，而是这个 skill 的设计中心。
- **跨平台策略更务实**：macOS 直接走原生 AppleScript，几乎零依赖；Windows 则走更实际的 CDP 路线。
- **以 skill / adapter 为中心，而不是以框架为中心**：目标是让 Claude Code、Codex、Cursor、Gemini CLI 等 agent 可以直接接入，而不是先搭一整套自动化基础设施。
- **前置条件透明**：agent 在真正执行前应先做 preflight check，环境没准备好就先停下并引导用户设置。

## 为什么需要这个 Skill？

AI 编程助手有多种访问网页的方式，但在面对企业级认证系统时，它们都无法通过登录：

| | Chrome Control（本 Skill） | agent-browser（Vercel） | WebFetch / Firecrawl |
|---|---|---|---|
| **浏览器** | 用户自己的 Chrome | Playwright 启动的 Chromium | 无浏览器，纯 HTTP 请求 |
| **登录态** | 完整继承——已登录即可用 | 全新 session，需重新登录 | 无 |
| **企业认证（SSO/MFA）** | 能通过——就是你自己的浏览器 | 通常被拦截（自动化指纹 + cookie 隔离） | 被拦截 |
| **安装依赖** | macOS 无需安装；Windows 需 Node.js | npm + Chromium（约 500MB） | 需要 API Key |
| **截图** | macOS: 不支持 / Windows: 支持 | 支持 | 不支持 |
| **无头模式** | 不支持（Chrome 必须打开） | 支持 | 天然无头 |
| **跨平台** | macOS + Windows | macOS / Windows / Linux | 全平台 |

### 什么场景用什么工具

- **需要访问内网 / 登录后的页面** → **Chrome Control**。这是唯一可靠的方案，其他工具都过不了企业登录。
- **自动化操作公开网页**（无需登录） → **agent-browser** 功能更全，支持截图、PDF、无头批量操作。
- **快速抓取公开网页内容** → **WebFetch** 最轻量，一行命令搞定。

## 工作原理

| 平台 | 实现方式 | 依赖 |
|---|---|---|
| **macOS** | AppleScript 直接与 Chrome 通信 | 无（macOS 原生支持） |
| **Windows** | Chrome DevTools Protocol (CDP) + agent-browser | Node.js + agent-browser |

两种方案都操作用户自己的 Chrome 实例，完整继承登录状态。Skill 会自动检测当前平台（`uname -s`），选择对应方案执行。

## 各 Agent 安装方式

### Claude Code

```bash
claude install-skill /path/to/browser-control-skill
```
或将 `skills/chrome-control/` 目录复制到项目的 skill 目录下。

### Codex (OpenAI)

将 `adapters/codex/AGENTS.md` 复制到项目根目录，或将内容追加到已有的 `AGENTS.md`。

### Cursor

将 `adapters/cursor/.cursorrules` 复制到项目根目录，或将内容追加到已有的 `.cursorrules`。

### Gemini CLI

将 `adapters/gemini/GEMINI.md` 复制到项目根目录。

### Windsurf

将 `adapters/windsurf/.windsurfrules` 复制到项目根目录，或将内容追加到已有的 `.windsurfrules`。

### 其他 Agent

将 `AGENT_INSTRUCTIONS.md` 复制到项目中，或将内容粘贴到 agent 的 system prompt / 自定义指令中。

## 环境配置

### macOS

只需在 Chrome 中开启一个设置（一次性）：

> Chrome 菜单栏 → **查看** → **开发者** → **允许 Apple 事件中的 JavaScript**

无需安装任何额外工具。

在 agent 执行任何浏览器操作之前，应先验证前置条件：

```bash
osascript -e 'tell application "Google Chrome" to get name'
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'
```

如果 JavaScript 检查失败，agent 应先停止操作，并引导用户：

- 打开 Chrome
- 开启 `查看 -> 开发者 -> 允许 Apple 事件中的 JavaScript`
- 如果 macOS 弹出自动化授权提示，选择允许
- 然后重新执行检查

### Windows

1. 安装 [Node.js](https://nodejs.org/)
2. 安装 agent-browser：
   ```powershell
   npm install -g agent-browser
   agent-browser install
   ```
3. SKILL.md 中提供了 `chrome-debug.ps1` 辅助脚本，可以一键完成 Chrome 重启和调试端口绑定

在 agent 执行任何浏览器操作之前，应先验证前置条件：

```powershell
where agent-browser
Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version"
```

如果任一检查失败，agent 应先停止操作，并引导用户：

- 安装 Node.js
- 运行 `npm install -g agent-browser`
- 运行 `agent-browser install`
- 完全关闭 Chrome
- 使用 `--remote-debugging-port=9222` 重新启动 Chrome
- 然后重新执行检查

## 使用方式

agent 在真正操作浏览器之前，应该始终：

1. 检测当前平台
2. 执行该平台对应的前置检查
3. 如果检查失败，先提示用户完成设置，不继续执行浏览器操作
4. 只有在前置条件确认满足后，才继续读取页面、点击、导航或执行 JavaScript

安装后，直接用自然语言让 Claude Code 操作浏览器：

- **读取已登录的页面内容**："帮我读一下当前 Chrome 标签页的内容"
- **导航和点击**："点击设置标签" 或 "打开 https://..."
- **提取数据**："提取这个页面上所有的链接"
- **填写表单**："在搜索框里输入..."

## 使用示例

```
你：读一下我当前 Chrome 页面的内容
Claude：[通过 AppleScript (macOS) 或 CDP (Windows) 提取页面文本]

你：点击「报表」标签
Claude：[找到文本为「报表」的元素并点击]

你：打开 https://internal.company.com/dashboard
Claude：[导航到目标 URL]
```

## 使用流程

1. 用户在 Chrome 中正常打开目标页面并登录
2. 告诉 Claude Code 你要做什么（读取内容、点击、提取数据等）
3. Claude 自动检测平台，使用对应方案操作你的 Chrome
4. 返回结果

**注意**：Windows 用户每次使用前需要用调试模式启动 Chrome（详见 SKILL.md）。

## 环境要求

### macOS
- Google Chrome
- 已开启「允许 Apple 事件中的 JavaScript」
- AppleScript 前置检查通过

### Windows
- Google Chrome
- Node.js
- agent-browser（`npm install -g agent-browser`）
- Chrome 以 `--remote-debugging-port=9222` 启动
- Windows 前置检查通过

## 已知限制

- 无法代替用户登录——用户必须先在 Chrome 中完成认证
- macOS：不支持截图；Chrome 必须处于打开状态
- Windows：每次使用前需要用调试模式重启 Chrome
- 超长页面内容需要分段读取

## 许可证

MIT
