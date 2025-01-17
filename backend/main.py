from fastapi import FastAPI, HTTPException
from functions import VideoGeneration
import json
from pathlib import Path
from pydantic import BaseModel
from typing import List
import asyncio

app = FastAPI()

# Store video generation objects in memory
video_generations = {}


class CreateVideoRequest(BaseModel):
    video_id: str
    character_ids: List[str]
    description: str


class CreateAgentRequest(BaseModel):
    # Add agent-specific fields here
    pass


@app.get("/video/{video_id}/status")
async def get_video_status(video_id: str):
    try:
        if video_id not in video_generations:
            raise HTTPException(status_code=404, detail="Video ID not found")

        video_gen = video_generations[video_id]
        status = video_gen._get_status()

        return status
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Video ID not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/video", status_code=201)
async def create_video(request: CreateVideoRequest):
    try:
        # Create video generation instance
        video_gen = VideoGeneration(
            request.video_id, request.character_ids, request.description
        )

        # Store in map
        video_generations[request.video_id] = video_gen

        # Start the generation process in the background
        asyncio.create_task(video_gen.generate_video())

        # Return immediately with the video ID
        return {
            "status": "success",
            "message": "Video creation initiated",
            "video_id": request.video_id,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
