"""
councelling_module.py — University Counseling & KNN Recommendation.
"""
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from dotenv import load_dotenv

load_dotenv()

# ✅ Updated imports to bypass the deleted root models.py
from database.models import StudentProfile, University
from database.connection import get_sync_session


class UniversityRecommender:
    def __init__(self):
        self.scaler = StandardScaler()
        self.model = None
        self.universities_df = None
        self.features_scaled = None

    def load_and_train(self):
        """Loads university data from DB and trains the KNN model."""
        session = get_sync_session()
        try:
            universities = session.query(University).all()

            if not universities:
                print("⚠️  No universities in DB. Populating dummy data...")
                populate_dummy_data()
                # Re-fetch after populating
                session.close()
                session = get_sync_session()
                universities = session.query(University).all()

            data = []
            for u in universities:
                tuition = None
                try:
                    program_tuitions = [
                        float(p.tuition_fee)
                        for p in (u.programs or [])
                        if p.tuition_fee is not None
                    ]
                    if program_tuitions:
                        tuition = sum(program_tuitions) / len(program_tuitions)
                except Exception:
                    pass
                if tuition is None:
                    tuition = 20000.0

                ranking = u.global_ranking if u.global_ranking is not None else 999

                data.append({
                    'id': str(u.id),
                    'name': u.name,
                    'tuition': float(tuition),
                    'ranking': int(ranking),
                })

            self.universities_df = pd.DataFrame(data)
            features = self.universities_df[['tuition', 'ranking']]
            self.features_scaled = self.scaler.fit_transform(features)

            n_neighbors = min(3, len(self.universities_df))
            self.model = NearestNeighbors(n_neighbors=n_neighbors, algorithm='auto')
            self.model.fit(self.features_scaled)
            print(f"✅ Recommender trained on {len(self.universities_df)} universities.")

        finally:
            session.close()

    def recommend(self, user_profile):
        """Finds universities closest to the user's preferences."""
        if self.model is None or self.universities_df is None:
            print("⚠️  Model not trained yet. Run load_and_train() first.")
            return []

        try:
            cgpa_val = float(user_profile.cgpa or 0)
        except Exception:
            cgpa_val = 0.0
        desired_rank = 50 if cgpa_val >= 3.5 else 200

        desired_tuition = 20000.0
        try:
            bmin = user_profile.budget_min
            bmax = user_profile.budget_max
            if bmin is not None and bmax is not None:
                desired_tuition = (float(bmin) + float(bmax)) / 2.0
            elif bmax is not None:
                desired_tuition = float(bmax)
            elif bmin is not None:
                desired_tuition = float(bmin)
        except Exception:
            pass

        user_vector = np.array([[desired_tuition, desired_rank]])
        user_vector_scaled = self.scaler.transform(user_vector)
        distances, indices = self.model.kneighbors(user_vector_scaled)

        recommendations = []
        for i in indices[0]:
            uni = self.universities_df.iloc[i]
            recommendations.append(uni.to_dict())

        return recommendations


class Counselor:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_profile(self):
        """Fetch the current profile from DB."""
        session = get_sync_session()
        try:
            return session.query(StudentProfile).filter_by(user_id=self.user_id).first()
        finally:
            session.close()


def populate_dummy_data():
    """Adds sample universities if the table is empty."""
    session = get_sync_session()
    try:
        count = session.query(University).count()
        if count == 0:
            print("Adding sample universities to DB...")
            dummy_unis = [
                University(name="MIT", global_ranking=1, location="Cambridge, USA"),
                University(name="Stanford University", global_ranking=3, location="Stanford, USA"),
                University(name="University of Toronto", global_ranking=18, location="Toronto, Canada"),
                University(name="University of Edinburgh", global_ranking=22, location="Edinburgh, UK"),
                University(name="TU Berlin", global_ranking=80, location="Berlin, Germany"),
                University(name="University of Florida", global_ranking=150, location="Florida, USA"),
                University(name="Community College of NY", global_ranking=800, location="New York, USA"),
            ]
            session.add_all(dummy_unis)
            session.commit()
            print(f"✅ Added {len(dummy_unis)} universities.")
    except Exception as e:
        session.rollback()
        print(f"Warning: Could not populate dummy data: {e}")
    finally:
        session.close()