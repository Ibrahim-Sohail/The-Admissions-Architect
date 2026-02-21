"""Compatibility shim — re-exports from the correctly-spelled module."""
from councelling_module import Counselor, UniversityRecommender, populate_dummy_data

__all__ = ["Counselor", "UniversityRecommender", "populate_dummy_data"]
