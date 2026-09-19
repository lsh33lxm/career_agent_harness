import {
  AlertCircle, ArrowRight, Check, CheckCircle2, ChevronRight, ClipboardCheck,
  FileText, Link2, RefreshCw, ScanText, Upload,
} from "lucide-react";

import { useHealth } from "../api/useHealth";
import { getTodayFallback } from "./today/data";

const today = getTodayFallback();
const priorityLabels = { urgent: "紧急", high: "高", medium: "中", low: "低" };

export function TodayPage() {
  const [health, retry] = useHealth();
  return (
    <main className="today-page">
      <header className="today-hero">
        <div>
          <div className="today-title-row"><h1>今天</h1><time>{today.dateLabel}</time></div>
          <p>在不确定的时代，做更清醒的选择。</p>
        </div>
        <div className="today-sunrise" aria-hidden="true">
          <span className="sunrise-sun" /><span className="sunrise-hill sunrise-hill--near" />
          <span className="sunrise-hill sunrise-hill--far" />
        </div>
        <p className="today-motto">积累真实的自己<br />走向更大的可能</p>
        <div className={`service-status service-status--${health.status}`} aria-live="polite">
          {health.status === "loading" && <span className="status-spinner" aria-hidden="true" />}
          {health.status === "online" && <CheckCircle2 size={16} aria-hidden="true" />}
          {health.status === "offline" && <AlertCircle size={16} aria-hidden="true" />}
          <span>{health.status === "online" ? `Core ${health.data.version}` : health.status === "loading" ? "连接中" : "Core 离线"}</span>
          {health.status === "offline" && <button type="button" onClick={retry} title="重试连接" aria-label="重试连接"><RefreshCw size={15} /></button>}
        </div>
      </header>

      <div className="today-layout">
        <div className="today-main-column">
          <section className="today-panel focus-panel" aria-labelledby="focus-title">
            <h2 className="today-section-title" id="focus-title"><span />今日焦点</h2>
            <div className="focus-content">
              <div className="focus-icon" aria-hidden="true"><FileText size={34} /></div>
              <div><h3>{today.focus.title}</h3><p>{today.focus.description}</p>
                <div className="focus-actions">
                  <button className="today-primary" type="button">{today.focus.actionLabel}<ArrowRight size={17} /></button>
                  <button className="today-link" type="button"><ClipboardCheck size={16} />{today.focus.evidenceLabel}</button>
                </div>
              </div>
              <p className="focus-note">好机会<br />从准备好开始</p>
            </div>
          </section>

          <section className="today-panel opportunity-stream" aria-labelledby="stream-title">
            <div className="today-section-heading">
              <h2 className="today-section-title" id="stream-title"><span />机会流</h2>
              <a href="/opportunities">查看全部<ArrowRight size={15} /></a>
            </div>
            <div className="today-opportunities">
              {today.opportunities.map((item) => (
                <article className="today-opportunity" key={item.id}>
                  <div className="company-glyph" aria-hidden="true">{item.company.slice(0, 1)}</div>
                  <div className="today-opportunity-name"><h3>{item.role}</h3><span>{item.company} · {item.location}</span><small>来自 <mark>{item.source}</mark></small></div>
                  <div className="today-match"><strong>{item.matchPercent}%</strong><span>匹配度</span></div>
                  <div className="today-opportunity-reason"><p>{item.reason}</p><div className="priority-pair"><span>系统建议 {priorityLabels[item.suggestedPriority]}</span><span>用户优先级 {priorityLabels[item.userPriority]}</span></div></div>
                  <ChevronRight size={18} aria-hidden="true" />
                </article>
              ))}
            </div>
          </section>

          <section className="today-panel weekly-panel" aria-labelledby="weekly-title">
            <h2 className="today-section-title" id="weekly-title"><span />本周回看 <small>9月16日 – 9月22日</small></h2>
            <div className="week-track">
              {today.weeklySteps.map((step, index) => <div className={`week-step week-step--${step.state}`} key={step.label}><div className="week-marker">{step.state === "done" && <Check size={15} />}</div>{index < today.weeklySteps.length - 1 && <span className="week-line" />}<strong>{step.label}</strong><small>{step.date}</small></div>)}
            </div>
            <blockquote>“这一周我更主动了，不再只是浏览，而是真正迈出了几步。”</blockquote>
          </section>
        </div>

        <aside className="today-side-column">
          <section className="today-panel confirmation-panel" aria-labelledby="confirm-title">
            <h2 className="today-section-title" id="confirm-title"><span />需要你确认 <small>{today.confirmations.length} 项</small></h2>
            <div className="confirmation-list">{today.confirmations.map((item) => <article className="confirmation-item" key={item.id}><div className="confirmation-icon" aria-hidden="true"><ScanText size={22} /></div><div><h3>{item.title}</h3><strong>{item.subtitle}</strong><small>来自 <mark>{item.source}</mark> · {item.date}</small><p>{item.description}</p><div><button className="today-secondary" type="button">{item.actionLabel}</button><button className="today-quiet" type="button">稍后处理</button></div></div></article>)}</div>
          </section>

          <section className="today-panel capture-panel" aria-labelledby="capture-title">
            <h2 className="today-section-title" id="capture-title"><span />快速收集</h2>
            <button className="capture-input" type="button"><Link2 size={17} />粘贴链接（职位、文章、公司页面等）</button>
            <div className="capture-tools"><button type="button"><Upload size={16} />上传 PDF</button><button type="button"><ScanText size={16} />截图识别</button><button type="button"><FileText size={16} />粘贴文本</button></div>
            <p>收集有价值的信息，让选择更有依据。</p>
            <div className="week-progress" aria-label={`本周进度 ${today.completedSteps}/4`}><div><small>本周进度</small><strong>{today.completedSteps}/4</strong></div></div>
            <p className="capture-note">稳步前行<br />已经走在更好的路上</p>
          </section>
        </aside>
      </div>
    </main>
  );
}
