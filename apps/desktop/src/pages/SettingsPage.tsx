import {
  Database, Github, Link2, Monitor, NotebookText, RotateCcw, ShieldCheck, SlidersHorizontal,
} from "lucide-react";

import { useHealth } from "../api/useHealth";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { Button } from "../components/ui/Button";

const settingsNav = [
  { id: "settings-connections", label: "连接状态", icon: Link2 },
  { id: "settings-preferences", label: "偏好设置", icon: SlidersHorizontal },
  { id: "settings-privacy", label: "隐私与数据", icon: ShieldCheck },
  { id: "settings-local", label: "本地服务", icon: Monitor },
] as const;

const notConnected = <span className="badge">尚未连接</span>;
const notWired = <span className="badge">尚未接入</span>;

/** 设置页：分类组织；未接入的能力显示为可理解的系统状态，而不是空白卡片。 */
export function SettingsPage() {
  const [health, retryHealth] = useHealth();
  return (
    <main className="page page--wide">
      <PageHeader
        eyebrow="职业工作台"
        title="设置"
        description="管理你的工作台偏好、连接与数据，让观复更好地为你服务。"
        art
      />

      <div className="settings-layout">
        <nav className="settings-nav" aria-label="设置分区">
          {settingsNav.map(({ id, label, icon: Icon }) => (
            <a key={id} href={`#${id}`}>
              <Icon size={15} aria-hidden="true" />
              <span>{label}</span>
            </a>
          ))}
        </nav>

        <div className="settings-main">
          <Surface>
            <Section
              title="连接状态"
              icon={Link2}
              description="管理与第三方服务的连接，获取最新数据以提升你的使用体验。"
              ariaLabel="连接状态"
              className="settings-section"
            >
              <div id="settings-connections" className="settings-anchor" />
              <div className="settings-rows">
                <div className="settings-row">
                  <span className="section__icon"><Github size={15} aria-hidden="true" /></span>
                  <div><strong>代码托管平台</strong><p className="text-aux">用于导入项目经历、贡献记录等</p></div>
                  {notConnected}
                </div>
                <div className="settings-row">
                  <span className="section__icon"><NotebookText size={15} aria-hidden="true" /></span>
                  <div><strong>笔记与文档</strong><p className="text-aux">用于导入学习笔记、项目文档等</p></div>
                  {notConnected}
                </div>
                <div className="settings-row settings-row--muted">
                  <span className="section__icon"><Link2 size={15} aria-hidden="true" /></span>
                  <div><strong>连接更多服务</strong><p className="text-aux">支持 GitHub、Notion 等，持续扩展中</p></div>
                  {notWired}
                </div>
              </div>
            </Section>
          </Surface>

          <Surface>
            <Section
              title="偏好设置"
              icon={SlidersHorizontal}
              description="自定义工作台的显示与使用习惯。"
              ariaLabel="偏好设置"
              className="settings-section"
            >
              <div id="settings-preferences" className="settings-anchor" />
              <div className="settings-rows">
                <div className="settings-row">
                  <span className="section__icon"><Monitor size={15} aria-hidden="true" /></span>
                  <div><strong>主题模式</strong><p className="text-aux">跟随系统，保持舒适的浏览体验</p></div>
                  {notWired}
                </div>
                <div className="settings-row">
                  <span className="section__icon"><ShieldCheck size={15} aria-hidden="true" /></span>
                  <div><strong>通知提醒</strong><p className="text-aux">接收重要进展与待办提醒</p></div>
                  {notWired}
                </div>
                <div className="settings-row">
                  <span className="section__icon"><Database size={15} aria-hidden="true" /></span>
                  <div><strong>首页默认视图</strong><p className="text-aux">登录后默认进入的页面</p></div>
                  {notWired}
                </div>
              </div>
              <p className="text-aux" style={{ marginTop: "var(--space-3)" }}>偏好设置尚未接入本地配置，当前不会读取或修改任何本地文件。</p>
            </Section>
          </Surface>

          <Surface>
            <Section
              title="隐私与数据"
              icon={ShieldCheck}
              description="管理你的数据、隐私和导出选项。"
              ariaLabel="隐私与数据"
              className="settings-section"
            >
              <div id="settings-privacy" className="settings-anchor" />
              <div className="settings-rows">
                <div className="settings-row">
                  <span className="section__icon"><Database size={15} aria-hidden="true" /></span>
                  <div><strong>数据管理</strong><p className="text-aux">导出、删除或清理你的个人数据</p></div>
                  {notWired}
                </div>
              </div>
              <p className="text-aux" style={{ marginTop: "var(--space-3)" }}>观复是本地优先应用：数据仅保存在你的设备上，不会上传到云端。</p>
            </Section>
          </Surface>
        </div>

        <aside className="settings-rail">
          <Surface>
            <Section
              title="本地服务"
              icon={Monitor}
              meta={<a href="#settings-local" className="text-aux">查看诊断</a>}
              ariaLabel="本地服务"
            >
              <div id="settings-local" className="settings-anchor" />
              <div className={health.status === "online" ? "settings-service settings-service--online" : "settings-service"}>
                <strong>{health.status === "online" ? "本地服务已连接" : health.status === "offline" ? "本地服务离线" : "正在连接本地服务"}</strong>
                <p className="text-aux">{health.status === "online" ? "数据已就绪 · 专注前行" : "本地服务用于支持简历解析、文件处理等功能，数据仅保存在你的设备上。"}</p>
              </div>
              <dl className="dl" style={{ marginTop: "var(--space-3)" }}>
                <div><dt>服务状态</dt><dd>{health.status === "online" ? "正在运行" : health.status === "offline" ? "未响应" : "连接中"}</dd></div>
                <div><dt>版本信息</dt><dd>{health.status === "online" ? `v${health.data.version}` : "—"}</dd></div>
                <div><dt>运行环境</dt><dd>{health.status === "online" ? health.data.environment : "—"}</dd></div>
              </dl>
              <div className="resume-actions" style={{ marginTop: "var(--space-3)" }}>
                <Button size="sm" variant="secondary" onClick={retryHealth} icon={<RotateCcw size={13} aria-hidden="true" />}>重新检查</Button>
              </div>
              {health.status === "offline" && (
                <details className="state__details" style={{ marginTop: "var(--space-3)" }}>
                  <summary>查看诊断</summary>
                  <pre>{health.message}</pre>
                </details>
              )}
              <p className="text-aux" style={{ marginTop: "var(--space-3)" }}>如遇到连接问题，可尝试重新启动本地服务或查看诊断信息。</p>
            </Section>
          </Surface>
        </aside>
      </div>
    </main>
  );
}
