import os
import sys
import json
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.main import app

def run_api_tests():
    print("=" * 60)
    print("TRINETRA FASTAPI ENDPOINTS TEST SUITE")
    print("=" * 60)

    client = TestClient(app)
    tests = []

    # 1. Health Firebase
    res = client.get("/health/firebase")
    tests.append(("GET /health/firebase", res.status_code == 200, res.json()))

    # 2. Health Database
    res = client.get("/health/database")
    data = res.json()
    tests.append(("GET /health/database", res.status_code == 200 and data.get("is_60_threats_validated"), f"Total threats: {data.get('total_threats')}"))

    # 3. Personalized Dashboard for Student
    res = client.get("/api/dashboard?community=STUDENT")
    dash = res.json()
    tests.append(("GET /api/dashboard (Student)", res.status_code == 200 and dash.get("total_relevant_threats", 0) >= 15, f"Student threats: {dash.get('total_relevant_threats')}"))

    # 4. Personalized Dashboard for Senior Citizen
    res = client.get("/api/dashboard?community=SENIOR_CITIZEN")
    dash = res.json()
    tests.append(("GET /api/dashboard (Senior)", res.status_code == 200 and dash.get("total_relevant_threats", 0) >= 15, f"Senior threats: {dash.get('total_relevant_threats')}"))

    # 5. Personalized Dashboard for Small Business
    res = client.get("/api/dashboard?community=SMALL_BUSINESS")
    dash = res.json()
    tests.append(("GET /api/dashboard (Business)", res.status_code == 200 and dash.get("total_relevant_threats", 0) >= 15, f"Business threats: {dash.get('total_relevant_threats')}"))

    # 6. Personalized Dashboard for Regional Community
    res = client.get("/api/dashboard?community=REGIONAL_COMMUNITY")
    dash = res.json()
    tests.append(("GET /api/dashboard (Regional)", res.status_code == 200 and dash.get("total_relevant_threats", 0) >= 15, f"Regional threats: {dash.get('total_relevant_threats')}"))

    # 7. List Threats & Search
    res = client.get("/api/threats?query=UPI")
    threats = res.json()
    tests.append(("GET /api/threats?query=UPI", res.status_code == 200 and threats.get("total", 0) > 0, f"Found {threats.get('total')} UPI threats"))

    # 8. Get Single Threat Details
    res_all = client.get("/api/threats")
    all_threats = res_all.json().get("threats", [])
    if all_threats:
        t_id = all_threats[0]["id"]
        res_single = client.get(f"/api/threats/{t_id}")
        t_detail = res_single.json()
        tests.append(("GET /api/threats/{id}", res_single.status_code == 200 and t_detail.get("title") != "", f"Fetched title: '{t_detail.get('title')}'"))

    # 9. AI Chat Assistant Endpoint
    res_chat = client.post("/api/chat", json={
        "message": "I got an internship message asking for ₹500 fee.",
        "community": "STUDENT"
    })
    chat_resp = res_chat.json()
    tests.append(("POST /api/chat", res_chat.status_code == 200 and len(chat_resp.get("ai_response", "")) > 10, "Generated AI safety advice"))

    # 10. Submit Incident Report
    res_rep = client.post("/api/reports", json={
        "community": "STUDENT",
        "threat_type": "Fake Internship Scam",
        "description": "Suspicious WhatsApp message asking for registration fee",
        "platform": "WhatsApp",
        "url_or_phone": "+91 9876543210"
    })
    tests.append(("POST /api/reports", res_rep.status_code == 200, f"Report ID: {res_rep.json().get('report', {}).get('id')}"))

    # 11. Submit Victim Experience Review
    res_rev = client.post("/api/reviews", json={
        "threat_id": "threat_fake_internship",
        "threat_title": "Fake Internship Scam",
        "user_alias": "Concerned Student",
        "community": "STUDENT",
        "experience_text": "I got a similar internship message last week asking for payment."
    })
    tests.append(("POST /api/reviews", res_rev.status_code == 200, f"Review ID: {res_rev.json().get('review', {}).get('id')}"))

    # 12. User Auth Sign Up & Sign In
    res_reg = client.post("/api/auth/register", json={
        "name": "Ananya Sharma",
        "email": "ananya_test@student.edu",
        "password": "Password123!",
        "community": "STUDENT",
        "region": "Delhi",
        "language": "English"
    })
    tests.append(("POST /api/auth/register", res_reg.status_code in [200, 400], "Registered student user profile"))

    res_login = client.post("/api/auth/login", json={
        "email": "ananya_test@student.edu",
        "password": "Password123!"
    })
    login_user = res_login.json().get("user", {})
    tests.append(("POST /api/auth/login", res_login.status_code == 200 and login_user.get("community") == "STUDENT", f"Logged in user community: {login_user.get('community')}"))

    # Print Summary
    all_passed = True
    for test_name, success, info in tests:
        status_str = "PASS" if success else "FAIL"
        if not success:
            all_passed = False
        print(f"[{status_str}] {test_name:<42} | {info}")

    print("=" * 60)
    print(f"API ENDPOINTS TEST RESULT: {'[SUCCESS] ALL API ENDPOINTS OPERATIONAL' if all_passed else '[FAIL] API ISSUES DETECTED'}")
    print("=" * 60)

    return all_passed

if __name__ == "__main__":
    run_api_tests()
