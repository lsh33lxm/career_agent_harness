# 观复 Career Harness — 桌面端统一重构设计文档

分支：`ui/cohesive-desktop-redesign`（基于 `refactor/v1.4-integration` HEAD 5d544e6）
范围：`apps/desktop` 前端。不改动后端 API、数据模型、鉴权、证据链与确认流程。
基线截图：`C:\Users\lxm33\Desktop\agent找工作讨论\截屏\1.png–10.png`（10 张核心页面，只读分析，未移动或修改）与 `docs/screenshots/before/`；改造后截图：`docs/screenshots/after/`（离线态）与 `docs/screenshots/after-online/`（在线空态）。

## 1. 现状问题（基于 10 页基线截图与源码审计）

1. **卡片拼贴**：每个区域都是独立白卡（`#fff` + 灰边框），浮在米色背景上，页面没有主次与连续性；今天页、机会页、项目页尤为明显。
2. **双套视觉语言并存**：品牌 token（`--paper/--green/--gold`、宋体标题）与一套临时灰色后台样式（`#dce1dd` 边框、`#315d46` 按钮、Georgia 数字）混用；按钮有 `primary-command`、`today-primary/secondary/quiet`、`capture-button`、`button button-primary` 及浏览器默认按钮共五套以上。
3. **原生控件未清除**：默认复选框、默认灰色按钮（项目页"刷新"、沟通草稿"保存草稿"）、未设定宽高的 textarea 直接出现。
4. **错误呈现混乱**：`Local API is unavailable`、`本地服务尚未启动…`、`队列暂不可用` 等以红字、灰字、居中孤行、Banner 等多种形式随机出现；部分页面直接把英文技术信息作为主文案。
5. **空状态失控**：设置页用一张 1040px 白卡只放一句话；机会页"沟通草稿""求职流程"像空白段落散落在页面底部。
6. **层级缺失**：顶部搜索（禁用但伪装成可用输入框）、快速收集、侧栏、页面标题、页面操作之间没有明确秩序；侧栏 10 个菜单同权堆叠。
7. **任务流不清**：今天页的焦点/队列/确认/预览都是同权白卡；机会页的"导入→搜索→浏览→草稿→求职流程"没有表达出步骤关系。
8. **衔接生硬**：长页面分区之间仅靠卡片间隙分隔；表单标签、输入框、按钮对齐不稳定（机会页筛选行、知识页资料源行）。

## 2. 设计原则

- **一个页面，一张主工作表面**：页面内容组织在统一的暖白表面内，分区用发丝线（hairline）与留白分隔，不再卡片套卡片。
- **克制的层级**：页面标题 28px 半粗体（同一套字），分区标题 15px，正文 14px，辅助 12–13px；只有侧栏品牌字"观复"与座右铭保留楷体气质。
- **状态统一**：loading / empty / offline / error / success / disabled 全站一套组件与文案结构："发生了什么 → 影响什么 → 可以做什么"；技术细节默认收进"查看技术详情"。
- **本地优先的诚实**：不用假数据掩盖离线；离线时界面平静、可恢复（重试 / 诊断），不展示英文原始错误。
- **桌面应用的秩序**：导航按任务分组；工具栏固定承载上下文、命令入口与全局主操作；控件位置可预测。
- **动效克制**：仅导航、hover、弹层、页面进入使用 160–220ms 过渡，支持 `prefers-reduced-motion`。

参考（不照搬）：Apple HIG（Sidebar/Toolbar/分层材质、可预测控件位）、Linear（高密度下的克制层级）、Raycast（命令入口与紧凑反馈）。

## 3. 设计 Token（`src/styles/tokens.css`）

| 类别 | 关键值 |
| --- | --- |
| 背景 | `--paper:#f3eee2`（暖象牙白） |
| 表面 | `--surface:#fbf8f0` 主工作面；`--surface-raised:#fffdf8`；`--surface-sunken:#f0eadd` 内凹区 |
| 墨色 | `--ink:#17332e`；`--muted:#68736c` |
| 品牌 | `--green:#0a514d`、`--green-deep:#093f3d`、`--green-soft:#e3ece6` |
| 强调 | `--gold:#c9982f`（低饱和）、`--gold-text:#77571c`、`--gold-soft:#f5e7c4` |
| 错误 | `--danger:#9a4a3e`（柔和砖红）、`--danger-soft:#f7e7e2` |
| 边框 | `--border:#ded7c6`、`--border-strong:#c8bfa9` |
| 字体 | 正文系统中文字体栈；展示字（仅品牌）楷体/宋体；数字 `tabular-nums` |
| 字号 | h1 28/600；分区 15/600；正文 14；辅助 12.5 |
| 间距 | 4/8pt：`--space-1..12`（4–48px） |
| 控件 | 高度 32px（页面主操作 36px）；圆角 6/8/12；图标线宽统一 lucide 默认 2px，尺寸 15/16/18 |
| 阴影 | `--shadow-1:0 1px 2px rgb(23 51 46/5%)`；`--shadow-2:0 6px 20px rgb(23 51 46/8%)`（仅弹层/抽屉） |
| 动效 | `--dur-fast:160ms`、`--dur:200ms`，ease-out；reduced-motion 归零 |

