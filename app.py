import logging
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

# Load environment variables from .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

FRONTEND_DIR = BASE_DIR / "Frontend"

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

# FastAPI application
app = FastAPI(
    title="ResearchX AI API",
    description="AI-powered multi-agent research application",
    version="1.0.0",
)


# Request schema
class ResearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    topic: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Research topic",
    )


# Response schema
class ResearchResponse(BaseModel):
    topic: str
    report: str
    feedback: str
    search_results: str
    scraped_content: str
    fallback: bool = False


@app.get("/health")
def health_check():
    """Check whether the API is running."""
    return {
        "status": "healthy",
        "application": "ResearchX AI",
    }


@app.post("/api/research", response_model=ResearchResponse)
def research(payload: ResearchRequest) -> ResearchResponse:
    """Run the multi-agent research pipeline."""

    topic = payload.topic

    logger.info("Research request received for topic: %s", topic)

    try:
        from src.Pipelines.pipeline import run_research_pipeline

        result = run_research_pipeline(topic)

        if not isinstance(result, dict):
            logger.error("Pipeline returned an invalid response.")
            raise HTTPException(
                status_code=502,
                detail="The research pipeline returned an invalid response.",
            )

        if result.get("error"):
            logger.error(
                "Research pipeline failed: %s",
                result["error"],
            )
            raise HTTPException(
                status_code=502,
                detail=str(result["error"]),
            )

        report = result.get("report", "")

        if not report:
            logger.warning(
                "Research pipeline returned an empty report for topic: %s",
                topic,
            )

        logger.info("Research request completed for topic: %s", topic)

        return ResearchResponse(
            topic=topic,
            report=report,
            feedback=result.get("feedback", ""),
            search_results=result.get("search_results", ""),
            scraped_content=result.get("scraped_content", ""),
            fallback=result.get("fallback", False),
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Research pipeline could not be started or completed."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "The research service encountered an internal error. "
                "Check the terminal logs, model configuration, and API credentials."
            ),
        ) from exc


# Serve the frontend
if FRONTEND_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="frontend",
    )
else:
    logger.warning(
        "Frontend directory not found: %s",
        FRONTEND_DIR,
    )


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )


