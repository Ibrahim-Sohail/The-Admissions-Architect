"""
import_universities.py — Imports university data from Excel into the database.
Run once:  py -3.14 import_universities.py

Excel columns used:
  University Name, City, University Rank (Approx), Level, Course Name,
  Estimated Tuition Fee (£ per year), IELTS Requirement,
  Scholarship Available (Yes/No), Visa Type
"""
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from models import University, Program, Scholarship, get_sync_session


EXCEL_FILE = "UK_Undergraduate_Masters_With_Visa_Admission_Architect.xlsx"


def import_from_excel():
    df = pd.read_excel(EXCEL_FILE)
    session = get_sync_session()

    try:
        # --- Step 1: Clear existing data ---
        print("Clearing existing university data...")
        session.query(Scholarship).delete()
        session.query(Program).delete()
        session.query(University).delete()
        session.commit()
        print("✅ Cleared.")

        # --- Step 2: Insert unique universities ---
        print("Importing universities...")
        unique_unis = df[['University Name', 'City', 'University Rank (Approx)']].drop_duplicates()

        uni_map = {}  # name → University object
        for _, row in unique_unis.iterrows():
            uni = University(
                name=str(row['University Name']).strip(),
                location=f"{str(row['City']).strip()}, UK",
                global_ranking=int(row['University Rank (Approx)']) if pd.notna(row['University Rank (Approx)']) else None,
            )
            session.add(uni)
            session.flush()  # get ID assigned
            uni_map[uni.name] = uni

        print(f"✅ Inserted {len(uni_map)} universities.")

        # --- Step 3: Insert programs ---
        print("Importing programs...")
        programs_added = 0
        scholarships_added = 0

        for _, row in df.iterrows():
            uni_name = str(row['University Name']).strip()
            uni = uni_map.get(uni_name)
            if not uni:
                continue

            # Parse tuition fee
            try:
                tuition = float(str(row['Estimated Tuition Fee (£ per year)']).replace('£','').replace(',','').strip())
            except Exception:
                tuition = None

            # Parse IELTS requirement
            try:
                ielts = float(row['IELTS Requirement']) if pd.notna(row['IELTS Requirement']) else None
            except Exception:
                ielts = None

            # Degree level
            level = str(row['Level']).strip() if pd.notna(row['Level']) else None

            # Visa sponsorship — all rows have "UK Student Visa (Tier 4)"
            visa_type = str(row.get('Visa Type', '')).strip()
            has_visa = 'visa' in visa_type.lower()

            program = Program(
                university_id=uni.id,
                course_name=str(row['Course Name']).strip(),
                degree_level=level,
                tuition_fee=tuition,
                ielts_requirement=ielts,
                visa_sponsorship=has_visa,
            )
            session.add(program)
            programs_added += 1

            # Add scholarship if available
            scholarship_available = str(row.get('Scholarship Available (Yes/No)', 'No')).strip().lower()
            if scholarship_available == 'yes':
                scholarship = Scholarship(
                    university_id=uni.id,
                    name=f"{uni_name} International Scholarship",
                    is_full_tuition=False,
                    eligibility_criteria="Open to international students. Merit-based.",
                )
                session.add(scholarship)
                scholarships_added += 1

        session.commit()
        print(f"✅ Inserted {programs_added} programs.")
        print(f"✅ Inserted {scholarships_added} scholarships.")

        # --- Step 4: Summary ---
        print("\n📊 Database Summary:")
        unis = session.query(University).all()
        for u in unis:
            prog_count = len(u.programs)
            print(f"  {u.name} (Rank #{u.global_ranking}) — {prog_count} programs")

        print(f"\n✅ Import complete! {len(unis)} universities, {programs_added} programs loaded.")

    except Exception as e:
        session.rollback()
        print(f"❌ Error during import: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    import_from_excel()
