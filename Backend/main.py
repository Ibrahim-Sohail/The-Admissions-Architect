"""
main.py — Web Server Entry Point for The Admission Architect.

Run this file to start your backend API so your Node.js frontend can connect to it!
"""
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables before starting the server
load_dotenv()

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Starting The Admission Architect Web API...")
    print("📡 Your Node.js frontend can now connect to: http://localhost:8000")
    print("=" * 50)
    
    # The string "api:app" tells uvicorn to look inside your 'api.py' file 
    # and run the FastAPI instance named 'app'.
    # reload=True means the server will auto-restart if you save changes to your code!
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)