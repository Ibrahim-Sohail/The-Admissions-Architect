"""
councelling_module.py — AI University Recommender Engine (CSV Powered & Bulletproof)
"""
import os
import csv
import random
import glob
from database.models import University, Program
from database.connection import get_sync_session

def populate_dummy_data():
    session = get_sync_session()
    try:
        # 🚨 THE FIX: Force wipe the database to clear out the old cached dummy data!
        print("🧹 FORCING DATABASE WIPE TO LOAD FRESH CSV...")
        session.query(Program).delete()
        session.query(University).delete()
        session.commit()

        print("📚 Checking for CSV database...")
        current_dir = os.path.dirname(__file__)
        csv_files = glob.glob(os.path.join(current_dir, "*.csv"))
        
        csv_path = None
        if csv_files:
            # Prioritize the uploaded UK file
            for f in csv_files:
                if "Admission" in f or "UK" in f or "universities" in f:
                    csv_path = f
                    break
            if not csv_path:
                csv_path = csv_files[0]

        if not csv_path or not os.path.exists(csv_path):
            print("⚠️ No CSV found! Please ensure your CSV file is inside the 'Backend' folder.")
            return

        print(f"📖 Loading real data from {os.path.basename(csv_path)}...")
        
        created_unis = {}
        rows = []
        
        # Safely try multiple encodings to handle Microsoft Excel's formatting
        for enc in ['utf-8', 'cp1252', 'latin-1']:
            try:
                with open(csv_path, mode='r', encoding=enc) as file:
                    reader = csv.DictReader(file)
                    rows = list(reader) 
                break 
            except UnicodeDecodeError:
                continue
        
        for row in rows:
            uni_name = row.get('University Name', '').strip()
            if not uni_name: continue
            
            # 1. Create University
            if uni_name not in created_unis:
                rank_str = row.get('University Rank (Approx)', '').strip()
                try: rank = int(rank_str)
                except ValueError: rank = 999
                
                uni = University(
                    name=uni_name,
                    location=row.get('City', '').strip() + ", UK", 
                    global_ranking=rank
                )
                session.add(uni)
                session.flush()
                created_unis[uni_name] = uni.id
            
            # 2. Process Program
            fee_key = next((k for k in row.keys() if k and 'Estimated Tuition Fee' in k), None)
            fee_str = row.get(fee_key, '') if fee_key else ''
            fee_str = fee_str.replace(',', '').replace('£', '').strip()
            
            try: fee_in_gbp = float(fee_str)
            except ValueError: fee_in_gbp = 20000.0
            
            fee_in_usd = fee_in_gbp * 1.25 
            
            pct_str = row.get('Min Percentage Equivalent', '').strip()
            try: pct = float(pct_str)
            except ValueError: pct = 70.0
            cgpa_proxy = pct * 0.04  
            
            course_name = row.get('Course Name', '').strip()

            prog = Program(
                university_id=created_unis[uni_name],
                course_name=course_name,
                degree_level=row.get('Level', '').strip(),
                tuition_fee=fee_in_usd,
                ielts_requirement=cgpa_proxy 
            )
            session.add(prog)

        session.commit()
        print("✅ Real University Database Loaded from CSV successfully!")
    except Exception as e:
        session.rollback()
        print(f"❌ Error populating data from CSV: {e}")
    finally:
        session.close()

class UniversityRecommender:
    def load_and_train(self):
        pass

    def recommend(self, profile):
        session = get_sync_session()
        try:
            query = session.query(University).join(Program)
            
            # Filter: Country
            if profile.preferred_country and profile.preferred_country != "Any":
                query = query.filter(University.location.ilike(f"%{profile.preferred_country}%"))
                
            # Filter: Major
            major_query = profile.major_interest.strip().lower() if profile.major_interest else ""
            if major_query:
                query = query.filter(Program.course_name.ilike(f"%{major_query}%"))
                
            # Filter: Budget (with 15% flexibility buffer)
            if profile.budget_max:
                buffered_budget = profile.budget_max * 1.15
                query = query.filter(Program.tuition_fee <= buffered_budget)

            unis = query.all()
            results = []
            
            for uni in unis:
                # Safely grab the matching program
                if major_query:
                    matching_progs = [p for p in uni.programs if major_query in p.course_name.lower()]
                else:
                    matching_progs = uni.programs

                if not matching_progs:
                    continue 
                    
                prog = matching_progs[0]
                req_cgpa = prog.ielts_requirement or 3.0 
                
                # Academic Filter: Exclude if student is more than 0.4 below the cutoff
                if profile.cgpa and profile.cgpa < (req_cgpa - 0.4):
                    continue 
                    
                # 🚨 THE MATH FIX: CGPA Match is now King. Rank is just a tie-breaker.
                # We multiply the CGPA gap by 1000. 
                # A perfect academic fit will now obliterate a poorly-fitting Ivy League school!
                cgpa_diff = abs((profile.cgpa or 3.0) - req_cgpa)
                score = (cgpa_diff * 1000) + (uni.global_ranking or 999)
                
                results.append({
                    # 🚨 UI FIX: Displaying the matched course so you can see exactly what it found!
                    "name": f"{uni.name} ({prog.course_name})", 
                    "location": uni.location,
                    "ranking": uni.global_ranking,
                    "tuition": prog.tuition_fee,
                    "score": score
                })

            # Sort by our new, smarter score
            results.sort(key=lambda x: x["score"])
            
            # Remove duplicate names in case of multiple matching programs
            seen = set()
            unique_results = []
            for r in results:
                base_name = r["name"].split(" (")[0] # Check uniqueness by the actual university name
                if base_name not in seen:
                    seen.add(base_name)
                    unique_results.append(r)
            
            return unique_results[:3]
        finally:
            session.close()


class Counselor:
    pass