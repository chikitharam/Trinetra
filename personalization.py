import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("trinetra.personalization")

SEVERITY_WEIGHTS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1
}

COMMUNITY_SAFETY_TIPS = {
    "STUDENT": {
        "title": "Protect your academic and financial credentials",
        "tip": "Never pay upfront fees for 'guaranteed' internships, scholarships, or exam papers. Verify all recruiting companies on official job portals."
    },
    "SENIOR_CITIZEN": {
        "title": "Keep your OTP and Banking PIN private",
        "tip": "No official bank, pension department, or electricity board will ever call to ask for your OTP, UPI PIN, or remote app installation."
    },
    "SMALL_BUSINESS": {
        "title": "Enforce strict financial authentication workflows",
        "tip": "Always verify invoice bank details via phone call to a trusted offline contact before processing payments or wire transfers."
    },
    "REGIONAL_COMMUNITY": {
        "title": "Verify local government schemes before sharing details",
        "tip": "Do not open suspicious links sent in regional WhatsApp groups offering free recharges, laptops, or subsidies."
    }
}

class PersonalizationEngine:
    def __init__(self, firestore_service):
        self.db_service = firestore_service

    def calculate_relevance(self, threat: Dict[str, Any], user_community: str, user_region: str = "", user_lang: str = "") -> float:
        user_comm_upper = (user_community or "STUDENT").upper()
        base_score = 0.5

        main_comm = (threat.get("community") or "").upper()
        if main_comm == user_comm_upper:
            base_score = 0.95
        else:
            for tc in threat.get("target_communities", []):
                tc_name = (tc.get("community") if isinstance(tc, dict) else str(tc)).upper()
                if tc_name == user_comm_upper:
                    rel = tc.get("relevance_score", 0.85) if isinstance(tc, dict) else 0.85
                    base_score = max(base_score, rel)
                    break

        # Regional & Language boost
        if user_region and threat.get("region") and user_region.lower() in threat.get("region", "").lower():
            base_score = min(1.0, base_score + 0.05)
        if user_lang and threat.get("language") and user_lang.lower() in threat.get("language", "").lower():
            base_score = min(1.0, base_score + 0.05)

        return round(base_score, 2)

    def get_personalized_dashboard(self, user_id: Optional[str] = None, community_override: Optional[str] = None) -> Dict[str, Any]:
        user_community = "STUDENT"
        user_region = "All Regions"
        user_lang = "English"
        user_name = "Cyber Citizen"

        if user_id:
            user = self.db_service.get_user(user_id)
            if user:
                user_community = user.get("community", "STUDENT")
                user_region = user.get("region", "All Regions")
                user_lang = user.get("language", "English")
                user_name = user.get("name", "Cyber Citizen")

        if community_override:
            user_community = community_override.upper()

        # Fetch matching threats
        threats = self.db_service.get_threats_by_community(user_community)
        
        # If community returns fewer than expected, fallback to all threats filtered
        if not threats:
            all_threats = self.db_service.get_all_threats()
            threats = [
                t for t in all_threats
                if (t.get("community") or "").upper() == user_community or
                any((tc.get("community") if isinstance(tc, dict) else str(tc)).upper() == user_community for tc in t.get("target_communities", []))
            ]

        # Score & Enrich threats
        enriched_threats = []
        for t in threats:
            t_copy = t.copy()
            relevance = self.calculate_relevance(t_copy, user_community, user_region, user_lang)
            t_copy["relevance_score"] = relevance
            enriched_threats.append(t_copy)

        # Sort: Severity desc, Relevance desc, Last updated desc
        def sort_key(t):
            sev = (t.get("severity") or "HIGH").upper()
            sev_weight = SEVERITY_WEIGHTS.get(sev, 2)
            rel = t.get("relevance_score", 0.5)
            date = t.get("last_updated") or t.get("published_date") or ""
            return (sev_weight, rel, date)

        enriched_threats.sort(key=sort_key, reverse=True)

        # High priority vs recent
        high_priority = [t for t in enriched_threats if t.get("severity") in ["CRITICAL", "HIGH"]]
        recent = sorted(enriched_threats, key=lambda x: x.get("published_date") or "", reverse=True)[:5]

        # Safety Tip
        safety_tip = COMMUNITY_SAFETY_TIPS.get(
            user_community,
            {
                "title": "Stay Vigilant Against Cyber Fraud",
                "tip": "Always verify unexpected calls, links, and payment requests through official channels."
            }
        )

        # Dynamic Severity Breakdown for user community
        sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for t in enriched_threats:
            s = (t.get("severity") or "HIGH").upper()
            if s in sev_counts:
                sev_counts[s] += 1

        return {
            "user_name": user_name,
            "community": user_community,
            "total_relevant_threats": len(enriched_threats),
            "high_priority_count": len(high_priority),
            "severity_counts": sev_counts,
            "safety_tip": safety_tip,
            "high_priority": high_priority,
            "recent": recent,
            "threats": enriched_threats
        }
