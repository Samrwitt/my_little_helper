from fastapi import APIRouter

from app.api.routes import agent, applications, auth, dashboard, matches, notifications, profile, reminders, scholarships

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(scholarships.router)
api_router.include_router(matches.router)
api_router.include_router(applications.router)
api_router.include_router(reminders.router)
api_router.include_router(notifications.router)
api_router.include_router(agent.router)
api_router.include_router(dashboard.router)
