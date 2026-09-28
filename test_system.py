import sys
import os
import time
import urllib.request
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

BASE = "http://127.0.0.1:8001"

def test_endpoint(name, url, method="GET", body=None, headers=None):
    print(f"\n--- Testing {name} ({method} {url}) ---")
    req = urllib.request.Request(url, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if body:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")
    else:
        data = None

    try:
        with urllib.request.urlopen(req, data=data) as resp:
            status = resp.status
            res_headers = dict(resp.headers)
            res_body = json.loads(resp.read().decode("utf-8"))
            print(f"Status: {status}")
            print(f"CORS Allow-Origin: {res_headers.get('access-control-allow-origin')}")
            print(f"Response Summary: {str(res_body)[:150]}...")
            return True, res_body
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code}: {err_body}")
        return False, err_body
    except Exception as e:
        print(f"Error: {e}")
        return False, str(e)

if __name__ == "__main__":
    print("=== TRINETRA SYSTEM INTEGRATION TEST ===")
    
    # 1. Health DB
    test_endpoint("Database Health", f"{BASE}/health/database")
    
    # 2. CORS Preflight / Request from 127.0.0.1:5500
    test_endpoint("Dashboard (STUDENT)", f"{BASE}/api/dashboard?community=STUDENT", headers={"Origin": "http://127.0.0.1:5500"})
    
    # 3. Threat Search
    test_endpoint("Threat Matrix Search ('internship')", f"{BASE}/api/threats?query=internship&community=STUDENT", headers={"Origin": "http://127.0.0.1:5500"})
    
    # 4. Report Incident
    report_payload = {
        "user_id": "test_student_123",
        "community": "STUDENT",
        "threat_type": "Fake Internship Scam",
        "description": "Test report: Received suspicious internship message asking for ₹500 fee.",
        "platform": "WhatsApp",
        "url_or_phone": "+91 9876543210"
    }
    test_endpoint("Submit Report", f"{BASE}/api/reports", method="POST", body=report_payload, headers={"Origin": "http://127.0.0.1:5500"})
    
    # 5. Share Experience
    review_payload = {
        "threat_id": "threat_test",
        "threat_title": "Fake Internship Scam",
        "user_alias": "Aware Student",
        "community": "STUDENT",
        "experience_text": "I got an offer asking for money. Verified on TRINETRA and blocked sender.",
        "platform": "WhatsApp",
        "action_taken": "Blocked & Reported"
    }
    test_endpoint("Submit Experience", f"{BASE}/api/reviews", method="POST", body=review_payload, headers={"Origin": "http://127.0.0.1:5500"})
    
    # 6. AI Test 1: "hi"
    test_endpoint("AI Chat (hi)", f"{BASE}/api/chat", method="POST", body={"message": "hi", "community": "STUDENT"}, headers={"Origin": "http://127.0.0.1:5500"})
    
    # 7. AI Test 2: Internship scam prompt
    test_endpoint("AI Chat (internship ₹500)", f"{BASE}/api/chat", method="POST", body={"message": "I got an internship offer asking for ₹500 fee.", "community": "STUDENT"}, headers={"Origin": "http://127.0.0.1:5500"})

    # 8. AI Test 3: OTP scam prompt
    test_endpoint("AI Chat (OTP scam)", f"{BASE}/api/chat", method="POST", body={"message": "My bank called and asked for my OTP.", "community": "SENIOR_CITIZEN"}, headers={"Origin": "http://127.0.0.1:5500"})

    # 9. AI Test 4: Business payment prompt
    test_endpoint("AI Chat (Invoice scam)", f"{BASE}/api/chat", method="POST", body={"message": "I received an email asking me to change our company bank account.", "community": "SMALL_BUSINESS"}, headers={"Origin": "http://127.0.0.1:5500"})
