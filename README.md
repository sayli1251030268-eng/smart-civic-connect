# Smart Civic Connect

AI-powered community civic management platform connecting Citizens, Local Representatives, and Municipal Authorities.

**Live Deployment (Render):** [https://smart-civic-connect-ob2z.onrender.com/](https://smart-civic-connect-ob2z.onrender.com/)  
**Interactive API Documentation:** [https://smart-civic-connect-ob2z.onrender.com/docs](https://smart-civic-connect-ob2z.onrender.com/docs)  
**Stack:** FastAPI (Python 3.12), SQLite / MySQL (SQLAlchemy 2.0), React 18, Tailwind CSS, Leaflet Maps, and PyTorch/CLIP AI layer.

---

## Evaluation Credentials

For judges and evaluators reviewing the live platform:

### 1. Municipal Administrator (Full Control)
- **Email / Username:** `admin@civic.local`
- **Password:** `Admin@12345`
- **Dashboard URL:** `/admin` (or click "Dashboard" in header)
- **Key Capabilities:** Review real-time KPIs, assign departments, inspect AI briefings, upload repair completion proof, run auto-escalation scans, and moderate reported abuse.

### 2. Local Elected Representative (Nagarsevak / MLA)
- **Email:** `nagarsevak.patil@pmc.gov.in`
- **Password:** `Patil@12345`
- **Ward:** Kothrud
- **Portal URL:** `/representative` (or click "My portal" in header)
- **Key Capabilities:** Filter ward complaints, officially escalate urgent delays to municipal heads, and post public development updates with before/after photos.

### 3. Citizen / Resident
- **Email:** `sayli@vit.edu`
- **Password:** `Sayli@12345`
- **Key Capabilities:** File complaints with GPS & photo, test AI duplicate prompts, support ("I face this too"), like, repost, comment, follow wards/issues, and verify resolved work with 1-5 star ratings.

---

## What Has Been Completed & Tested

### 1. Citizen & Social Experience
- **Issue Reporting with GPS & Photo**: Drop exact pin on Pune map or auto-detect GPS.
- **AI Duplicate Detection**: Compares geo-proximity (Haversine radius) and image similarity (CLIP embeddings / perceptual dHash). Alerts users with a 409 Conflict and prompts them to back the existing issue rather than create fragmented duplicates.
- **Instagram-Style Community Feed**: "I face this too" (Support), Like, Repost, and Discussion Comments.
- **Following Feed & Follows**: Citizens and representatives can follow specific issues, wards, or users with a dedicated `Follows` table and `feed=following` tab.
- **Anonymous Reporting & Privacy Protection**: Option to report anonymously (masks citizen name on public feeds) and image redaction helper.
- **Multilingual Support (i18n)**: One-click instant switching between English, Marathi (मराठी), and Hindi (हिंदी).
- **Official Citizen Receipt & WhatsApp Sharing**: Instant WhatsApp sharing link with prefilled context and printable citizen receipt (`SCC-PUNE-XXXXXX`) with audit stamps.

### 2. Resolution Workflow & Dedicated Verifications
- **Status Progression**: `reported` → `under_review` → `assigned` → `in_progress` → `resolved_awaiting_verification` → `verified_resolved`.
- **Proof of Work**: Municipal officers must upload an "after photo" to mark an issue as resolved.
- **AI Evidence Verification**: Checks if after photo is identical to before photo (fake fix), different location, or still showing the problem.
- **Dedicated Citizen Verifications Table**: Citizens rate the repair quality (1 to 5 stars), leave feedback notes, and verify site proximity. Rejection sends the complaint back to `in_progress`.

### 3. Municipal Operations Dashboard (`/admin`)
- **Actionable KPIs**: Total filed, open issues, unreviewed count, SLA compliance rate, and citizen satisfaction rating.
- **SLA Tracking & Auto-Escalation**: Category-based SLA timers (Water: 24h, Drainage: 48h, Garbage: 48h, Streetlight: 72h, Pothole: 7 days). One-click and automated scan flags overdue issues as `is_escalated`.
- **AI Municipal Assistant**: Auto-generates concise 2-sentence officer summaries, suggests responsible department, and flags category mismatches.
- **Abuse Moderation Queue**: Community-driven abuse reports (spam, harassment, fake reports) with admin actions to hide or delete content.
- **Ward Activity Leaderboard & Analytics**: Performance breakdown by ward and department.

### 4. Representative Portal (`/representative`)
- **Ward Overview**: Filter complaints by ward/constituency.
- **Official Escalation**: Flag urgent citizen issues directly to the municipal commissioner's office.
- **Development Updates**: Post verified before-and-after project updates on `/updates`.

---

## How to Run (One Single Command)

You do **not** need two terminals anymore. The frontend and backend are now unified into a single command:

```bash
cd /Users/sayli/.gemini/antigravity/scratch/smart-civic-connect
python3 run.py
# Or: ./start.sh
# Or: npm start
```
This builds the frontend, ensures the Pune database is seeded, and serves **both the React application and FastAPI backend on `http://localhost:8000`** with zero CORS and zero configuration. It will even open your default browser automatically.

If you are developing and prefer live hot-reloading for code changes:
```bash
python3 run.py --dev
```
*(Runs both Uvicorn and Vite together in one terminal, and shuts both down gracefully with `Ctrl+C`)*.

---

## Automated Tests & Verification

### Run End-to-End Test Suite
```bash
cd backend
PYTHONPATH=. /Users/sayli/venv/bin/pytest tests/test_civic.py
```
*Covers authentication, duplicate detection, follows, moderation, SLA escalation, 5-star citizen verification, and receipts.*

### Run Load Testing Harness
```bash
cd backend
/Users/sayli/venv/bin/python load_test.py --concurrency 25 --requests 150
```
*Simulates 25 concurrent workers executing hundreds of requests, outputting RPS and latency percentiles (P50, P90, P95, P99).*

### Run Frontend Build
```bash
cd frontend
npm run build
```
