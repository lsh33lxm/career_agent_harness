"""临时 mock：本地职业核心空数据响应，仅用于 UI 空态/在线态截图验证。"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

EMPTY_ARRAY_PATHS = {
    "/api/v1/opportunities",
    "/api/v1/plugins",
    "/api/v1/projects",
    "/api/v1/resumes",
    "/api/v1/applications",
    "/api/v1/evidence",
    "/api/v1/tasks",
    "/api/v1/model-providers",
    "/api/v1/source-connectors",
    "/api/v1/capabilities/identities",
    "/api/v1/capability-inbox",
    "/api/v1/communications/drafts",
    "/api/v1/memory",
    "/api/v1/memory/proposals",
}

OVERVIEW = {
    "data_as_of": None,
    "job_count": 0,
    "interview_count": 0,
    "question_count": 0,
    "coding_count": 0,
    "needs_review_count": 0,
    "top_skills": [],
    "top_companies": [],
    "top_locations": [],
    "questions": [],
    "interviews": [],
}

IMPORT_STATUS = {
    "configured_source_root": None,
    "source_accessible": False,
    "latest_report": None,
}

TODAY = {
    "items": [],
    "input_revisions": [],
    "generated_at": "2026-09-23T08:00:00Z",
    "policy_version": "mock-ui-review",
}

COMMUNICATION_SUMMARY = {
    "created_today": 0,
    "daily_limit": 0,
    "remaining_today": 0,
    "reply_count": 0,
    "follow_up_count": 0,
    "channel_counts": {},
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        self._send({})

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0].rstrip("/") or "/"
        if path == "/health":
            self._send({
                "status": "ok",
                "service": "agent-career-harness",
                "version": "0.0.0-mock",
                "environment": "ui-review",
            })
        elif path == "/api/v1/today":
            self._send(TODAY)
        elif path == "/api/v1/legacy/knowledge-overview":
            self._send(OVERVIEW)
        elif path == "/api/v1/legacy/status":
            self._send(IMPORT_STATUS)
        elif path == "/api/v1/communications/summary":
            self._send(COMMUNICATION_SUMMARY)
        elif path == "/api/v1/wiki/health":
            self._send({"detail": "not found"}, 404)
        elif path in EMPTY_ARRAY_PATHS:
            self._send([])
        else:
            self._send([], 200)

    def do_POST(self):  # noqa: N802
        path = self.path.split("?")[0].rstrip("/") or "/"
        if path == "/api/v1/jobs/search":
            self._send([])
        elif path == "/api/v1/knowledge/search":
            self._send({"items": [], "message": "没有可引用的已确认知识。"})
        else:
            self._send({"detail": "mock server is read-only"}, 405)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
