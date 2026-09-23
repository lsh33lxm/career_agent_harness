import { describe, expect, it } from "vitest";

import { listDemoJobs } from "./demoJobs";

describe("demo job projection", () => {
  it("exposes stable, redacted job summaries", () => {
    const first = listDemoJobs();
    const second = listDemoJobs();
    expect(first).toEqual([]);
    expect(first.map((job) => job.staging_id)).toEqual(second.map((job) => job.staging_id));
    expect(first.every((job) => job.source_url === null)).toBe(true);
    expect(first.every((job) => job.source_path.includes("演示数据包"))).toBe(true);
  });
});
