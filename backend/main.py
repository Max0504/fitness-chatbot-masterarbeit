from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine
from .models import Base
from .routers import profile, plan, dashboard, workouts, exercises, nutrition, progress, activity
from .seed import seed_if_empty

app = FastAPI(title="Fitness Chatbot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_if_empty()


app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(plan.router, prefix="/api/plan", tags=["plan"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(workouts.router, prefix="/api/workouts", tags=["workouts"])
app.include_router(exercises.router, prefix="/api/exercises", tags=["exercises"])
app.include_router(nutrition.router, prefix="/api/nutrition", tags=["nutrition"])
app.include_router(progress.router, prefix="/api/progress", tags=["progress"])
app.include_router(activity.router, prefix="/api/activity", tags=["activity"])


@app.get("/")
def root():
    return {"status": "ok", "service": "fitness-chatbot-api"}
