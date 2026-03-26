# Chrome Control — AI 编程助手的浏览器控制能力

[English README](./README.md)

让 AI 编程助手直接操控你的 Chrome 浏览器，访问任何你能看到的页面——包括企业 SSO、MFA、安全网关后面的内网页面。**读取页面、填写表单、上传文件、点击按钮、撰写消息**——人在 Chrome 里能做的，agent 都能做。

无需扩展。无需 API Key。直接用你真实的 Chrome，通过系统原生机制控制。

兼容 **Claude Code**、**Codex**、**Cursor**、**Gemini CLI**、**Windsurf** 及任何可执行 shell 命令的 AI agent。

## 为什么做这个

AI 编程助手都能抓取公开网页，但你真正需要访问的页面——企业内网、需要登录的系统——它们都访问不了。

这个 skill 的思路很简单：直接操作**你自己的 Chrome**，继承你已有的登录态。你在 Chrome 里能看到的，agent 就能读取和操作。

## 和其他工具的区别

市面上有很多 AI 浏览器工具，定位各不相同：

| | Chrome Control | Chrome DevTools MCP | agent-browser / Playwright | WebFetch / Firecrawl | Browserbase |
|---|---|---|---|---|---|
| **本质** | 文档型 skill——agent 通过指令学会控制浏览器 | Chrome 官方 MCP 服务器，通过 CDP 协议通信 | 无头浏览器自动化库 | HTTP 内容提取服务 | 云托管浏览器会话 |
| **浏览器** | 用户自己的 Chrome | 用户的 Chrome（需调试模式启动） | 独立启动 Chromium | 无浏览器 | 远程 Chromium |
| **登录态** | 完整继承 | 继承（Chrome 需在运行） | 每次全新会话 | 无 | 全新会话 |
| **企业认证** | 能通过——就是你的浏览器 | 能通过（同一个 Chrome） | 通常被拦截 | 被拦截 | 被拦截 |
| **安装成本** | macOS: 勾一个选项；Windows: npm install | npm install + 重启 Chrome 加调试参数 | npm + Chromium (~500MB) | API Key | API Key + 注册账号 |
| **Agent 支持** | Claude Code, Codex, Cursor, Gemini CLI, Windsurf | Claude Code（仅 MCP） | 取决于框架 | 大部分 agent | 取决于框架 |
| **架构** | 零依赖的纯文档 | MCP 服务器进程 | 库 / MCP 服务器 | API 服务 | 云 API |

### 什么场景用什么

- **内网 / 登录后的页面** → **Chrome Control**。唯一能直接继承登录态、几乎零配置的方案。
- **深度浏览器调试**（网络、性能、DOM 检查） → **Chrome DevTools MCP**。功能更强，但需要 Chrome 以调试模式重启，且只支持 MCP 协议。
- **公开网站的自动化测试** → **agent-browser / Playwright**。无头批量操作、截图、PDF 生成更合适。
- **快速抓取公开内容** → **WebFetch / Firecrawl**。最轻量，一个 HTTP 请求搞定。
- **大规模并行浏览器会话** → **Browserbase**。云端隔离，但没有登录态继承。

## 设计原则

这个 skill 有意保持极简：

1. **轻量渐进式架构** —— 基础操作使用纯 `osascript`（macOS）或 `agent-browser`（Windows），零基础设施。高级写入操作按需升级到 CDP 增强模式，通过一个纯 Python 3 标准库脚本实现（无需 pip install）。

2. **真实会话优先** —— 核心设计围绕继承用户已有的 Chrome 登录态，而不是创建新的自动化会话。

3. **结构化推理** —— Agent 在每次操作前遵循 EVALUATE → OBSERVE → PLAN → ACT 循环，减少盲目点击和无效调用。

4. **安全边界** —— 内置银行、支付、认证网站黑名单。密码字段和支付按钮永远不会被触碰。操作前强制 URL 验证。

5. **标签页保护** —— Agent 始终打开新标签页，用户已有的标签页永远不会被跳转。

6. **多 Agent 适配** —— 一个 skill，适配 5+ 种 agent 格式。无论用 Claude Code、Codex、Cursor、Gemini CLI 还是 Windsurf，行为一致。

## 架构

```
┌───────────────────────────────────────────────────────────┐
│                     Chrome Control Skill                  │
├────────────────────────────┬──────────────────────────────┤
│     基础模式 (默认)         │    CDP 增强模式 (按需启用)    │
├────────────────────────────┼──────────────────────────────┤
│ macOS: AppleScript (零      │ 可信点击 (isTrusted)         │
│   依赖, 读取 + 基础        │ 键盘输入 (Enter/Tab)         │
│   点击/填写)               │ 文件上传 (无需 OS 对话框)     │
│                            │ 富文本编辑器 (Notion/Slack/   │
│ Windows: agent-browser     │   Gmail 撰写)               │
│   (CDP, 读取 + 基础        │ 悬浮触发菜单                 │
│   交互)                    │ 下拉选择自动化               │
│                            │ iframe 穿透                  │
├────────────────────────────┼──────────────────────────────┤
│ 依赖: 无 (macOS) /         │ 依赖: Python 3.6+ (macOS    │
│   Node.js (Windows)        │   自带) + Chrome             │
│                            │   --remote-debugging-port    │
└────────────────────────────┴──────────────────────────────┘
```

