"""
api.py — FastAPI REST API with proper auth, chat history, and test history.
"""
import uuid
import os
import re
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Cookie
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import bcrypt
import jwt
from datetime import datetime, timedelta

from models import (User, TestSession, StudentProfile, University, Program,
                    ChatMessage, init_db, get_sync_session)
from gre_module import GREPrep
from ielts_module import IELTSPrep
from councelling_module import Counselor, UniversityRecommender, populate_dummy_data

app = FastAPI(title="Admission Architect API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = os.getenv("JWT_SECRET", "admission-architect-jwt-secret-2024")
JWT_EXPIRE_DAYS = 7

def make_token(user_id: str) -> str:
    payload = {"user_id": user_id, "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("user_id")
    except Exception:
        return None

@app.on_event("startup")
async def startup():
    await init_db()
    populate_dummy_data()
    print("✅ API ready.")

# ==============================================================
# AUTH
# ==============================================================

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

def validate_email(email: str) -> bool:
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

@app.post("/api/auth/signup")
def signup(data: SignupRequest):
    if len(data.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if not validate_email(data.email):
        raise HTTPException(status_code=400, detail="Invalid email address.")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    session = get_sync_session()
    try:
        if session.query(User).filter_by(username=data.username.strip()).first():
            raise HTTPException(status_code=400, detail="Username already taken.")
        if session.query(User).filter_by(email=data.email.lower()).first():
            raise HTTPException(status_code=400, detail="Email already registered.")

        hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
        token = str(uuid.uuid4())  # verification token
        user = User(
            id=str(uuid.uuid4()),
            username=data.username.strip(),
            email=data.email.lower(),
            password_hash=hashed,
            is_active=False,
            verification_token=token
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        return {"user_id": str(user.id), "email": user.email, "verification_token": token}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
@app.get("/api/auth/verify/{token}")
def verify_email(token: str):
    session = get_sync_session()
    try:
        user = session.query(User).filter_by(verification_token=token).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification link.")
        user.is_active = True
        user.verification_token = None
        session.commit()
        return {"success": True, "email": user.email}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
        
@app.post("/api/auth/login")
def login(data: LoginRequest):
    if not validate_email(data.email):
        raise HTTPException(status_code=400, detail="Invalid email address.")
    if not data.password:
        raise HTTPException(status_code=400, detail="Password is required.")

    session = get_sync_session()
    try:
        user = session.query(User).filter_by(email=data.email.lower()).first()
        if not user:
            raise HTTPException(status_code=401, detail="No account found with this email.")
        if not bcrypt.checkpw(data.password.encode(), user.password_hash.encode()):
            raise HTTPException(status_code=401, detail="Incorrect password.")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="EMAIL_NOT_VERIFIED")  # special code frontend catches

        token = make_token(str(user.id))
        return {"token": token, "user_id": str(user.id), "username": user.username, "email": user.email}
    except HTTPException:
        raise
    finally:
        session.close()

# ==============================================================
# PROFILE
# ==============================================================

class ProfileRequest(BaseModel):
    user_id: str
    cgpa: float
    major_interest: str
    budget_min: float
    budget_max: float
    preferred_country: str

@app.post("/api/profile/save")
def save_profile(data: ProfileRequest):
    session = get_sync_session()
    try:
        profile = session.query(StudentProfile).filter_by(user_id=data.user_id).first()
        if not profile:
            profile = StudentProfile(user_id=data.user_id)
            session.add(profile)
        profile.cgpa = data.cgpa
        profile.major_interest = data.major_interest
        profile.budget_min = data.budget_min
        profile.budget_max = data.budget_max
        profile.preferred_country = data.preferred_country
        session.commit()
        return {"success": True}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/profile/{user_id}")
def get_profile(user_id: str):
    session = get_sync_session()
    try:
        profile = session.query(StudentProfile).filter_by(user_id=user_id).first()
        if not profile:
            return {"exists": False}
        return {
            "exists": True,
            "cgpa": float(profile.cgpa or 0),
            "major_interest": profile.major_interest,
            "budget_min": float(profile.budget_min or 0),
            "budget_max": float(profile.budget_max or 0),
            "preferred_country": profile.preferred_country,
        }
    finally:
        session.close()

# ==============================================================
# UNIVERSITY RECOMMENDATIONS
# ==============================================================

class RecommendRequest(BaseModel):
    user_id: str

@app.post("/api/universities/recommend")
def recommend_universities(data: RecommendRequest):
    session = get_sync_session()
    try:
        profile = session.query(StudentProfile).filter_by(user_id=data.user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found. Please complete your profile first.")
        recommender = UniversityRecommender()
        recommender.load_and_train()
        results = recommender.recommend(profile)
        return {"recommendations": results}
    finally:
        session.close()

@app.get("/api/universities/all")
def get_all_universities():
    session = get_sync_session()
    try:
        unis = session.query(University).all()
        result = []
        for u in unis:
            programs = [{"course_name": p.course_name, "degree_level": p.degree_level,
                         "tuition_fee": float(p.tuition_fee) if p.tuition_fee else None,
                         "ielts_requirement": float(p.ielts_requirement) if p.ielts_requirement else None}
                        for p in (u.programs or [])]
            result.append({"id": str(u.id), "name": u.name, "location": u.location,
                           "global_ranking": u.global_ranking, "programs": programs})
        return {"universities": result}
    finally:
        session.close()

# ==============================================================
# GRE
# ==============================================================

class GREQuestionRequest(BaseModel):
    user_id: str
    topic: str

class GREAnswerRequest(BaseModel):
    user_id: str
    topic: str
    question_text: str
    user_answer: str
    correct_answer: str
    explanation: str

class GREEssayRequest(BaseModel):
    user_id: str
    essay_text: str

@app.post("/api/gre/question")
def gre_question(data: GREQuestionRequest):
    gre = GREPrep(data.user_id)
    result = gre.generate_question(data.topic)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/api/gre/submit-answer")
def gre_submit(data: GREAnswerRequest):
    gre = GREPrep(data.user_id)
    score = 1 if data.user_answer.upper() == data.correct_answer.upper() else 0
    gre.save_result(data.topic, score, data.explanation)
    return {"correct": score == 1, "score": score, "explanation": data.explanation}

@app.post("/api/gre/grade-essay")
def gre_essay(data: GREEssayRequest):
    gre = GREPrep(data.user_id)
    result = gre.grade_essay(data.essay_text)
    gre.save_result("Analytical Writing", result.get("score", 0), result.get("feedback", ""))
    return result

# ==============================================================
# IELTS
# ==============================================================

class IELTSRequest(BaseModel):
    user_id: str

class IELTSWritingRequest(BaseModel):
    user_id: str
    essay_text: str

class IELTSSpeakingRequest(BaseModel):
    user_id: str
    response_text: str

class IELTSScoreRequest(BaseModel):
    user_id: str
    module: str
    score: float
    feedback: str

@app.post("/api/ielts/reading")
def ielts_reading(data: IELTSRequest):
    return IELTSPrep(data.user_id).generate_reading()

@app.post("/api/ielts/listening")
def ielts_listening(data: IELTSRequest):
    from groq import Groq
    import json
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = """
    Write a short conversation between two university students discussing course registration.
    Provide 3 multiple-choice questions about specific details mentioned in the conversation.
    Output STRICTLY in JSON (no markdown):
    {
        "script": "Student A: ... Student B: ...",
        "questions": [
            {"q": "Question?", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "answer": "A"},
            {"q": "Question?", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "answer": "B"},
            {"q": "Question?", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "answer": "C"}
        ]
    }
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    clean = response.choices[0].message.content.replace('```json','').replace('```','').strip()
    return json.loads(clean)

@app.post("/api/ielts/grade-writing")
def ielts_writing(data: IELTSWritingRequest):
    from groq import Groq
    import json
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = f"""
    Grade this IELTS Writing Task 2 essay on band scale 0-9.
    Essay: "{data.essay_text}"
    Output STRICTLY in JSON (no markdown):
    {{"band": 6.5, "feedback": "...", "task_achievement": 6.5, "coherence": 7.0, "lexical_resource": 6.5, "grammar": 6.0}}
    """
    response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
    clean = response.choices[0].message.content.replace('```json','').replace('```','').strip()
    result = json.loads(clean)
    IELTSPrep(data.user_id).save_result("Writing", result.get("band", 0), result.get("feedback", ""))
    return result

@app.post("/api/ielts/grade-speaking")
def ielts_speaking(data: IELTSSpeakingRequest):
    from groq import Groq
    import json
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = f"""
    Grade this IELTS Speaking response on band scale 0-9.
    Topic: "Describe a memorable journey you have taken."
    Response: "{data.response_text}"
    Output STRICTLY in JSON (no markdown):
    {{"band": 6.5, "feedback": "..."}}
    """
    response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
    clean = response.choices[0].message.content.replace('```json','').replace('```','').strip()
    result = json.loads(clean)
    IELTSPrep(data.user_id).save_result("Speaking", result.get("band", 0), result.get("feedback", ""))
    return result

@app.post("/api/ielts/save-score")
def ielts_save(data: IELTSScoreRequest):
    IELTSPrep(data.user_id).save_result(data.module, data.score, data.feedback)
    return {"success": True}

# ==============================================================
# AI CHAT — with persistent history per user
# ==============================================================

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/api/chat")
def chat(data: ChatRequest):
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    session = get_sync_session()

    try:
        # Load last 20 messages from DB for this user
        past = session.query(ChatMessage)\
            .filter_by(user_id=data.user_id)\
            .order_by(ChatMessage.timestamp.asc())\
            .limit(20).all()

        system_prompt = """You are an expert study abroad consultant for The Admission Architect.
        Help students with: university applications, IELTS/GRE prep, UK visa requirements,
        scholarships, and study abroad planning. Be concise, friendly, and helpful. Max 150 words."""

        messages = [{"role": "system", "content": system_prompt}]
        for msg in past:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": data.message})

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=200,
        )
        reply = response.choices[0].message.content

        # Save both messages to DB
        session.add(ChatMessage(user_id=data.user_id, role="user", content=data.message))
        session.add(ChatMessage(user_id=data.user_id, role="assistant", content=reply))
        session.commit()

        return {"reply": reply}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/chat/history/{user_id}")
def get_chat_history(user_id: str):
    session = get_sync_session()
    try:
        messages = session.query(ChatMessage)\
            .filter_by(user_id=user_id)\
            .order_by(ChatMessage.timestamp.asc()).all()
        return {"history": [{"role": m.role, "content": m.content,
                             "timestamp": m.timestamp.strftime("%Y-%m-%d %H:%M") if m.timestamp else ""}
                            for m in messages]}
    finally:
        session.close()

# ==============================================================
# PROGRESS / HISTORY
# ==============================================================

@app.get("/api/progress/{user_id}")
def get_progress(user_id: str):
    session = get_sync_session()
    try:
        results = session.query(TestSession).filter_by(user_id=user_id)\
            .order_by(TestSession.timestamp.desc()).all()
        return {"history": [{"test_type": r.test_type.value if r.test_type else "N/A",
                              "module": r.module or "", "score": float(r.score_obtained) if r.score_obtained else 0,
                              "feedback": r.feedback or "",
                              "date": r.timestamp.strftime("%Y-%m-%d") if r.timestamp else ""}
                             for r in results]}
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
