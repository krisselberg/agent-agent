from pydantic import BaseModel


class ScenePrompt(BaseModel):
    image_prompt: str
    character_id: str
    dialogue: str


class Character(BaseModel):
    voice_id: str
    runway_id: str


class SceneDescription(BaseModel):
    description: str
