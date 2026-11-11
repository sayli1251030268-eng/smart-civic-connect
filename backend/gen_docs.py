"""Regenerates docs/API.md and docs/DATABASE.md from the code: python gen_docs.py"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
from fastapi.routing import APIRoute
import app.models  # noqa: registers tables
from app.main import app as api
from app.database import Base

spec = api.openapi()
OUT = os.path.join(os.path.dirname(__file__), "..", "docs")

def resolve(schema):
    if "$ref" in schema:
        return spec["components"]["schemas"][schema["$ref"].split("/")[-1]]
    return schema

def access(route):
    found = {"roles": None, "verified": False, "login": False, "optional": False}
    def walk(d):
        for s in d.dependencies:
            c = s.call
            if not hasattr(c, "__name__"):
                continue
            if c.__name__ == "verified_rep": found["verified"] = True
            elif c.__name__ == "current_user": found["login"] = True
            elif c.__name__ == "optional_user": found["optional"] = True
            elif c.__name__ == "dep" and c.__module__.endswith("security"):
                found["roles"] = "/".join(c.__closure__[0].cell_contents)
            walk(s)
    walk(route.dependant)
    if found["verified"]: return "Verified representative"
    if found["roles"]: return f"Role: {found['roles']}"
    if found["login"]: return "Login required"
    if found["optional"]: return "Optional login"
    return "Public"

def inputs(op):
    parts = []
    q = [p["name"] + ("*" if p.get("required") else "") for p in op.get("parameters", [])]
    if q: parts.append("query/path: " + ", ".join(q))
    for ctype, body in op.get("requestBody", {}).get("content", {}).items():
        sch = resolve(body["schema"])
        req = set(sch.get("required", []))
        fields = ", ".join(k + ("*" if k in req else "") for k in sch.get("properties", {}))
        parts.append(("form" if "multipart" in ctype else "json") + ": " + fields)
    return "<br>".join(parts) or "none"

NOTES = {
    ("POST", "/auth/register"): "Create an account. Representatives start unverified. Returns a JWT and the user.",
    ("POST", "/auth/login"): "Returns a JWT (valid 7 days) and the user.",
    ("GET", "/auth/me"): "The logged-in user.",
    ("GET", "/categories"): "Valid complaint categories.",
    ("POST", "/complaints/check-duplicates"): "Suggest similar nearby complaints before filing (GPS plus photo similarity).",
    ("POST", "/complaints"): "File a complaint with optional photo. Returns 409 with suggestions if similar ones exist; resend with force=true to file anyway.",
    ("GET", "/complaints"): "Feed. feed = all, nearby (needs lat, lng, radius_km), trending (by community support), or mine. Filters: category, status, ward.",
    ("GET", "/complaints/{cid}"): "One complaint with counts, the caller's own interactions and full status history.",
    ("POST", "/complaints/{cid}/support"): "Toggle support (I face this too). Returns the updated complaint.",
    ("POST", "/complaints/{cid}/like"): "Toggle like.",
    ("POST", "/complaints/{cid}/repost"): "Toggle repost.",
    ("GET", "/complaints/{cid}/comments"): "Comments, oldest first, with author role and verified badge.",
    ("POST", "/complaints/{cid}/comments"): "Add a comment. Notifies the reporter.",
    ("GET", "/notifications"): "The caller's latest 50 notifications.",
    ("POST", "/notifications/read"): "Mark all notifications read.",
    ("GET", "/admin/departments"): "Municipal departments.",
    ("PATCH", "/admin/complaints/{cid}/status"): "Move a complaint to the next valid status. Assigning needs department_id; resolving needs an after photo. Notifies reporter and supporters.",
    ("GET", "/admin/analytics"): "Totals by status and category, plus average resolution time in hours.",
    ("GET", "/admin/representatives/pending"): "Representatives awaiting verification.",
    ("POST", "/admin/representatives/{uid}/verify"): "Verify a representative after checking credentials.",
    ("GET", "/updates"): "Public development updates, newest first. Optional ward filter.",
    ("POST", "/updates"): "Publish a development update with optional before and after photos.",
    ("DELETE", "/updates/{uid}"): "Delete one of your own updates.",
    ("GET", "/health"): "Liveness check.",
}

groups = {}
for r in api.routes:
    if not isinstance(r, APIRoute) or r.path in ("/openapi.json",):
        continue
    op = spec["paths"][r.path][list(r.methods)[0].lower()]
    tag = (op.get("tags") or ["other"])[0]
    m0 = list(r.methods - {"HEAD"})[0]
    doc = NOTES.get((m0, r.path)) or (r.endpoint.__doc__ or "").strip().split("\n")[0]
    groups.setdefault(tag, []).append((list(r.methods - {"HEAD"})[0], r.path, access(r), doc, inputs(op)))

md = ["# API reference", "", "Generated from the code by `backend/gen_docs.py`. Interactive docs: `/docs` on the running backend.",
      "", "`*` marks a required field. Authenticated calls send `Authorization: Bearer <token>`. "
      "Errors return `{\"detail\": \"message\"}`; `409` on `POST /complaints` returns similar-complaint suggestions.", ""]
for tag, rows in groups.items():
    md += [f"## {tag.capitalize()}", "", "| Method | Path | Access | Inputs | Notes |", "|---|---|---|---|---|"]
    md += [f"| {m} | `{p}` | {a} | {i} | {d} |" for m, p, a, d, i in rows]
    md.append("")
open(os.path.join(OUT, "API.md"), "w").write("\n".join(md))

db = ["# Database schema", "", "Generated from the SQLAlchemy models by `backend/gen_docs.py`. SQLite for development, MySQL 8 in production.",
      "", "Design rule: one canonical row in `complaints` per real-world issue. Supports, likes, reposts and comments reference it and never create new official complaints.", "",
      "```mermaid", "erDiagram"]
for t in Base.metadata.sorted_tables:
    for fk in t.foreign_keys:
        db.append(f"    {fk.column.table.name} ||--o{{ {t.name} : \"{fk.parent.name}\"")
db += ["```", ""]
for t in Base.metadata.sorted_tables:
    db += [f"## {t.name}", "", "| Column | Type | Notes |", "|---|---|---|"]
    for c in t.columns:
        n = []
        if c.primary_key: n.append("primary key")
        for fk in c.foreign_keys: n.append(f"references {fk.column.table.name}.{fk.column.name}")
        if c.unique: n.append("unique")
        if not c.nullable and not c.primary_key: n.append("required")
        if c.index: n.append("indexed")
        db.append(f"| {c.name} | {c.type} | {', '.join(n)} |")
    uq = [", ".join(x.name for x in u.columns) for u in t.constraints if u.__class__.__name__ == "UniqueConstraint"]
    if uq: db += ["", "Unique together: " + "; ".join(f"({u})" for u in uq)]
    db.append("")
open(os.path.join(OUT, "DATABASE.md"), "w").write("\n".join(db))
print("wrote", sum(len(v) for v in groups.values()), "endpoints,", len(Base.metadata.tables), "tables")
