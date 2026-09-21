import "./RecordLookup.css";
export function StructuredSections({ value }: { value: Record<string, unknown> }) {
  const labels: Record<string, string> = {
    summary: "个人简介",
    experience: "工作经历",
    work_experience: "工作经历",
    projects: "项目经历",
    skills: "技能",
    education: "教育经历",
    certifications: "证书与认证",
  };
  const content = (item: unknown) => {
    if (typeof item === "string" || typeof item === "number") return <p>{String(item)}</p>;
    if (typeof item === "boolean") return <p>{item ? "是" : "否"}</p>;
    if (item === null) return <p>未填写</p>;
    return <pre>{JSON.stringify(item, null, 2)}</pre>;
  };
  return Object.keys(value).length
    ? <div>{Object.entries(value).map(([key, item]) => <section key={key}><h3>{labels[key] ?? key}</h3>{content(item)}</section>)}</div>
    : <p>该记录内容为空。</p>;
}
