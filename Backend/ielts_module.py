"""
ielts_module.py — IELTS Preparation using Groq AI.
"""
import os
import json
import time
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


class IELTSPrep:
    def __init__(self, user_id):
        self.user_id = user_id

    def generate_reading(self):
        """Generates a reading passage and questions."""
        print("\n--- Generating Reading Section ---")
        prompt = """
        Generate a short (150 words) IELTS Academic Reading passage about 'Ocean Life'.
        Then provide 3 multiple-choice questions based on it.
        Output STRICTLY in JSON (no markdown):
        {
            "passage": "Text...",
            "questions": [
                {"q": "Question 1?", "options": ["A) ...", "B) ...", "C) ..."], "answer": "A"},
                {"q": "Question 2?", "options": ["A) ...", "B) ...", "C) ..."], "answer": "B"},
                {"q": "Question 3?", "options": ["A) ...", "B) ...", "C) ..."], "answer": "C"}
            ]
        }
        """
        try:
            raw = ask_groq(prompt)
            clean = raw.replace('```json', '').replace('```', '').strip()
            return json.loads(clean)
        except Exception as e:
            print(f"Error generating reading: {e}")
            return {"passage": "Error generating passage.", "questions": []}

    def practice_listening(self):
        """Generates a dialogue and asks a question (audio via gTTS)."""
        print("\n--- Listening Section ---")
        prompt = """
        Write a short conversation between two students discussing a library book.
        Provide 1 question about a specific detail (like a date or title).
        Output STRICTLY in JSON (no markdown):
        {
            "script": "Student A: Hi... Student B: Hello...",
            "question": "When is the book due?",
            "answer": "Monday"
        }
        """
        try:
            raw = ask_groq(prompt)
            clean = raw.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean)

            # Try to play audio if gtts is available
            try:
                from gtts import gTTS
                print("Generating audio...")
                tts = gTTS(text=data['script'], lang='en', slow=False)
                audio_file = "ielts_listening_test.mp3"
                tts.save(audio_file)
                print(f"Audio saved to: {audio_file}")
                if os.name == 'nt':
                    os.startfile(audio_file)
                elif os.name == 'posix':
                    os.system(f"open '{audio_file}' 2>/dev/null || xdg-open '{audio_file}' 2>/dev/null")
            except Exception as audio_err:
                print(f"(Audio unavailable: {audio_err})")
                print(f"\n[Script]\n{data['script']}")

            print(f"\nQuestion: {data['question']}")
            user_ans = input("Your Answer: ").strip()

            correct = data['answer'].lower() in user_ans.lower()
            score = 8.0 if correct else 4.0
            print(f"Result: {'✅ Correct' if correct else '❌ Incorrect'} — Answer was: {data['answer']}")
            self.save_result("Listening", score, f"Q: {data['question']} | Correct: {data['answer']}")

        except Exception as e:
            print(f"Error in listening module: {e}")

    def practice_speaking(self):
        """Text-based speaking practice (no microphone required)."""
        print("\n--- Speaking Section ---")
        topic = "Describe a memorable journey you have taken."
        print(f"Topic: {topic}")
        print("You have a moment to think...")
        time.sleep(2)

        user_text = input("\nType your response here: ").strip()
        print("Grading...")

        grading_prompt = f"""
        Grade this IELTS Speaking response on a scale of 0-9.
        Topic: {topic}
        Response: "{user_text}"
        Output STRICTLY in JSON (no markdown):
        {{ "band": 6.5, "feedback": "Grammar good, fluency needs work." }}
        """
        try:
            raw = ask_groq(grading_prompt)
            clean = raw.replace('```json', '').replace('```', '').strip()
            result = json.loads(clean)
            print(f"Band Score: {result['band']}/9.0")
            print(f"Feedback: {result['feedback']}")
            self.save_result("Speaking", result['band'], result['feedback'])
        except Exception as e:
            print(f"Error grading speaking: {e}")

    def save_result(self, module, score, feedback):
        """Saves IELTS result to DB with correct types."""
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
