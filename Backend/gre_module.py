"""
gre_module.py — GRE Preparation using Groq AI.
"""
import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

from models import TestSession, TestType, get_sync_session

# --- Groq Setup ---
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY not found in .env")

client = Groq(api_key=api_key)

def ask_groq(prompt: str) -> str:
    """Send a prompt to Groq and return the text response."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content


class GREPrep:
    def __init__(self, user_id):
        self.user_id = user_id

    def generate_question(self, topic):
        """Generates a GRE question and returns a dict."""
        prompt = f"""
        You are a GRE Test Tutor. Generate a difficult {topic} question.
        Output STRICTLY in this JSON format (no markdown, no extra text):
        {{
            "question_text": "The actual question...",
            "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
            "correct_answer": "The correct option letter (A/B/C/D)",
            "explanation": "Why it is correct"
        }}
        """
        try:
            raw = ask_groq(prompt)
            clean = raw.replace('```json', '').replace('```', '').strip()
            return json.loads(clean)
        except Exception as e:
            return {"error": f"Failed to generate question: {str(e)}"}

    def grade_essay(self, essay_text):
        """Grades a GRE Analytical Writing essay."""
        prompt = f"""
        Grade this GRE Analytical Writing essay on a scale of 0.0 to 6.0.
        Provide feedback on grammar, structure, and vocabulary.
        Essay: "{essay_text}"
        Output STRICTLY in JSON (no markdown):
        {{
            "score": 4.5,
            "feedback": "Detailed feedback here..."
        }}
        """
        try:
            raw = ask_groq(prompt)
            clean = raw.replace('```json', '').replace('```', '').strip()
            return json.loads(clean)
        except Exception as e:
            return {"score": 0, "feedback": f"Error grading essay: {str(e)}"}

    def save_result(self, module, score, feedback):
        """Saves test result to DB with correct types."""
        session = get_sync_session()
        try:
            new_session = TestSession(
                user_id=self.user_id,
                test_type=TestType.GRE,
                module=module,
                score_obtained=float(score),
                feedback=str(feedback),
            )
            session.add(new_session)
            session.commit()
            print(f"✅ Result saved for GRE - {module}.")
        except Exception as e:
            session.rollback()
            print(f"❌ Error saving result: {e}")
        finally:
            session.close()
