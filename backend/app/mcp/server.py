"""Optional stdio MCP entrypoint for external clients."""

from __future__ import annotations

import json
import sys

from app.db.session import SessionLocal, init_db
from app.mcp.tools import MCPServer
from app.repositories import PlanRepository
from app.seed import seed_if_empty
from app.services.plan_service import PlanService


def main() -> None:
    init_db()
    session = SessionLocal()
    try:
        seed_if_empty(session)
        session.commit()
        mcp = MCPServer(PlanService(PlanRepository(session)))
        print(json.dumps({"tools": [t.model_dump() for t in mcp.list_tools()]}), flush=True)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            req = json.loads(line)
            name = req.get("tool") or req.get("name")
            args = req.get("arguments") or req.get("args") or {}
            result = mcp.call_tool(name, args)
            session.commit()
            print(json.dumps(result, default=str), flush=True)
    finally:
        session.close()


if __name__ == "__main__":
    main()
