# v2.0 Autonomous Blockers

当前没有阻塞 Slice A 本地实现的 blocker。

当前没有阻塞 Slice B 本地实现的 blocker；Slice C 可继续离线推进。

当前没有阻塞 Slice C 本地实现的 blocker；Slice D 可继续使用 manual/offline source。

预先登记的外部边界：

- `BLOCKED_EXTERNAL_ACTION`：真实 Feishu/Gmail/Notion/ATS 写入需要凭据、权限和单独授权；本轮只实现离线 contract、proposal 或 projection。
- `NEEDS_USER_AUTHORITY`：任何 legacy canonical identity、个人事实 promotion 或 authority 冲突不得由插件自动解决。
- `BLOCKED_EXTERNAL_ACTION`：第三方插件的许可证、条款和 immutable commit 未验证前只能进入 quarantined/preview 状态。
- `BLOCKED_EXTERNAL_ACTION`：`career-kb-weknora` 没有配置 endpoint、credential 或已核验条款；当前 adapter 保持 read-only blocked，不发网络请求。
- `BLOCKED_EXTERNAL_ACTION`：真实 ATS 提交、第三方模板执行和 Magic Resume 代码/资产复用未获授权；当前 Resume Studio 只生成本地 preview/PDF Artifact。
- `BLOCKED_EXTERNAL_ACTION`：JobSpy、WebMagic/JobHunter 和 AI Job Search portal 尚未核验许可证、robots/ToS、登录边界和网络域名；Slice D 仅启用 manual/offline source，不发外部网络请求。
- `BLOCKED_EXTERNAL_ACTION`：真实 marketplace 下载、第三方 plugin worker 执行与在线依赖扫描需要明确来源、immutable commit、许可证和网络权限；Slice E 当前只对 repository-owned releases 做离线 lifecycle 验收。
