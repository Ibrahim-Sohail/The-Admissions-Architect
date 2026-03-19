"""
ielts_module.py — IELTS Preparation using Groq AI (Randomized).
"""
import os
import json
import random
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

from database.models import TestSession, TestType
from database.connection import get_sync_session

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY not found in .env")

client = Groq(api_key=api_key)

def ask_groq(prompt: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    return response.choices[0].message.content

class IELTSPrep:
    def __init__(self, user_id):
        self.user_id = user_id

    def generate_reading(self):
        # ✅ Random IELTS Reading topics
        topics = ['Ocean Life', 'Space Exploration', 'Ancient Egyptian Architecture', 'The History of the Internet', 'Climate Change Effects', 'Human Psychology', 'Renewable Energy Innovations', 'The Evolution of Languages']
        topic = random.choice(topics)

        prompt = f"""
        Generate a completely unique, short (150 words) IELTS Academic Reading passage about '{topic}'.
        Then provide 3 multiple-choice questions based on it.
        Output STRICTLY in JSON (no markdown):
        {{
            "passage": "Text...",
            "questions": [
                {{"q": "Question 1?", "options": ["A) ...", "B) ...", "C) ..."], "answer": "A"}},
                {{"q": "Question 2?", "options": ["A) ...", "B) ...", "C) ..."], "answer": "B"}},
                {{"q": "Question 3?", "options": ["A) ...", "B) ...", "C) ..."], "answer": "C"}}
            ]
        }}
        """
        try:
            raw = ask_groq(prompt)
            clean = raw.replace('```json', '').replace('```', '').strip()
            return json.loads(clean)
        except Exception as e:
            print(f"Error generating reading: {e}")
            return {"passage": "Error generating passage.", "questions": []}

    def save_result(self, module, score, feedback):
        session = get_sync_session()
        try:
            new_session = TestSession(
                user_id=self.user_id,
                test_type=TestType.IELTS,
                module=module,
                score_obtained=float(score),
                feedback=str(feedback),
            )
            session.add(new_session)
            session.commit()
            print(f"✅ Result saved for IELTS - {module}.")
        except Exception as e:
            session.rollback()
            print(f"❌ Error saving result: {e}")
        finally:
            session.close()