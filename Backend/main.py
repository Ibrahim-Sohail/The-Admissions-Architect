"""
main.py — CLI Entry Point for the AI Education Platform.
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from models import User, TestSession, init_db_sync as init_db, get_sync_session
from gre_module import GREPrep
from ielts_module import IELTSPrep
from councelling_module import Counselor, UniversityRecommender, populate_dummy_data


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def get_or_create_user():
    """Simple username-based login / registration."""
    clear_screen()
    print("=" * 40)
    print("   🎓  AI EDUCATION PLATFORM  🎓")
    print("=" * 40)
    username = input("\nEnter your username to login/register: ").strip()

    session = get_sync_session()
    try:
        user = session.query(User).filter_by(username=username).first()

        if not user:
            print(f"User '{username}' not found. Creating new account...")
            user = User(
                username=username,
                email=f"{username}@example.com",
                password_hash="placeholder_hash"  # TODO: add real hashing
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print("✅ Account created!")
        else:
            print(f"👋 Welcome back, {user.username}!")

        # Detach from session so we can use user.id outside
        user_id = user.id
        user_username = user.username
        return user_id, user_username
    finally:
        session.close()


def get_user_profile(user_id):
    """Fetch user profile fresh from DB."""
    from models import StudentProfile
    session = get_sync_session()
    try:
        return session.query(StudentProfile).filter_by(user_id=user_id).first()
    finally:
        session.close()


def show_history(user_id):
    """View past test results."""
    print("\n--- 📜 Your Test History ---")
    session = get_sync_session()
    try:
        results = session.query(TestSession).filter_by(user_id=user_id).all()
        if not results:
            print("No tests taken yet.")
        else:
            print(f"{'TEST':<10} | {'MODULE':<20} | {'SCORE':<10} | {'DATE'}")
            print("-" * 55)
            for r in results:
                test_name = r.test_type.value if r.test_type else "N/A"
                date_str = r.timestamp.date() if r.timestamp else "N/A"
                print(f"{test_name:<10} | {str(r.module):<20} | {str(r.score_obtained):<10} | {date_str}")
    finally:
        session.close()
    input("\nPress Enter to return...")


def main_menu():
    # 1. Initialize DB schema (safe to run multiple times)
    print("Initializing database...")
    init_db()

    # 2. Populate dummy university data if needed
    populate_dummy_data()

    # 3. Login
    user_id, username = get_or_create_user()

    # 4. Instantiate modules
    gre_tool = GREPrep(user_id)
    ielts_tool = IELTSPrep(user_id)
    counselor = Counselor(user_id)
    recommender = UniversityRecommender()

    while True:
        clear_screen()
        print(f"\n🎓 Dashboard  |  User: {username}")
        print("-" * 35)
        print("1. 🏛️   University Counseling & Recommendations")
        print("2. 📘  GRE Preparation")
        print("3. 🎧  IELTS Preparation")
        print("4. 📜  View My Progress")
        print("5. 🚪  Exit")

        choice = input("\nSelect an option (1-5): ").strip()

        if choice == '1':
            print("\nLoading Recommender...")
            recommender.load_and_train()

            # FIX: Always fetch profile fresh from DB
            profile = get_user_profile(user_id)

            if not profile:
                print("⚠️  No profile found. Let's build it now.")
                profile = counselor.build_profile()

            if profile:
                recommender.recommend(profile)

            if input("\nUpdate profile? (y/n): ").lower() == 'y':
                counselor.build_profile()
                # Fetch updated profile fresh from DB
                profile = get_user_profile(user_id)
                if profile:
                    recommender.recommend(profile)

            input("\nPress Enter to return...")

        elif choice == '2':
            while True:
                print("\n--- 📘 GRE MENU ---")
                g_choice = input("1. Verbal\n2. Quantitative\n3. Analytical Writing\n4. Back\nSelect: ").strip()

                if g_choice == '1':
                    data = gre_tool.generate_question("Verbal Reasoning")
                    if "error" in data:
                        print(data["error"])
                        continue
                    print(f"\nQ: {data['question_text']}")
                    for opt in data['options']:
                        print(opt)
                    ans = input("\nYour Answer (A/B/C/D): ").upper().strip()
                    score = 1 if ans == data['correct_answer'] else 0
                    print(f"{'✅ Correct!' if score else '❌ Wrong.'}")
                    print(f"Explanation: {data['explanation']}")
                    gre_tool.save_result("Verbal Reasoning", score, data['explanation'])

                elif g_choice == '2':
                    data = gre_tool.generate_question("Quantitative Reasoning")
                    if "error" in data:
                        print(data["error"])
                        continue
                    print(f"\nQ: {data['question_text']}")
                    for opt in data['options']:
                        print(opt)
                    ans = input("\nYour Answer (A/B/C/D): ").upper().strip()
                    score = 1 if ans == data['correct_answer'] else 0
                    print(f"{'✅ Correct!' if score else '❌ Wrong.'}")
                    print(f"Explanation: {data['explanation']}")
                    gre_tool.save_result("Quantitative Reasoning", score, data['explanation'])

                elif g_choice == '3':
                    print("\nPrompt: 'Technology is making us less human.'")
                    essay = input("Write your essay: ").strip()
                    print("Grading...")
                    res = gre_tool.grade_essay(essay)
                    print(f"Score: {res['score']}/6.0")
                    print(f"Feedback: {res['feedback']}")
                    gre_tool.save_result("Analytical Writing", res['score'], res['feedback'])

                elif g_choice == '4':
                    break

        elif choice == '3':
            while True:
                print("\n--- 🎧 IELTS MENU ---")
                i_choice = input("1. Reading\n2. Listening\n3. Speaking\n4. Back\nSelect: ").strip()

                if i_choice == '1':
                    data = ielts_tool.generate_reading()
                    print(f"\n📄 Passage:\n{data['passage']}\n")
                    score = 0
                    for i, q in enumerate(data.get('questions', []), 1):
                        print(f"Q{i}: {q['q']}")
                        for opt in q.get('options', []):
                            print(f"  {opt}")
                        ans = input("Your answer (A/B/C): ").upper().strip()
                        if ans == q['answer'].upper():
                            print("✅ Correct!")
                            score += 1
                        else:
                            print(f"❌ Wrong. Answer: {q['answer']}")
                    ielts_tool.save_result("Reading", score, f"Scored {score}/{len(data.get('questions', []))}")

                elif i_choice == '2':
                    ielts_tool.practice_listening()

                elif i_choice == '3':
                    ielts_tool.practice_speaking()

                elif i_choice == '4':
                    break

        elif choice == '4':
            show_history(user_id)

        elif choice == '5':
            print("Goodbye! 👋")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