两种模式都操作用户自己的 Chrome 实例，完整继承登录状态。Skill 自动检测平台（`uname -s`），选择对应方案。CDP 增强模式仅在基础模式不够用时才会激活。

## 环境配置

### macOS

只需在 Chrome 中开启一个设置（一次性）：

> Chrome 菜单栏 → **查看** → **开发者** → **允许 Apple 事件中的 JavaScript**

无需安装任何工具。

### Windows

1. 安装 [Node.js](https://nodejs.org/)
2. 安装 agent-browser：
   ```powershell
   npm install -g agent-browser
   agent-browser install
   ```
3. 以调试模式启动 Chrome：`chrome.exe --remote-debugging-port=9222`

## 各 Agent 安装方式

### Claude Code

```bash
claude install-skill /path/to/browser-control-skill
```

### Codex (OpenAI)

将 `adapters/codex/AGENTS.md` 复制到项目根目录。

### Cursor

将 `adapters/cursor/.cursorrules` 复制到项目根目录，或追加到已有的 `.cursorrules`。

### Gemini CLI

将 `adapters/gemini/GEMINI.md` 复制到项目根目录。

### Windsurf

将 `adapters/windsurf/.windsurfrules` 复制到项目根目录，或追加到已有的 `.windsurfrules`。

### 其他 Agent

将 `AGENT_INSTRUCTIONS.md` 复制到项目中，或将内容粘贴到 agent 的 system prompt。

## 使用方式

安装后，用自然语言让 agent 操作浏览器。建议使用"我的 Chrome"等措辞来明确触发浏览器控制：

- **读取已登录的页面**："帮我读一下我 Chrome 里当前标签页的内容"
- **导航**："在我的 Chrome 里打开 https://internal.company.com/dashboard"
- **点击**："点击设置标签"
- **提取数据**："提取这个页面上所有的链接"
- **填写表单**："在搜索框里输入 quarterly report"
- **上传文件**："把这个截图上传到 Jira 工单里"
- **富文本编辑**："帮我在 Gmail 里写一封回复"
- **键盘操作**："按 Enter 提交表单"
- **复杂工作流**："在 Notion 里创建一个新页面并填入这些内容"

Agent 会自动：
1. 检测当前平台
2. 执行前置检查
3. 如有问题，引导你完成配置
4. 打开新标签页进行导航（不会影响你现有的标签页）
5. 每个操作都遵循 EVALUATE → OBSERVE → PLAN → ACT 循环

### 快速开始

1. 在 Chrome 中打开目标页面并登录
2. 告诉 Agent 你要做什么
3. Agent 操作 Chrome 并返回结果

## 发展路线

```
Phase 1              Phase 1.5（当前）           Phase 2                  Phase 3+
基础读取/点击       → CDP 增强模式             → WebMCP 集成            → 站点经验缓存
AppleScript +          可信事件、文件上传、        （Chrome Stable 支持      与记忆机制
agent-browser          键盘输入、富文本、          后，预计 2026 下半年+）
                       悬浮菜单
```

设计上确保每个阶段是叠加而非替换。基础模式始终保持为快速默认选项；CDP 增强模式仅在需要时激活。

## 安全机制

以下规则是强制执行的——agent 会拒绝违反这些规则的操作：

- **敏感网站黑名单**：银行、支付、认证、云控制台网站只能读取（不能点击、填写或执行 JS）
- **密码字段**：永远不会填写或点击
- **支付按钮**：永远不会点击（pay、purchase、checkout、subscribe 等）
- **操作前 URL 检查**：在与任何页面交互前，agent 会先验证 URL 是否在黑名单中

## 环境要求

### macOS
- Google Chrome
- 已开启「允许 Apple 事件中的 JavaScript」

### Windows
- Google Chrome + Node.js
- agent-browser（`npm install -g agent-browser`）
- Chrome 以 `--remote-debugging-port=9222` 启动

## 已知限制

- 无法代替用户登录——你必须先在 Chrome 中完成认证
- macOS：Chrome 必须处于打开状态（AppleScript 无法控制隐藏的浏览器）
- Windows：每次使用前需要用调试模式重启 Chrome
- 超长页面内容需要分段读取
- 每次一个操作——复杂工作流可能需要多轮交互

## 许可证

MIT
