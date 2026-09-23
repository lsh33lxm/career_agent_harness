# 第三轮视觉审计与逐页验收

目标图：`docs/visual-reference/观复-前端重构视觉稿-10页/deliverables/guanfu-ui-visuals/01–10.png`
验收截图（1536×1024）：`docs/screenshots/round3/`（`*-demo.png` 为 `?demo=visual-review` fixture 模式，`*-empty.png` 为真实离线/空数据模式，`r1280-*` 为 1280px 抽查）。

## 集成分支可视 Smoke（2026-09-23）

使用本地 Chromium 1234、Vite 随机空闲端口和 `scripts/mock_core_for_screenshots.py`，在合并验证 worktree 执行了 30 次真实页面加载与截图：
`artifacts/verification/ui-smoke-20260923-221418/`，覆盖 1536、1440、1280 × 今天、机会、项目与证据、能力地图、简历、职业历程、我的、设置、工具与模型、知识。
每次检查均读取页面标题，且 `document.body.scrollWidth <= document.documentElement.clientWidth`；未发现横向异常滚动。截图和 mock 日志均在 Git 忽略目录，未进入提交。

## 视觉验收模式

- 启用：开发服务器下访问 `http://127.0.0.1:<port>/?demo=visual-review`（或 `VITE_VISUAL_REVIEW=true` / `__ACH_CONFIG__.visualReview=true`）。
- 实现：`src/api/visualReview.ts` 在 `apiRequest` 入口拦截，`import.meta.env.DEV` 为 false 时分支被静态移除；fixture 数据在 `src/api/visualReviewFixtures.ts`。写操作短路为安全回执，不持久化。
- 生产页面只渲染真实 API 数据；fixture 仅用于布局/密度/图标/状态验收。

## 逐页对照

| 页面 | 当前问题（改造前） | 对应视觉稿元素 | 本次改动 | 验证截图 |
| --- | --- | --- | --- | --- |
| 今天 | 大空白卡、焦点弱、模块松散 | 页头日期+日出、焦点主 surface+CTA、队列 checklist、右侧回看 | 页头 36px+SunriseArt；焦点全宽+主按钮；队列三列行（图标/来源/时限/优先级）；回看/飞书/收集右列 | `1536-today.png` / `1440-today.png` / `1280-today.png` |
| 机会 | 筛选与草稿分散、无 master-detail 感 | 紧凑导入+筛选、左列表右详情、公司头像、来源证据、主操作 | 任务流条；岗位行=公司头像+状态徽标+标签+地点薪资；详情头元信息网格+"加入求职流程" | `1536-opportunities.png` / `1440-opportunities.png` / `1280-opportunities.png` |
| 项目与证据 | 分析表单占地大、档案像空白列表 | 页首紧凑分析入口+三条只读承诺、可扫描项目列表、证据标签 | 分析工作区紧凑单行+令牌收起；项目列表图标头像；证据卡权威/复核/时效标签修复（补 code_verified 映射） | `1536-projects.png` / `1440-projects.png` / `1280-projects.png` |
| 能力地图 | 空白大卡、控制区松散 | 页头选择+刷新、能力数字、节点/详情分区 | 控制组上移页头；真实指标带（节点数/市场信号/图谱版本）；修复 relation 标签映射（part_of/related_to） | `1536-capabilities.png` / `1440-capabilities.png` / `1280-capabilities.png` |
| 简历 | 表单与内容混排、预览弱 | 左栏事实来源、右栏预览、小提示、高级工具二级入口 | 双栏工作区：事实行（类型图标+说明+内容）｜预览/修订+差异/来源折叠+提示条；选择/刷新上移页头 | `1536-resume.png` / `1440-resume.png` / `1280-resume.png` |
| 职业历程 | 孤立错误卡、无时间线 | 指标概览、离线提示条、时间线列表、证据操作 | 真实指标带（申请/面试/Offer/未通过，由申请状态计算）；离线=警示 Banner+重试；时间线行（状态点+徽标+投递时间+证据链接） | `1536-history.png` / `1440-history.png` / `1280-history.png` |
| 我的 | 两卡+散落表单 | 隐私提示、统计卡、页签+筛选、底部 composer | StatusBanner 隐私提示；已确认/待确认统计卡切换页签；搜索+类型筛选；composer 含字数 | `1536-context.png` / `1440-context.png` / `1280-context.png` |
| 设置 | 巨大空白卡"尚未接入" | 页内导航、连接/偏好/隐私分区、右侧本地服务卡 | 新 SettingsPage：锚点导航+分区行（未接入=徽标）+本地服务真实健康卡（状态/版本/诊断/重试） | `1536-settings.png` / `1440-settings.png` / `1280-settings.png` |
| 工具与模型 | 孤立错误行+卡片堆叠 | 本地服务状态卡、Tabs、厂商卡片、配置入口 | 状态卡（真实健康/工具数/版本/诊断/重试）；页签 模型服务/本地工具/任务队列；模型区内子页签 已配置/添加厂商/本地模型/高级配置 + 抽屉配置 | `1536-plugins.png` / `1440-plugins.png` / `1280-plugins.png` |
| 知识 | 三个大空卡 | 资料源汇总、类型计数、检索+结果列表 | 资料源类型汇总条（本地文件/GitHub/Legacy+连接状态）；检索结果分类图标；分区顺序 资料源→检索→历史→治理 | `1536-knowledge.png` / `1440-knowledge.png` / `1280-knowledge.png` |

## 全局规格收敛（本轮）

- 页标题 36px、正文 15px、辅助 13px、眉题 12px；控件高 40/44px；圆角 10/14px；顶栏 60px；侧栏导航行高 38px。
- 图标统一 lucide 线性、分区图标 32px 软底方块；`CompanyAvatar`/`ProviderMark` 本地渲染，无外链图片。
- 空状态一律说明原因+下一步；离线统一 Banner/ErrorState + "查看诊断"折叠。

## 与视觉稿的已知差异（诚实性保留）

- 能力页无雷达图（后端无维度评分数据，用真实指标带替代）；视觉稿的"优势/待提升/建议表"映射为节点详情内的个人状态与投资建议。
- 历史页行内无公司/岗位名（申请投影只有 ID），以 ID+状态徽标呈现。
- 知识页不做按来源筛选检索结果的左栏（结果无来源类型字段）。
- 模型卡片暂无"删除/设为默认"（后端无端点）。
