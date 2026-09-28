import logging
import feedparser
import datetime
from backend.services.firestore_service import FirestoreService
from backend.services.ai_service import AIService

logger = logging.getLogger("trinetra.rss_collector")

FEED_SOURCES = [
    {
        "name": "CERT-In Cyber Advisories",
        "url": "https://www.cert-in.org.in/s2cits?PAGEID=rss",
        "default_community": "REGIONAL_COMMUNITY"
    },
    {
        "name": "CISA Cyber News",
        "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
        "default_community": "SMALL_BUSINESS"
    },
    {
        "name": "NVD Vulnerability Feed",
        "url": "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss-analyzed.xml",
        "default_community": "SMALL_BUSINESS"
    }
]

class ThreatCollector:
    def __init__(self):
        self.db_service = FirestoreService()
        self.ai_service = AIService()

    def fetch_and_process_feeds(self) -> Dict[str, Any]:
        fetched_count = 0
        new_inserted = 0
        duplicates_skipped = 0

        existing_threats = self.db_service.get_all_threats()
        existing_hashes = set()
        for t in existing_threats:
            h = self.db_service.generate_threat_hash(t.get("title", ""), t.get("source_url", ""))
            existing_hashes.add(h)

        for source in FEED_SOURCES:
            try:
                feed = feedparser.parse(source["url"])
                entries = feed.entries[:5]  # Limit per feed for fast execution
                
                for entry in entries:
                    fetched_count += 1
                    title = entry.get("title", "Cyber Threat Alert")
                    link = entry.get("link", "")
                    summary = entry.get("summary", entry.get("description", ""))
                    published = entry.get("published", datetime.datetime.utcnow().isoformat())

                    t_hash = self.db_service.generate_threat_hash(title, link)
                    if t_hash in existing_hashes:
                        duplicates_skipped += 1
                        continue

                    # Determine target community by keyword heuristics
                    title_lower = title.lower() + " " + summary.lower()
                    comm = source["default_community"]
                    if any(k in title_lower for k in ["student", "exam", "internship", "campus", "scholarship", "game"]):
                        comm = "STUDENT"
                    elif any(k in title_lower for k in ["pension", "kyc", "otp", "bank call", "elderly"]):
                        comm = "SENIOR_CITIZEN"
                    elif any(k in title_lower for k in ["invoice", "vendor", "payroll", "ransomware", "business"]):
                        comm = "SMALL_BUSINESS"
                    elif any(k in title_lower for k in ["regional", "local", "utility", "bill", "festival"]):
                        comm = "REGIONAL_COMMUNITY"

                    threat_data = {
                        "title": title,
                        "description": summary or f"Cyber threat advisory from {source['name']}.",
                        "threat_type": "OSINT Threat Advisory",
                        "severity": "HIGH" if "critical" in title_lower or "severe" in title_lower else "MEDIUM",
                        "community": comm,
                        "target_communities": [{"community": comm, "relevance_score": 0.90}],
                        "attack_method": "Phishing / Social Engineering",
                        "platform": ["Web", "Email"],
                        "region": "National / Global",
                        "language": "English",
                        "keywords": [k.strip() for k in title.split() if len(k) > 4][:5],
                        "indicators": ["Suspicious communication", "Unverified domain"],
                        "how_to_identify": ["Check sender authenticity", "Verify official website"],
                        "what_to_do": ["Do not click links", "Report to security team"],
                        "prevention_tips": ["Enable Multi-Factor Authentication", "Keep software updated"],
                        "source": source["name"],
                        "source_url": link,
                        "published_date": published,
                        "status": "active",
                        "ai_processed": True
                    }

                    self.db_service.create_threat(threat_data)
                    existing_hashes.add(t_hash)
                    new_inserted += 1

            except Exception as e:
                logger.error(f"Error reading feed {source['name']}: {e}")

        return {
            "fetched_count": fetched_count,
            "new_inserted": new_inserted,
            "duplicates_skipped": duplicates_skipped
        }
