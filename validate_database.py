import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.config.firebase import get_firebase_status, is_firebase_live
from backend.services.firestore_service import FirestoreService
from backend.services.personalization import PersonalizationEngine

def run_validation():
    print("=" * 60)
    print("TRINETRA DATABASE & SYSTEM VALIDATION SUITE")
    print("=" * 60)

    db_service = FirestoreService()
    engine = PersonalizationEngine(db_service)
    
    test_results = []

    # TEST 1: Firebase Initialization
    try:
        status = get_firebase_status()
        test_results.append(("TEST 1: Firebase Initialization", True, status["mode"]))
    except Exception as e:
        test_results.append(("TEST 1: Firebase Initialization", False, str(e)))

    # TEST 2: Firestore Connection
    try:
        db = db_service.db
        test_results.append(("TEST 2: Firestore Access", True, "Connected & Operational"))
    except Exception as e:
        test_results.append(("TEST 2: Firestore Access", False, str(e)))

    # TEST 3: Read Threats
    try:
        threats = db_service.get_all_threats()
        test_results.append(("TEST 3: Read Threats Collection", True, f"Found {len(threats)} total threats"))
    except Exception as e:
        test_results.append(("TEST 3: Read Threats Collection", False, str(e)))

    # TEST 4: Read Users
    try:
        users = db_service.db.collection("users").stream()
        user_list = [u.to_dict() for u in users if hasattr(u, "to_dict") and u.to_dict()]
        test_results.append(("TEST 4: Read Users Collection", True, f"Found {len(user_list)} registered users"))
    except Exception as e:
        test_results.append(("TEST 4: Read Users Collection", False, str(e)))

    # TEST 5: Community Filtering
    try:
        st_threats = db_service.get_threats_by_community("STUDENT")
        sn_threats = db_service.get_threats_by_community("SENIOR_CITIZEN")
        sb_threats = db_service.get_threats_by_community("SMALL_BUSINESS")
        rg_threats = db_service.get_threats_by_community("REGIONAL_COMMUNITY")
        msg = f"Student:{len(st_threats)}, Senior:{len(sn_threats)}, Business:{len(sb_threats)}, Regional:{len(rg_threats)}"
        test_results.append(("TEST 5: Community Filtering Engine", True, msg))
    except Exception as e:
        test_results.append(("TEST 5: Community Filtering Engine", False, str(e)))

    # TEST 6: Dashboard Retrieval
    try:
        dash = engine.get_personalized_dashboard(community_override="STUDENT")
        test_results.append(("TEST 6: Dashboard Personalized Retrieval", True, f"Retrieved {dash['total_relevant_threats']} relevant threats for Student"))
    except Exception as e:
        test_results.append(("TEST 6: Dashboard Personalized Retrieval", False, str(e)))

    # TEST 7: Threat Details Retrieval
    try:
        all_t = db_service.get_all_threats()
        if all_t:
            sample_id = all_t[0]["id"]
            single_t = db_service.get_threat(sample_id)
            pass_single = single_t is not None and single_t.get("title") != ""
            test_results.append(("TEST 7: Threat Details Document Fetch", pass_single, f"Fetched threat: '{single_t.get('title')}'"))
        else:
            test_results.append(("TEST 7: Threat Details Document Fetch", False, "No threats found to test"))
    except Exception as e:
        test_results.append(("TEST 7: Threat Details Document Fetch", False, str(e)))

    # TEST 8: 60-Threat Validation
    try:
        stats = db_service.get_database_stats()
        valid = stats["is_60_threats_validated"]
        details = (f"Student: {stats['student_threats']}/15, "
                   f"Senior: {stats['senior_citizen_threats']}/15, "
                   f"Business: {stats['small_business_threats']}/15, "
                   f"Regional: {stats['regional_community_threats']}/15, "
                   f"Total: {stats['total_threats']}/60")
        test_results.append(("TEST 8: 60-Threat Mandatory Dataset Criteria", valid, details))
    except Exception as e:
        test_results.append(("TEST 8: 60-Threat Mandatory Dataset Criteria", False, str(e)))

    # TEST 9: Duplicate Detection
    try:
        h1 = db_service.generate_threat_hash("Fake Internship Scam", "https://cybercrime.gov.in")
        h2 = db_service.generate_threat_hash("Fake Internship Scam", "https://cybercrime.gov.in")
        test_results.append(("TEST 9: Hash-based Duplicate Prevention", h1 == h2, f"Hash generated: {h1}"))
    except Exception as e:
        test_results.append(("TEST 9: Hash-based Duplicate Prevention", False, str(e)))

    # TEST 10: Authentication / Database Association
    try:
        test_user = {
            "name": "Validation Test User",
            "email": "test_validation@trinetra.org",
            "community": "SENIOR_CITIZEN",
            "region": "National",
            "language": "English"
        }
        created = db_service.create_user(test_user)
        test_results.append(("TEST 10: User Auth & Firestore Profile Link", created["id"] != "", f"User ID: {created['id']} ({created['community']})"))
    except Exception as e:
        test_results.append(("TEST 10: User Auth & Firestore Profile Link", False, str(e)))

    # Print Report
    all_passed = True
    for test_name, success, info in test_results:
        status_str = "PASS" if success else "FAIL"
        if not success:
            all_passed = False
        print(f"[{status_str}] {test_name:<42} | {info}")

    print("=" * 60)
    print(f"OVERALL SYSTEM VALIDATION RESULT: {'[SUCCESS] ALL CRITERIA MET' if all_passed else '[FAIL] ISSUES DETECTED'}")
    print("=" * 60)

    return all_passed

if __name__ == "__main__":
    run_validation()
