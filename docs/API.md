# API reference

Generated from the code by `backend/gen_docs.py`. Interactive docs: `/docs` on the running backend.

`*` marks a required field. Authenticated calls send `Authorization: Bearer <token>`. Errors return `{"detail": "message"}`; `409` on `POST /complaints` returns similar-complaint suggestions.

## Auth

| Method | Path | Access | Inputs | Notes |
|---|---|---|---|---|
| POST | `/auth/register` | Public | json: name*, email*, password*, role, ward, phone | Create an account. Representatives start unverified. Returns a JWT and the user. |
| POST | `/auth/login` | Public | json: email*, password* | Returns a JWT (valid 7 days) and the user. |
| GET | `/auth/me` | Login required | none | The logged-in user. |

## Complaints

| Method | Path | Access | Inputs | Notes |
|---|---|---|---|---|
| GET | `/categories` | Public | none | Valid complaint categories. |
| POST | `/ai/classify` | Login required | form: image* | Suggest a category from the photo. available=false when the AI model is not installed. |
| POST | `/ai/redact` | Login required | form: image* | Privacy feature: blurs faces, vehicle plates, or sensitive regions for anonymous reporting. |
| POST | `/complaints/check-duplicates` | Login required | form: latitude*, longitude*, category*, image | Suggest similar nearby complaints before filing (GPS plus photo similarity). |
| POST | `/complaints` | Login required | form: title*, description*, category*, latitude*, longitude*, address, ward, is_anonymous, force, image | File a complaint with optional photo. Returns 409 with suggestions if similar ones exist; resend with force=true to file anyway. |
| GET | `/complaints` | Optional login | query/path: feed, lat, lng, radius_km, category, status, ward, limit, offset | Feed. feed = all, nearby (needs lat, lng, radius_km), trending (by community support), or mine. Filters: category, status, ward. |
| GET | `/complaints/{cid}` | Optional login | query/path: cid* | One complaint with counts, the caller's own interactions and full status history. |
| GET | `/complaints/{cid}/receipt` | Public | query/path: cid* | Generate official printable citizen receipt & tracking record with audit trail. |
| POST | `/complaints/{cid}/support` | Login required | query/path: cid* | Toggle support (I face this too). Returns the updated complaint. |
| POST | `/complaints/{cid}/like` | Login required | query/path: cid* | Toggle like. |
| POST | `/complaints/{cid}/repost` | Login required | query/path: cid* | Toggle repost. |
| POST | `/complaints/{cid}/follow` | Login required | query/path: cid* |  |
| POST | `/wards/{ward}/follow` | Login required | query/path: ward* |  |
| GET | `/me/follows` | Login required | none |  |
| GET | `/complaints/{cid}/comments` | Public | query/path: cid* | Comments, oldest first, with author role and verified badge. |
| POST | `/complaints/{cid}/comments` | Login required | query/path: cid*<br>json: body* | Add a comment. Notifies the reporter. |
| POST | `/complaints/{cid}/report-abuse` | Login required | query/path: cid*<br>json: target_type*, target_id*, reason*, details |  |
| POST | `/comments/{comment_id}/report-abuse` | Login required | query/path: comment_id*<br>json: target_type*, target_id*, reason*, details |  |
| POST | `/complaints/{cid}/verify` | Login required | query/path: cid*<br>json: accepted*, rating, note, latitude, longitude | Dedicated Citizen Verification with GPS Proximity & Satisfaction Rating. |
| GET | `/notifications` | Login required | none | The caller's latest 50 notifications. |
| POST | `/notifications/read` | Login required | none | Mark all notifications read. |

## Admin

| Method | Path | Access | Inputs | Notes |
|---|---|---|---|---|
| GET | `/admin/departments` | Role: admin/representative | none | Municipal departments. |
| PATCH | `/admin/complaints/{cid}/status` | Role: admin | query/path: cid*<br>form: status*, note, department_id, after_image | Move a complaint to the next valid status. Assigning needs department_id; resolving needs an after photo. Notifies reporter and supporters. |
| POST | `/admin/auto-escalate` | Role: admin | none | Scans all open complaints for SLA breaches, auto-escalates them and alerts ward reps. |
| GET | `/admin/moderation` | Role: admin | none | Returns reported content queue for municipal admin moderation. |
| POST | `/admin/moderation/{report_id}/action` | Role: admin | query/path: report_id*<br>json: action*, note |  |
| GET | `/admin/analytics` | Role: admin | none | Totals by status and category, plus average resolution time in hours. |
| GET | `/admin/representatives/pending` | Role: admin | none | Representatives awaiting verification. |
| POST | `/admin/representatives/{uid}/verify` | Role: admin | query/path: uid* | Verify a representative after checking credentials. |
| GET | `/admin/complaints/{cid}/insights` | Role: admin | query/path: cid* | AI assist for officers: summary, suggested department, category check, evidence warning. |

## Representatives

| Method | Path | Access | Inputs | Notes |
|---|---|---|---|---|
| GET | `/updates` | Public | query/path: ward, limit | Public development updates, newest first. Optional ward filter. |
| POST | `/updates` | Verified representative | form: title*, body*, ward, before_image, after_image | Publish a development update with optional before and after photos. |
| DELETE | `/updates/{uid}` | Verified representative | query/path: uid* | Delete one of your own updates. |
| POST | `/complaints/{cid}/escalate` | Verified representative | query/path: cid*<br>json: note* | Representatives cannot change official status; they flag the issue for the municipal office. |

## Other

| Method | Path | Access | Inputs | Notes |
|---|---|---|---|---|
| GET | `/health` | Public | none | Liveness check. |
