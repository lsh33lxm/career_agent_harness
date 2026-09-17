import { Inbox } from "lucide-react";

interface SectionPageProps {
  title: string;
  emptyLabel: string;
}

export function SectionPage({ title, emptyLabel }: SectionPageProps) {
  return (
    <main className="page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>{title}</h1>
        </div>
      </div>
      <section className="work-queue">
        <div className="section-heading">
          <h2>Overview</h2>
          <span>0 items</span>
        </div>
        <div className="empty-state">
          <div className="empty-state-mark" aria-hidden="true">
            <Inbox size={22} />
          </div>
          <h3>{emptyLabel}</h3>
        </div>
      </section>
    </main>
  );
}
