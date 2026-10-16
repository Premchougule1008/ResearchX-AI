import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field


FRONTEND_DIR = Path(__file__).resolve().parent / "Frontend"
logger = logging.getLogger(__name__)
app = FastAPI(title="ResearchX API")


class ResearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    topic: str = Field(min_length=1, max_length=500)


class ResearchResponse(BaseModel):
    topic: str
    report: str
    feedback: str
    search_results: str
    scraped_content: str
    fallback: bool = False


@app.post("/api/research", response_model=ResearchResponse)
def research(payload: ResearchRequest) -> ResearchResponse:
    topic = payload.topic
    try:
        from src.Pipelines.pipeline import run_research_pipeline

        result = run_research_pipeline(topic)
    except Exception as exc:
        logger.exception("Research pipeline could not be started.")
        raise HTTPException(
            status_code=500,
            detail="The research service could not be started. Check the server logs and API credentials.",
        ) from exc

    if result.get("error"):
        logger.error("Research pipeline failed: %s", result["error"])
        raise HTTPException(status_code=502, detail=result["error"])

    return ResearchResponse(
        topic=topic,
        report=result.get("report", ""),
        feedback=result.get("feedback", ""),
        search_results=result.get("search_results", ""),
        scraped_content=result.get("scraped_content", ""),
        fallback=result.get("fallback", False),
    )


app.mount("/", app=StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

