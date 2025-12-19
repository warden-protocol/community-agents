from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from agent.graph import build_graph

# load environment variables from .env
load_dotenv()

app = FastAPI(
    title="Onchain Risk & Anomaly Monitor Agent",
    version="0.1.0",
)

graph = build_graph()


class AnalyzeRequest(BaseModel):
    chain: str = Field(..., description="blockchain name, e.g. ethereum")
    targets: list[str] = Field(..., description="list of wallet or contract addresses")
    window_minutes: int = Field(60, description="60, 360, or 1440")
    risk_profile: str = Field("balanced", description="strict | balanced | fast")
    tvl_protocol_slug: str | None = Field(
        None, description="optional defillama protocol slug (e.g. aave)"
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    try:
        state = {"request": request.model_dump()}
        output = graph.invoke(state)
        return output["result"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
