import io, os
import pytest
from PIL import Image
from fastapi.testclient import TestClient

# Use isolated sqlite DB for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_suite.db"
os.environ["AI_ENABLED"] = "off"
from app.main import app

def make_test_img(color="blue"):
    b = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(b, "PNG")
    return b.getvalue()

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
    if os.path.exists("test_suite.db"):
        os.remove("test_suite.db")

def test_full_civic_platform_flow(client):
    H = lambda t: {"Authorization": f"Bearer {t}"}
    
    # 1. Register Citizen and Representative
    r_cit = client.post("/auth/register", json={
        "name": "Sayli Praghane",
        "email": "sayli@vit.edu",
        "phone": "+919307060293",
        "password": "Password123!",
        "role": "citizen",
        "ward": "Kothrud"
    })
    assert r_cit.status_code == 201
    cit_token = r_cit.json()["token"]
    cit_id = r_cit.json()["user"]["id"]

    r_rep = client.post("/auth/register", json={
        "name": "Nagarsevak Patil",
        "email": "patil@ward.gov.in",
        "phone": "+919800000000",
        "password": "Password123!",
        "role": "representative",
        "ward": "Kothrud"
    })
    assert r_rep.status_code == 201
    rep_token = r_rep.json()["token"]
    rep_id = r_rep.json()["user"]["id"]

    # Admin login
    r_adm = client.post("/auth/login", json={"email": "admin@civic.local", "password": "Admin@12345"})
    assert r_adm.status_code == 200
    adm_token = r_adm.json()["token"]

    # Admin verifies representative
    v_rep = client.post(f"/admin/representatives/{rep_id}/verify", headers=H(adm_token))
    assert v_rep.status_code == 200

    # 2. File a civic complaint
    report_data = {
        "title": "Severe Pothole near School Gate",
        "description": "Deep dangerous pothole on Paud Road outside school causing bike accidents.",
        "category": "pothole",
        "latitude": "18.5074",
        "longitude": "73.8077",
        "address": "Paud Road, near Bharati Vidya Bhavan School",
        "ward": "Kothrud",
        "is_anonymous": "false"
    }
    r_comp = client.post("/complaints", data=report_data, files={"image": ("pothole.png", make_test_img("gray"), "image/png")}, headers=H(cit_token))
    assert r_comp.status_code == 201
    comp = r_comp.json()
    cid = comp["id"]
    assert comp["ward"] == "Kothrud"
    assert comp["counts"]["supports"] == 0
    assert comp["sla_hours_remaining"] > 0

    # 3. Duplicate detection test
    dup_res = client.post("/complaints", data=report_data, files={"image": ("pothole2.png", make_test_img("gray"), "image/png")}, headers=H(cit_token))
    assert dup_res.status_code == 409
    assert len(dup_res.json()["suggestions"]) > 0

    # 4. Social interactions: Support, Like, Repost, Comment
    sup_res = client.post(f"/complaints/{cid}/support", headers=H(cit_token))
    assert sup_res.status_code == 200
    assert sup_res.json()["me"]["supported"] is True

    like_res = client.post(f"/complaints/{cid}/like", headers=H(cit_token))
    assert like_res.status_code == 200
    assert like_res.json()["me"]["liked"] is True

    comm_res = client.post(f"/complaints/{cid}/comments", json={"body": "Buses and autos swerve dangerously here."}, headers=H(cit_token))
    assert comm_res.status_code == 201
    
    comments = client.get(f"/complaints/{cid}/comments").json()
    assert len(comments) == 1
    assert comments[0]["body"] == "Buses and autos swerve dangerously here."

    # 5. Follows & Following Feed test
    # Author already auto-follows their own complaint upon filing
    assert comp["me"]["followed"] is True

    # Following the ward
    w_res = client.post("/wards/Kothrud/follow", headers=H(cit_token))
    assert w_res.json()["following"] is True

    # Test "following" feed (shows the complaint because author follows it and its ward)
    following_feed = client.get("/complaints?feed=following", headers=H(cit_token)).json()
    assert len(following_feed) >= 1
    assert any(x["id"] == cid for x in following_feed)

    # Test unfollow and re-follow toggle
    f_unfollow = client.post(f"/complaints/{cid}/follow", headers=H(cit_token))
    assert f_unfollow.json()["following"] is False
    f_refollow = client.post(f"/complaints/{cid}/follow", headers=H(cit_token))
    assert f_refollow.json()["following"] is True

    # 6. Abuse Reporting & Moderation Queue test
    rep_abuse = client.post(f"/complaints/{cid}/report-abuse", json={
        "target_type": "complaint",
        "target_id": cid,
        "reason": "spam",
        "details": "Testing moderation flagging"
    }, headers=H(cit_token))
    assert rep_abuse.status_code == 201

    mod_queue = client.get("/admin/moderation", headers=H(adm_token)).json()
    assert len(mod_queue) >= 1
    report_entry = next(r for r in mod_queue if r["target_id"] == cid)
    assert report_entry["reason"] == "spam"

    # Admin dismisses report as valid civic post
    act_res = client.post(f"/admin/moderation/{report_entry['id']}/action", json={"action": "dismiss"}, headers=H(adm_token))
    assert act_res.status_code == 200

    # 7. Municipal Workflow (under_review -> assigned -> in_progress -> resolved_awaiting_verification)
    deps = client.get("/admin/departments", headers=H(adm_token)).json()
    dept_id = str(deps[0]["id"])
    
    assert client.patch(f"/admin/complaints/{cid}/status", data={"status": "under_review", "note": "Inspecting site"}, headers=H(adm_token)).status_code == 200
    assert client.patch(f"/admin/complaints/{cid}/status", data={"status": "assigned", "department_id": dept_id, "note": "Assigned road crew"}, headers=H(adm_token)).status_code == 200
    assert client.patch(f"/admin/complaints/{cid}/status", data={"status": "in_progress", "note": "Asphalt patch in progress"}, headers=H(adm_token)).status_code == 200

    # Upload after photo to resolve awaiting verification
    res_await = client.patch(f"/admin/complaints/{cid}/status", data={"status": "resolved_awaiting_verification", "note": "Pothole filled and leveled"},
                             files={"after_image": ("after.png", make_test_img("white"), "image/png")}, headers=H(adm_token))
    assert res_await.status_code == 200
    assert res_await.json()["status"] == "resolved_awaiting_verification"

    # 8. Dedicated Citizen Verification with 5-star rating & GPS proximity
    v_body = {
        "accepted": True,
        "rating": 5,
        "note": "Smooth asphalt now. Thank you PMC!",
        "latitude": 18.5075,
        "longitude": 73.8076
    }
    verif_res = client.post(f"/complaints/{cid}/verify", json=v_body, headers=H(cit_token))
    assert verif_res.status_code == 200
    assert verif_res.json()["status"] == "verified_resolved"

    # Detail check: verifications audit records
    detail_res = client.get(f"/complaints/{cid}", headers=H(cit_token)).json()
    assert len(detail_res["verifications_list"]) == 1
    assert detail_res["verifications_list"][0]["rating"] == 5
    assert detail_res["verifications_list"][0]["photo_distance_m"] is not None

    # 9. Printable Citizen Receipt with unique tracking ID
    receipt = client.get(f"/complaints/{cid}/receipt").json()
    assert receipt["tracking_reference"].startswith("SCC-PUNE-")
    assert receipt["status"] == "verified_resolved"
    assert len(receipt["timeline"]) >= 4

    # 10. AI Officer Insights & Summary
    insights = client.get(f"/admin/complaints/{cid}/insights", headers=H(adm_token)).json()
    assert "summary" in insights
    assert len(insights["summary"]["text"]) > 10

    # 11. Public Analytics & SLA Compliance
    analytics = client.get("/admin/analytics", headers=H(adm_token)).json()
    assert analytics["total"] >= 1
    assert "by_ward" in analytics
    assert analytics["citizen_satisfaction"] >= 4.0