## 4. 核心组件（`src/components/ui/`）

- `AppShell`：侧栏 + 工具栏 + 内容区；桌面端侧栏可收起为图标轨（≥1024px），窄屏为抽屉（遮罩 + Esc 关闭）。
- `Sidebar`：品牌区、分组导航（工作流 / 职业档案 / 系统与资料）、底部服务状态入口。
- `TopToolbar`：当前页上下文、禁用的命令入口（`⌘K` + "即将推出"，不再伪装输入框）、离线状态点、快速收集（主操作，禁用态有说明）。
- `PageHeader`：眉题 → 标题 + 一句说明 → 页面级操作。
- `Section`：主工作表面内的分区（标题行 + 计数/说明 + 内容），发丝线分隔。
- `Button`：`primary / secondary / quiet / destructive`，统一 32px 高、loading、disabled。
- `Field`：label + 控件 + helper/error 关联（`aria-describedby`）。
- `StatusBanner` / `InlineNotice`：页面级与行内提示（info / warning / danger / success）。
- `EmptyState` / `ErrorState` / `Skeleton` / `Spinner`：统一空、错、加载；ErrorState 支持重试与折叠技术详情。
- `ServiceStatusPill`：侧栏与工具栏共用的服务状态。
- `errorCopy.ts`：把 `ApiError`（含 `Local API is unavailable`、launch token 缺失、401/403、演示模式）映射为中文标题 + 建议 + 原始详情。

## 5. 页面改造要点

- **今天**：统一 PageHeader（日期/问候/服务状态并入眉题行）；主表面内按 今日焦点 → 今日队列 → 本周回看 分区，侧栏列 待确认 / 飞书离线预览 / 快速收集；日出与手写体装饰移除，气质交给留白与排版；离线时焦点/队列/确认显示同一 ErrorState（重试）。
- **机会**：一个主表面表达任务流——① 导入历史数据（紧凑单行表单）→ ② 搜索筛选（对齐的控制组）→ ③ 岗位列表+详情（列表/详情双栏，发丝线行）；沟通草稿与求职流程成为后续分区，空态引导回第一步；草稿操作区别人工确认（主按钮）与只读信息。
- **项目**：受控分析工作区收进可发现的折叠分区（默认收起，不压过项目档案）；项目浏览器为列表/详情一张表面；空态给出"先去分析或登记"的下一步。
- **能力**：选择档案/刷新/状态合并为紧凑控制组；无档案空态给下一步；有数据时 节点列表 / 详情 / 信号 分层呈现。
- **简历**：选择简历 + 刷新为控制组；高级修订工具收进折叠面板；空态说明为何为空并指向"我的/职业事实确认"。
- **历史**：统一时间线表面；离线为统一 ErrorState（同一按钮规格）；证据入口为低干扰 secondary 按钮。
- **我的**：统计带 + 分段（已确认/待确认/手动记录）；待确认为主任务；手动记录为底部 composer（对齐的 select/textarea/提交 + 明确反馈）。
- **知识**：资料源管理与精确检索合为连续工作台表面；表单统一 Field；本地路径权限有 helper 说明；检索区有焦点态、空态与范围说明。
- **设置**：分类组织（概览/偏好），"尚未接入"为状态徽标 + 说明 + 诊断入口，不再是巨大白卡。
- **工具与模型**：本地工具状态（紧凑 Banner）→ 模型服务配置（渐进披露）→ 高级设置；表单统一高度/标签/保存反馈；密钥不渲染明文。

## 6. 状态文案规范

