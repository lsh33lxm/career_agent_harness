export interface KnowledgeCitation {
  knowledge_id: string;
  revision: number;
  evidence_refs: string[];
  source_type: string;
  source_locator: string;
  authority: string;
}

export interface KnowledgeSearchResult {
  knowledge_id: string;
  revision: number;
  title: string;
  snippet: string;
  score: number;
  category: string;
  status: string;
  citation: KnowledgeCitation;
}

export interface KnowledgeSearchPage {
  items: KnowledgeSearchResult[];
  query: string;
  evidence_sufficient: boolean;
  message: string | null;
  next_cursor: string | null;
}
