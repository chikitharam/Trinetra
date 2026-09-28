import datetime
import hashlib
import logging
from typing import List, Dict, Any, Optional
from backend.config.firebase import get_db

logger = logging.getLogger("trinetra.firestore_service")

class FirestoreService:
    def __init__(self):
        self.db = get_db()

    # --- USER OPERATIONS ---
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        email = user_data.get("email", "").lower().strip()
        user_id = user_data.get("id") or f"user_{hashlib.md5(email.encode()).hexdigest()[:12]}"
        
        doc_ref = self.db.collection("users").document(user_id)
        now = datetime.datetime.utcnow().isoformat()
        
        user_obj = {
            "id": user_id,
            "name": user_data.get("name", "Cyber Citizen"),
            "email": email,
            "community": user_data.get("community", "STUDENT").upper(),
            "region": user_data.get("region", "All Regions"),
            "language": user_data.get("language", "English"),
            "notification_preference": user_data.get("notification_preference", True),
            "created_at": user_data.get("created_at") or now,
            "updated_at": now
        }
        
        doc_ref.set(user_obj)
        logger.info(f"User created/updated: {user_id} ({user_obj['community']})")
        return user_obj

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.collection("users").document(user_id).get()
        if hasattr(doc, "to_dict") and doc.to_dict():
            return doc.to_dict()
        return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        email_clean = email.lower().strip()
        docs = self.db.collection("users").where("email", "==", email_clean).stream()
        for doc in docs:
            data = doc.to_dict() if hasattr(doc, "to_dict") else None
            if data:
                return data
        return None

    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        doc_ref = self.db.collection("users").document(user_id)
        existing = self.get_user(user_id)
        if not existing:
            return None
        
        update_data["updated_at"] = datetime.datetime.utcnow().isoformat()
        doc_ref.set(update_data, merge=True)
        return self.get_user(user_id)

    # --- THREAT OPERATIONS ---
    def generate_threat_hash(self, title: str, source_url: str = "") -> str:
        clean_title = (title or "").lower().strip()
        clean_url = (source_url or "").lower().strip()
        return hashlib.sha256(f"{clean_title}:{clean_url}".encode()).hexdigest()[:16]

    def create_threat(self, threat_data: Dict[str, Any]) -> Dict[str, Any]:
        title = threat_data.get("title", "Untitled Cyber Threat")
        source_url = threat_data.get("source_url", "")
        
        threat_id = threat_data.get("id") or f"threat_{self.generate_threat_hash(title, source_url)}"
        now = datetime.datetime.utcnow().isoformat()

        # Format target communities
        target_comm = threat_data.get("target_communities", [])
        if not target_comm and threat_data.get("community"):
            target_comm = [{"community": threat_data["community"], "relevance_score": 0.95}]

        threat_obj = {
            "id": threat_id,
            "title": title,
            "description": threat_data.get("description", ""),
            "threat_type": threat_data.get("threat_type", "Cyber Scam"),
            "severity": (threat_data.get("severity") or "HIGH").upper(),
            "community": (threat_data.get("community") or "STUDENT").upper(),
            "target_communities": target_comm,
            "attack_method": threat_data.get("attack_method", "Social Engineering / Phishing"),
            "platform": threat_data.get("platform") if isinstance(threat_data.get("platform"), list) else [threat_data.get("platform", "Web")],
            "region": threat_data.get("region", "National / All Regions"),
            "language": threat_data.get("language", "English"),
            "keywords": threat_data.get("keywords", []),
            "indicators": threat_data.get("indicators", []),
            "how_to_identify": threat_data.get("how_to_identify", []),
            "what_to_do": threat_data.get("what_to_do", []),
            "prevention_tips": threat_data.get("prevention_tips", []),
            "source": threat_data.get("source", "TRINETRA OSINT Intelligence"),
            "source_url": source_url or "https://cybercrime.gov.in",
            "published_date": threat_data.get("published_date") or now,
            "last_updated": threat_data.get("last_updated") or now,
            "status": threat_data.get("status", "active"),
            "ai_processed": threat_data.get("ai_processed", True)
        }

        doc_ref = self.db.collection("threats").document(threat_id)
        doc_ref.set(threat_obj)
        return threat_obj

    def get_threat(self, threat_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.collection("threats").document(threat_id).get()
        if hasattr(doc, "to_dict") and doc.to_dict():
            return doc.to_dict()
        return None

    def get_all_threats(self) -> List[Dict[str, Any]]:
        docs = self.db.collection("threats").stream()
        results = []
        for doc in docs:
            data = doc.to_dict() if hasattr(doc, "to_dict") else None
            if data:
                results.append(data)
        return results

    def get_threats_by_community(self, community: str) -> List[Dict[str, Any]]:
        comm_upper = community.upper()
        all_threats = self.get_all_threats()
        
        matching = []
        for t in all_threats:
            # Check main community field
            if t.get("community") == comm_upper:
                matching.append(t)
                continue
            # Check target_communities array
            targets = t.get("target_communities", [])
            for tc in targets:
                if isinstance(tc, dict) and tc.get("community") == comm_upper:
                    matching.append(t)
                    break
                elif isinstance(tc, str) and tc.upper() == comm_upper:
                    matching.append(t)
                    break
        return matching

    def search_threats(
        self,
        query: str = "",
        community: Optional[str] = None,
        severity: Optional[str] = None,
        threat_type: Optional[str] = None,
        platform: Optional[str] = None,
        region: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        threats = self.get_all_threats()
        q_clean = (query or "").lower().strip()

        filtered = []
        for t in threats:
            # Community filter
            if community and community.upper() != "ALL":
                comm_upper = community.upper()
                main_match = t.get("community") == comm_upper
                target_match = any(
                    (tc.get("community") == comm_upper if isinstance(tc, dict) else str(tc).upper() == comm_upper)
                    for tc in t.get("target_communities", [])
                )
                if not (main_match or target_match):
                    continue

            # Severity filter
            if severity and severity.upper() != "ALL":
                if t.get("severity", "").upper() != severity.upper():
                    continue

            # Threat type filter
            if threat_type and threat_type.upper() != "ALL":
                if threat_type.lower() not in t.get("threat_type", "").lower():
                    continue

            # Platform filter
            if platform and platform.upper() != "ALL":
                platforms = [p.lower() for p in t.get("platform", [])]
                if not any(platform.lower() in p for p in platforms):
                    continue

            # Region filter
            if region and region.upper() != "ALL":
                if region.lower() not in t.get("region", "").lower():
                    continue

            # Query text matching across title, description, keywords, attack_method, etc.
            if q_clean:
                title_match = q_clean in t.get("title", "").lower()
                desc_match = q_clean in t.get("description", "").lower()
                attack_match = q_clean in t.get("attack_method", "").lower()
                type_match = q_clean in t.get("threat_type", "").lower()
                kw_match = any(q_clean in str(k).lower() for k in t.get("keywords", []))
                ind_match = any(q_clean in str(i).lower() for i in t.get("indicators", []))
                
                if not (title_match or desc_match or attack_match or type_match or kw_match or ind_match):
                    continue

            filtered.append(t)

        return filtered

    # --- REPORT OPERATIONS ---
    def create_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        import uuid
        report_id = f"report_{uuid.uuid4().hex[:10]}"
        now = datetime.datetime.utcnow().isoformat()

        report_obj = {
            "id": report_id,
            "user_id": report_data.get("user_id", "anonymous_user"),
            "community": (report_data.get("community") or "STUDENT").upper(),
            "threat_type": report_data.get("threat_type", "Cyber Incident"),
            "description": report_data.get("description", ""),
            "platform": report_data.get("platform", "WhatsApp"),
            "url_or_phone": report_data.get("url_or_phone", ""),
            "region": report_data.get("region", "All Regions"),
            "timestamp": now,
            "status": "pending"
        }
        
        self.db.collection("reports").document(report_id).set(report_obj)
        return report_obj

    def get_reports(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        docs = self.db.collection("reports").stream()
        results = []
        for doc in docs:
            data = doc.to_dict() if hasattr(doc, "to_dict") else None
            if data:
                if user_id and data.get("user_id") != user_id:
                    continue
                results.append(data)
        # Sort newest first
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results

    # --- REVIEW / EXPERIENCE OPERATIONS ---
    def create_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        import uuid
        review_id = f"rev_{uuid.uuid4().hex[:10]}"
        now = datetime.datetime.utcnow().isoformat()

        review_obj = {
            "id": review_id,
            "threat_id": review_data.get("threat_id", ""),
            "threat_title": review_data.get("threat_title", "General Threat"),
            "user_alias": review_data.get("user_alias", "Community Member"),
            "community": (review_data.get("community") or "STUDENT").upper(),
            "experience_text": review_data.get("experience_text", ""),
            "platform": review_data.get("platform", "WhatsApp"),
            "action_taken": review_data.get("action_taken", "Reported & Blocked"),
            "timestamp": now
        }
        
        self.db.collection("reviews").document(review_id).set(review_obj)
        return review_obj

    def get_reviews(self, threat_id: Optional[str] = None, community: Optional[str] = None) -> List[Dict[str, Any]]:
        docs = self.db.collection("reviews").stream()
        results = []
        for doc in docs:
            data = doc.to_dict() if hasattr(doc, "to_dict") else None
            if data:
                if threat_id and data.get("threat_id") != threat_id:
                    continue
                if community and community.upper() != "ALL" and data.get("community") != community.upper():
                    continue
                results.append(data)
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results

    # --- ALERT OPERATIONS ---
    def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        import uuid
        alert_id = f"alert_{uuid.uuid4().hex[:10]}"
        now = datetime.datetime.utcnow().isoformat()

        alert_obj = {
            "id": alert_id,
            "user_id": alert_data.get("user_id", "all"),
            "community": (alert_data.get("community") or "STUDENT").upper(),
            "threat_id": alert_data.get("threat_id", ""),
            "title": alert_data.get("title", "New High-Priority Cyber Alert"),
            "message": alert_data.get("message", ""),
            "severity": (alert_data.get("severity") or "HIGH").upper(),
            "timestamp": now,
            "is_read": False
        }

        self.db.collection("alerts").document(alert_id).set(alert_obj)
        return alert_obj

    def get_user_alerts(self, user_id: Optional[str] = None, community: Optional[str] = None) -> List[Dict[str, Any]]:
        docs = self.db.collection("alerts").stream()
        results = []
        for doc in docs:
            data = doc.to_dict() if hasattr(doc, "to_dict") else None
            if data:
                if community and community.upper() != "ALL":
                    comm_match = data.get("community") == community.upper() or data.get("community") == "ALL"
                    if not comm_match:
                        continue
                results.append(data)
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results

    def mark_alert_read(self, alert_id: str) -> bool:
        doc_ref = self.db.collection("alerts").document(alert_id)
        doc = doc_ref.get()
        if hasattr(doc, "to_dict") and doc.to_dict():
            doc_ref.set({"is_read": True}, merge=True)
            return True
        return False

    # --- DATABASE HEALTH / VALIDATION STATS ---
    def get_database_stats(self) -> Dict[str, Any]:
        all_threats = self.get_all_threats()
        
        student_count = 0
        senior_count = 0
        business_count = 0
        regional_count = 0
        
        severity_dist = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for t in all_threats:
            comm = (t.get("community") or "").upper()
            sev = (t.get("severity") or "HIGH").upper()
            
            if sev in severity_dist:
                severity_dist[sev] += 1
            else:
                severity_dist["HIGH"] += 1

            # Count communities
            target_comms = [
                (tc.get("community") if isinstance(tc, dict) else str(tc)).upper()
                for tc in t.get("target_communities", [])
            ]
            if not target_comms and comm:
                target_comms = [comm]

            if "STUDENT" in target_comms or comm == "STUDENT":
                student_count += 1
            if "SENIOR_CITIZEN" in target_comms or comm == "SENIOR_CITIZEN":
                senior_count += 1
            if "SMALL_BUSINESS" in target_comms or comm == "SMALL_BUSINESS":
                business_count += 1
            if "REGIONAL_COMMUNITY" in target_comms or comm == "REGIONAL_COMMUNITY":
                regional_count += 1

        users_count = len(self.db.collection("users").stream())
        reports_count = len(self.db.collection("reports").stream())
        reviews_count = len(self.db.collection("reviews").stream())
        alerts_count = len(self.db.collection("alerts").stream())

        is_valid = (
            student_count >= 15 and
            senior_count >= 15 and
            business_count >= 15 and
            regional_count >= 15 and
            len(all_threats) >= 60
        )

        return {
            "total_threats": len(all_threats),
            "student_threats": student_count,
            "student_valid": student_count >= 15,
            "senior_citizen_threats": senior_count,
            "senior_citizen_valid": senior_count >= 15,
            "small_business_threats": business_count,
            "small_business_valid": business_count >= 15,
            "regional_community_threats": regional_count,
            "regional_community_valid": regional_count >= 15,
            "is_60_threats_validated": is_valid,
            "severity_distribution": severity_dist,
            "total_users": users_count,
            "total_reports": reports_count,
            "total_reviews": reviews_count,
            "total_alerts": alerts_count
        }
