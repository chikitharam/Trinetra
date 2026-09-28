import os
import json
import logging
import re
import time
import uuid
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("trinetra.ai_service")

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.genai_client = None
        self.legacy_model = None
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.preferred_models = [
            "gemini-flash-lite-latest",
            "gemini-3.6-flash",
            "gemini-3.8-flash",
            "gemini-3.5-flash",
            "gemini-flash-latest"
        ]

        if self.api_key:
            # 1. Try modern google.genai SDK
            try:
                from google import genai
                self.genai_client = genai.Client(api_key=self.api_key)
                logger.info("Gemini AI client (google.genai) initialized successfully.")
            except Exception as e1:
                logger.debug(f"google.genai SDK init skipped/failed: {e1}")
                # 2. Try legacy google.generativeai SDK
                try:
                    import google.generativeai as genai_legacy
                    genai_legacy.configure(api_key=self.api_key)
                    self.legacy_model = genai_legacy
                    logger.info("Gemini AI client (google.generativeai) initialized.")
                except Exception as e2:
                    logger.warning(f"Could not initialize Gemini AI SDK: {e2}")

    def clean_json_response(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def validate_threat_json(self, data: Dict[str, Any]) -> bool:
        required = ["title", "threat_type", "severity", "community", "description"]
        for field in required:
            if not data.get(field):
                return False
        if data.get("severity") not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            return False
        return True

    def simplify_threat_for_community(self, threat: Dict[str, Any], target_community: str) -> str:
        title = threat.get("title", "")
        desc = threat.get("description", "")
        comm = target_community.upper()

        if comm == "STUDENT":
            return f"Caution regarding '{title}': Scammers may send deceptive links or offers on messaging platforms targeting your college credentials, internships, or exam fees. {desc}"
        elif comm == "SENIOR_CITIZEN":
            return f"Important warning about '{title}': Fraudsters might call or message claiming to be bank or government officials asking for your OTP or PIN. Please do not share any codes or install remote applications. {desc}"
        elif comm == "SMALL_BUSINESS":
            return f"Cyber security alert for '{title}': Attackers are targeting company accounts and payment channels via fake invoices, executive impersonation, or malicious file attachments. {desc}"
        elif comm == "REGIONAL_COMMUNITY":
            return f"Regional warning about '{title}': Deceptive messages in local languages are offering fake government subsidies or electricity bill payments. {desc}"
        else:
            return desc

    def _get_system_instruction(self, community: str) -> str:
        comm_upper = (community or "STUDENT").upper()
        comm_labels = {
            "STUDENT": "Student",
            "SENIOR_CITIZEN": "Senior Citizen",
            "SMALL_BUSINESS": "Small Business",
            "REGIONAL_COMMUNITY": "Regional Community"
        }
        user_comm = comm_labels.get(comm_upper, "Student")

        return (
            f"You are TRINETRA AI Assistant, a helpful, friendly, and expert conversational AI assistant with a strong focus on cybersecurity awareness and cyber safety.\n\n"
            f"The current user's community is '{user_comm}'.\n\n"
            f"Core Directives:\n"
            f"1. Answer naturally and conversationally. You are a real chatbot that handles greetings, general questions, explanations, comparisons, and cybersecurity inquiries.\n"
            f"2. For cybersecurity questions, provide accurate, practical, and easy-to-understand guidance. Adapt examples to the user's community ('{user_comm}') when useful (e.g. fake internships/fees for Students, OTP/banking scams for Senior Citizens, invoice/vendor fraud for Small Businesses, or utility bill scams for Regional Communities).\n"
            f"3. Do NOT pretend that every user message is a cyber threat. If the user asks a normal general question (e.g. 'Hi', 'What can you do?', 'What is Python?', 'Tell me a joke'), answer it normally and conversationally.\n"
            f"4. If the user asks about a potentially dangerous or illegal activity, provide safe defensive guidance and educational context rather than actionable exploit steps.\n"
            f"5. Never invent fake facts, fake incidents, or fake sources. If you are uncertain, clearly say so.\n"
            f"6. Maintain conversation context from previous user messages in this chat session so follow-up questions (e.g. 'Why?', 'What should I check first?', 'Can you explain that in simple words?') make complete sense.\n"
            f"7. Do NOT use emoji characters in your text responses. Maintain a clean, readable tone with markdown formatting when appropriate.\n"
        )

    def _clean_text_response(self, text: str) -> str:
        if not text:
            return ""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U000025B6"
            "]+", flags=re.UNICODE
        )
        cleaned = emoji_pattern.sub("", text)
        return cleaned.strip()

    def generate_chat_response(
        self,
        message: str,
        community: str = "STUDENT",
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        comm_upper = (community or "STUDENT").upper()

        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        logger.info(f"[AI] Received chat request (cid: {conversation_id}, community: {comm_upper}): '{message}'")

        if not self.api_key:
            logger.error("[AI] GEMINI_API_KEY is not configured in environment.")
            return {
                "response": "Unable to get a response right now. Please try again.",
                "conversation_id": conversation_id
            }

        sys_instruction = self._get_system_instruction(comm_upper)

        if conversation_id not in self.sessions:
            self.sessions[conversation_id] = {
                "community": comm_upper,
                "history": [],
                "model_index": 0
            }

        session = self.sessions[conversation_id]

        # 1. Using modern google.genai SDK
        if self.genai_client:
            from google.genai import types

            raw_history = session.get("history", [])
            contents_history = [
                types.Content(
                    role=item["role"],
                    parts=[types.Part.from_text(text=item["parts"][0])]
                )
                for item in raw_history
            ]

            config = types.GenerateContentConfig(system_instruction=sys_instruction)

            start_idx = session.get("model_index", 0)
            num_models = len(self.preferred_models)

            for offset in range(num_models):
                model_idx = (start_idx + offset) % num_models
                model_name = self.preferred_models[model_idx]

                try:
                    chat_obj = self.genai_client.chats.create(
                        model=model_name,
                        config=config,
                        history=contents_history
                    )

                    for attempt in range(2):
                        try:
                            res = chat_obj.send_message(message)
                            if res and res.text:
                                cleaned_res = self._clean_text_response(res.text)
                                raw_history.append({"role": "user", "parts": [message]})
                                raw_history.append({"role": "model", "parts": [cleaned_res]})
                                session["history"] = raw_history
                                session["model_index"] = model_idx

                                return {
                                    "response": cleaned_res,
                                    "conversation_id": conversation_id
                                }
                        except Exception as se:
                            logger.warning(f"[AI] Model {model_name} send_message attempt {attempt + 1} failed: {se}")
                            time.sleep(1.0)
                except Exception as me:
                    logger.warning(f"[AI] Failed to create chat with model {model_name}: {me}")

        # 2. Using legacy google.generativeai SDK fallback
        elif self.legacy_model:
            try:
                model = self.legacy_model.GenerativeModel(
                    "gemini-1.5-flash",
                    system_instruction=sys_instruction
                )
                raw_history = session.get("history", [])
                chat_obj = model.start_chat(history=[])
                for item in raw_history:
                    if item["role"] == "user":
                        try:
                            chat_obj.send_message(item["parts"][0])
                        except Exception:
                            pass

                res = chat_obj.send_message(message)
                if res and res.text:
                    cleaned_res = self._clean_text_response(res.text)
                    raw_history.append({"role": "user", "parts": [message]})
                    raw_history.append({"role": "model", "parts": [cleaned_res]})
                    session["history"] = raw_history
                    return {
                        "response": cleaned_res,
                        "conversation_id": conversation_id
                    }
            except Exception as e:
                logger.error(f"[AI] Legacy model send error: {e}")

        # Final graceful error response
        return {
            "response": "Unable to get a response right now. Please try again.",
            "conversation_id": conversation_id
        }


