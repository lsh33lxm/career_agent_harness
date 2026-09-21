# v2.0 Autonomous Blockers

更新时间：2026-09-22

## 当前状态

Slice A–E 的 local/offline Definition of Done 已完成；没有阻塞本地实现、测试、回归或文档收口的 P0/P1。下列条目是明确登记的外部边界，不能由当前仓库自行授权。

## External boundaries

- `BLOCKED_EXTERNAL_ACTION`：真实 Feishu/Gmail/Notion/ATS 写入需要凭据、权限和单独授权；当前只保留离线 contract、proposal 或 projection。
- `NEEDS_USER_AUTHORITY`：legacy canonical identity、个人事实 promotion 或 authority 冲突不得由插件自动解决。
- `BLOCKED_EXTERNAL_ACTION`：第三方插件的许可证、NOTICE、条款、immutable commit、install scripts、依赖漏洞和网络域名未核验前只能进入 quarantined/preview；离线 manifest 声明不解除隔离，真实 marketplace 下载与第三方 worker 执行不启用。
- `BLOCKED_EXTERNAL_ACTION`：`career-kb-weknora` 没有配置 endpoint/credential 或已核验条款；adapter 保持 read-only，不发网络请求。
- `BLOCKED_EXTERNAL_ACTION`：真实 ATS 提交、第三方模板执行和 Magic Resume 代码/资产复用未获授权；Resume Studio 只生成本地 preview/PDF Artifact。
- `BLOCKED_EXTERNAL_ACTION`：当前机器未配置 Typst sandbox/compiler；Typst 模板保持 disabled，HTML renderer、Resume Core 和生命周期验收不受影响。
- `QUARANTINED_EXTERNAL_SOURCE`：JobSpy、WebMagic/JobHunter 和 AI Job Search portal 尚未完成许可证、robots/ToS、登录边界、网络权限与 credentials 审核；Slice D 只启用 manual/offline source，并在每次 run 保存 terms note 与 checked-at provenance。
- `BLOCKED_EXTERNAL_ACTION`：模型 provider 配置与安全存储已实现，但仓库/运行环境没有用户 API key，因此没有执行真实 OpenAI、Anthropic 或 DeepSeek 连接与对话验收。页面必须保持“尚未配置/尚未测试”，不能用 synthetic connector 冒充外部成功。
- `BLOCKED_EXTERNAL_ACTION`：GitHub 静态分析链路与合成 fixture 已通过，但当前运行环境无法连接 `github.com:443`；真实 `octocat/Hello-World` 只读 clone 返回 connection failure。需要网络可达后重新执行公开仓库验收，不得将合成 fixture 写成真实 GitHub 成功。

这些边界不改变 A–E 的完成状态，也不允许通过猜测、静默降级或自动外部写入来解除。
