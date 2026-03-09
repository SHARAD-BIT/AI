from fastapi import FastAPI
from app.api import resume_routes, tender_routes

app = FastAPI(title="Tender Resume Matching RAG System")

app.include_router(tender_routes.router)
app.include_router(resume_routes.router)


@app.get("/")
def root():
    return {"message": "Tender RAG system running"}
