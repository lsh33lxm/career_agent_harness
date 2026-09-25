import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ListChecks, RefreshCw, RotateCcw } from "lucide-react";

import {
  getTask,
  listTasks,
  retryTask,
  runTaskStage,
  type TaskDetail,
  type TaskRecord,
  type TaskStatus,
} from "../api/tasks";
import { displayLabel, taskStageLabels } from "../app/displayLabels";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState } from "../components/ui/States";
import { Button } from "../components/ui/Button";
import { ErrorNotice, InlineNotice } from "../components/ui/Notice";

const statusLabels: Record<TaskStatus, string> = {
  pending: "等待执行",
  processing: "执行中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
  retrying: "等待重试",
  finalizing: "正在收尾",
  dead_letter: "需要人工处理",
};

const taskLabels: Record<string, string> = {
  "local.health_check": "本地运行检查",
  "source.local_folder_sync": "本地文件夹同步",
  "source.legacy_agent_radar_sync": "Legacy 历史数据同步",
  "source.github_sync": "GitHub 只读同步",
};

const date = (value: string) => new Intl.DateTimeFormat("zh-CN", {
  dateStyle: "medium",
  timeStyle: "short",
}).format(new Date(value));

function taskName(task: TaskRecord): string {
  return taskLabels[task.task_type] ?? task.task_type.replaceAll("_", " ").replaceAll(".", " · ");
}

export function TaskQueuePanel() {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [message, setMessage] = useState("正在读取任务队列…");
  const [messageDetail, setMessageDetail] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      setTasks(await listTasks(signal));
      setMessage("");
    } catch (error) {
      if (!signal?.aborted) {
        setMessage("任务队列读取失败，请确认本地服务已启动。");
        setMessageDetail((error as Error).message);
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function inspect(task: TaskRecord) {
    if (detail?.task.task_id === task.task_id) {
      setDetail(null);
      return;
    }
    setBusy(`${task.task_id}:detail`);
    try {
      setDetail(await getTask(task.task_id));
    } catch (error) {
      setMessage("任务详情读取失败，请重试。");
      setMessageDetail((error as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function retry(task: TaskRecord) {
    setBusy(`${task.task_id}:retry`);
    try {
      await retryTask(task.task_id);
      const results = await runTaskStage(task.stage);
      const retried = results.find((item) => item.task_id === task.task_id);
      const outcomeMessage = (
        retried?.status === "completed"
          ? `“${taskName(task)}”人工重试已完成。`
          : `“${taskName(task)}”已执行人工重试，请查看最新状态。`
      );
      setDetail(null);
      await load();
      setMessage(outcomeMessage);
      setMessageDetail("");
    } catch (error) {
      setMessage("人工重试失败，请重试。");
      setMessageDetail((error as Error).message);
    } finally {
      setBusy("");
    }
  }

  const failures = tasks.filter((task) => task.status === "failed" || task.status === "dead_letter").length;

  return (
    <Surface>
      <Section
        title="任务队列"
        description="查看同步与处理任务的进度、失败原因和不可变尝试记录。"
        meta={failures > 0
          ? <span className="badge badge--danger"><AlertTriangle size={12} aria-hidden="true" />{failures} 项待处理</span>
          : <span className="badge badge--green"><ListChecks size={12} aria-hidden="true" />队列正常</span>}
      >
        {message && (
          <div style={{ marginBottom: "var(--space-4)" }}>
            {messageDetail
              ? <ErrorNotice label={message} detail={messageDetail} />
              : <InlineNotice tone={message.includes("失败") ? "danger" : message.includes("完成") || message.includes("正常") ? "success" : "muted"} role="status">{message}</InlineNotice>}
          </div>
        )}
        {tasks.length === 0 && !message && (
          <EmptyState compact icon={ListChecks} title="当前没有任务记录" description="同步资料源后，任务会显示在这里。" />
        )}
        <div className="plugin-grid" aria-label="任务列表">
          {tasks.map((task) => {
            const selected = detail?.task.task_id === task.task_id;
            const retryable = task.status === "failed" || task.status === "dead_letter";
            return (
              <article className="plugin-card" key={task.task_id}>
                <div className="plugin-card__head">
                  <div className="plugin-icon" aria-hidden="true"><ListChecks size={17} /></div>
                  <div>
                    <h3>{taskName(task)}</h3>
                    <p>{date(task.updated_at)}</p>
                  </div>
                  <span className={task.status === "failed" || task.status === "dead_letter" ? "badge badge--danger" : task.status === "completed" ? "badge badge--green" : "badge"}>{statusLabels[task.status]}</span>
                </div>
                <dl className="dl plugin-meta">
                  <div><dt>进度</dt><dd>{Math.round(task.progress * 100)}%</dd></div>
                  <div><dt>尝试</dt><dd>{task.current_attempt} / {task.max_attempts}</dd></div>
                  <div><dt>阶段</dt><dd>{displayLabel(task.stage, taskStageLabels)}</dd></div>
                </dl>
                {task.last_error && <p className="text-aux">最近错误：{task.last_error}</p>}
                <div className="plugin-actions">
                  <Button size="sm" variant="secondary" loading={busy === `${task.task_id}:detail`} disabled={Boolean(busy)} onClick={() => void inspect(task)} icon={<RefreshCw size={13} aria-hidden="true" />}>
                    {selected ? "收起记录" : "查看尝试记录"}
                  </Button>
                  {retryable && (
                    <Button size="sm" variant="secondary" loading={busy === `${task.task_id}:retry`} disabled={Boolean(busy)} onClick={() => void retry(task)} icon={<RotateCcw size={13} aria-hidden="true" />}>人工重试</Button>
                  )}
                </div>
                {selected && (
                  <section className="plugin-audit" aria-label={`${taskName(task)}尝试记录`}>
                    <h3>不可变尝试记录</h3>
                    {detail.attempts.length === 0 ? <p>尚无已结束的尝试。</p> : (
                      <ol>
                        {detail.attempts.map((attempt) => (
                          <li key={`${attempt.task_id}:${attempt.attempt}`}>
                            第 {attempt.attempt} 次 · {attempt.status === "completed" ? "已完成" : attempt.status === "failed" ? "失败" : attempt.status === "cancelled" ? "已取消" : "已过期"}
                            {attempt.error_message ? ` · ${attempt.error_message}` : ""}
                          </li>
                        ))}
                      </ol>
                    )}
                  </section>
                )}
              </article>
            );
          })}
        </div>
      </Section>
    </Surface>
  );
}