- 用户主文案一律中文："暂时无法连接本地服务"；影响范围与恢复操作紧随其后。
- 英文/技术原文只出现在 `<details>查看技术详情</details>` 内。
- 同一离线原因全站只以一种 `ErrorState`/`StatusBanner` 呈现。
- 成功反馈用 `InlineNotice success`（如"草稿已保存，等待你审核"）。

## 7. 第二轮：视觉稿对齐与模型配置工作台（round 2）

以 `docs/visual-reference/观复-前端重构视觉稿-10页/deliverables/guanfu-ui-visuals/` 的 10 张高保真稿为验收标准迭代，截图对比见 `docs/screenshots/round2/`（`*-offline` / `*-online` / `r1280-*`）。

### 新增共享组件与 token

- `SunriseArt`：页头右侧轻量日出点缀（融入状态区，仅主页面启用）。
- `CompanyAvatar`：公司首字 + 稳定暖色；仅在真实数据有 `logoUrl` 时才用图，不为不存在的职位伪造商标。
- `ProviderMark`：厂商品牌字母标（本地渲染，无运行时外链图片）。
- `Drawer`：右侧配置抽屉（Esc/遮罩关闭、role=dialog、打开时聚焦关闭按钮）。
- `Section` 支持 `icon`（软底方块线性图标）；页标题升至 32px；顶栏新增通知（禁用态）与本地用户头像位；侧栏底部补品牌短句。

### 模型预设注册表（`src/api/providerPresets.ts`）

数据驱动预设：`id / name / kind / baseUrl / recommendedModel / models / supportsTest / isLocal / helpUrl / note`。
支持：OpenAI、Anthropic、Google Gemini、Kimi/Moonshot、DeepSeek、通义千问（百炼）、智谱 GLM、MiniMax、OpenRouter、Ollama、LM Studio、自定义 OpenAI 兼容、自定义 Anthropic 兼容。
映射到后端真实协议：`openai / anthropic / deepseek / openai_compatible`；端点与推荐模型依据厂商官方文档与后端 `PROVIDER_DEFAULTS`（Gemini OpenAI 兼容端点见 ai.google.dev/gemini-api/docs/openai；百炼兼容模式见阿里云文档；智谱 paas/v4 见 docs.bigmodel.cn；Kimi 见 platform.moonshot.cn）。模型 ID 均为可编辑预填，不写死不可改。
密钥安全：API Key 仅通过 `configure` 接口写入 Windows 凭据管理器；前端只存输入中的临时 state，保存即清空；不进入 localStorage/日志/错误文本。连接测试必须用户勾选确认后手动发起（`confirm_external_request`）。
后端无删除/设默认/模型发现接口，故卡片暂不提供这两个动作（见报告“已知限制”）。

### 页面层调整

- 工具与模型：本地服务状态卡（真实健康/工具数/版本/诊断/重试）+ 页签（模型服务/本地工具/任务队列）+ 已配置/可添加厂商/本地模型/高级自定义 分区 + 抽屉式配置。
- 今天：页头日出点缀、焦点全宽 CTA、队列/待确认与回看/飞书/收集双列、分区图标。
- 机会：岗位行加公司头像与 chevron；详情头部元信息网格 + 主操作“加入求职流程”。
- 项目：GitHub 只读分析工作区恢复为页首可见（紧凑化：地址+按钮一行、确认与令牌收起、三条只读承诺）；项目列表加图标。
- 能力：档案选择/刷新上移页头；就绪时显示真实指标带（节点数/市场信号/图谱版本）。
- 简历：左栏“已确认的职业事实”（类型图标行）+ 右栏预览/修订 + 小提示；高级工具保持折叠。
- 历史：真实指标带（申请/面试/Offer/未通过，来自申请状态）、离线警告 Banner + 重试、时间线列表 + 当前阶段分区。
- 我的：隐私提示 Banner、已确认/待确认统计卡与页签、搜索+类型筛选、底部 composer 带字数。
- 设置：页内导航 + 连接/偏好/隐私分区（未接入项为状态徽标）+ 右侧本地服务真实状态卡。
- 知识：资料源类型汇总条、检索结果分类图标、分区顺序调整（资料源→检索→历史知识→Wiki 治理）。
- 全站：技术详情折叠统一命名为“查看诊断”。

### 诚实性边界（不做假）

视觉稿中的示例数据（任务、公司 Logo、雷达图、指标数字）仅作设计参考；无真实后端字段处不伪造：能力页无雷达图（无维度数据），历史行无公司名（申请只有 ID），知识检索无来源类型筛选（结果无该字段），偏好设置显示“尚未接入”而非假开关。
