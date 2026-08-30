from pydantic import BaseModel


class InsightsResponse(BaseModel):
    generated_at: str
    data: dict


class InsightsDatasetsResponse(BaseModel):
    generated_at: str
    datasets: list[dict]
