from fastapi import FastAPI, HTTPException
from functions import VideoGeneration
import json
from pathlib import Path
from pydantic import BaseModel
from typing import List

app = FastAPI()


class CreateVideoRequest(BaseModel):
    video_id: str
    character_ids: List[str]
    description: str


class CreateAgentRequest(BaseModel):
    # Add agent-specific fields here
    pass


@app.post("/create_agent", status_code=201)
async def create_agent(request: CreateAgentRequest):
    try:
        # Here you would typically process the data and create an agent
        return {
            "status": "success",
            "message": "Agent created successfully",
            "data": request.dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/video/{video_id}/status")
async def get_video_status(video_id: str):
    try:
        status_file = Path(f"statuses/{video_id}.json")
        if not status_file.exists():
            raise HTTPException(status_code=404, detail="Video ID not found")

        with open(status_file, "r") as f:
            status = json.load(f)

        return {
            "status": "success",
            "video_id": video_id,
            "video_status": status["status"],
            "progress": status["progress"],
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/video", status_code=201)
async def create_video(request: CreateVideoRequest):
    try:
        # Create and start video generation job
        video_gen = VideoGeneration(request.video_id, request.character_ids)

        # Start the generation process asynchronously
        final_video_path = await video_gen.generate_video(
            description=request.description
        )

        return {
            "status": "success",
            "message": "Video creation initiated",
            "video_id": request.video_id,
            "character_ids": request.character_ids,
            "description": request.description,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
