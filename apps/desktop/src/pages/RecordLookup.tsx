import { Award, BriefcaseBusiness, FileText, FolderKanban, GraduationCap, UserRound, Wrench, type LucideIcon } from "lucide-react";
import "./RecordLookup.css";

const sectionMeta: Record<string, { label: string; icon: LucideIcon; hint: string }> = {
  summary: { label: "基本信息", icon: UserRound, hint: "姓名、联系方式、求职意向" },
  experience: { label: "工作经历", icon: BriefcaseBusiness, hint: "公司、职位、职责与成果" },
  work_experience: { label: "工作经历", icon: BriefcaseBusiness, hint: "公司、职位、职责与成果" },
  projects: { label: "项目经历", icon: FolderKanban, hint: "项目描述、个人贡献、成果" },
  skills: { label: "技能证书", icon: Wrench, hint: "专业技能、证书与工具" },
  education: { label: "教育经历", icon: GraduationCap, hint: "学校、专业、时间" },
  certifications: { label: "技能证书", icon: Award, hint: "专业技能、证书与工具" },
};

export function StructuredSections({ value }: { value: Record<string, unknown> }) {
  const content = (item: unknown) => {
    if (typeof item === "string" || typeof item === "number") return <p>{String(item)}</p>;
    if (typeof item === "boolean") return <p>{item ? "是" : "否"}</p>;
    if (item === null) return <p>未填写</p>;
    return <pre>{JSON.stringify(item, null, 2)}</pre>;
  };
  return Object.keys(value).length
    ? (
      <div className="structured-sections">
        {Object.entries(value).map(([key, item]) => {
          const meta = sectionMeta[key] ?? { label: key, icon: FileText, hint: "" };
          const Icon = meta.icon;
          return (
            <section className="fact-row" key={key}>
              <header>
                <span className="section__icon" aria-hidden="true"><Icon size={14} /></span>
                <span className="fact-row__id">
                  <h3>{meta.label}</h3>
                  {meta.hint ? <small>{meta.hint}</small> : null}
                </span>
              </header>
              <div className="fact-row__content">{content(item)}</div>
            </section>
          );
        })}
      </div>
    )
    : <p className="text-aux">该记录内容为空。</p>;
}
