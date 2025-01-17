import os
import json
from typing import List, Dict
import asyncio
from dotenv import load_dotenv
from class_types import ScenePrompt, Character, SceneDescription
from pathlib import Path
import replicate

# Load environment variables
load_dotenv()

from openai import AsyncOpenAI


openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
replicate_client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))


character_map = {
    "marionetta": "tharunkumartk/flux-marionetta:bbf2195b8e08319ba49dcc47275ec6a2e6e840763bf179c644db45235ae686a6",
    "sbg": "tharunkumartk/flux-sbg:8c17c2b0433859b461146c992548514100ef34be279bc6e72f55f7c3549016f0",
    "eleceed": "tharunkumartk/flux-eleceed:8e67f6038d53f6afbac83d2320e1851b7e582c93f4edc49536c8b2e924976a19",
    "snape": "tharunkumartk/snape:3a21251a6fb91b493e8623a1edecd3d544699fe0e47a525851b563c4e5e0ab14",
    "draco": "tharunkumartk/draco:98d6b20c",
    "samay": "tharunkumartk/samay-personal:15d25eb4",
    "will": "tharunkumartk/will-personal:5b8485e6",
    "tharun": "tharunkumartk/personal-flux:18081e54",
}


class VideoGeneration:
    def __init__(self, video_id: str, character_ids: List[str], description: str):
        self.video_id = video_id
        self.character_ids = character_ids
        self.description = description
        self.status_dir = Path("statuses")
        self.status_dir.mkdir(exist_ok=True)
        self.status_file = self.status_dir / f"{video_id}.json"
        self._initialize_status()

    def _initialize_status(self):
        """Initialize or load the status file for this video generation job"""
        status = {
            "video_id": self.video_id,
            "status": "initialized",
            "progress": 0,
            "steps_completed": [],
            "error": None,
            "generated_content": {
                "story_description": None,
                "scene_prompts": [],
                "image_paths": [],
                "audio_paths": [],
                "video_paths": [],
                "final_video_path": None,
            },
        }
        self._save_status(status)

    def _save_status(self, status: Dict):
        """Save the current status to the status file"""
        with open(self.status_file, "w") as f:
            json.dump(status, f, indent=2)

    def _update_status(
        self, status: str, progress: int, error: str = None, **content_updates
    ):
        """Update the status file with new information"""
        current_status = self._get_status()
        current_status["status"] = status
        current_status["progress"] = progress
        if error:
            current_status["error"] = error
        if content_updates:
            current_status["generated_content"].update(content_updates)
        self._save_status(current_status)

    def _get_status(self) -> Dict:
        """Get the current status from the status file"""
        with open(self.status_file, "r") as f:
            return json.load(f)

    async def get_story_description(self, description: str) -> SceneDescription:
        """Get a story description based on the characters"""
        self._update_status("generating_story", 10)

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": "Generate a really cool and funny story description for the characters "
                    + str(self.character_ids)
                    + " in a video about "
                    + description
                    + "Make sure that you ONLY output the story description. DO NOT INCLUDE ANYTHING ELSE.",
                }
            ],
            temperature=0.9,
        )
        story_description = SceneDescription(
            description=response.choices[0].message.content
        )
        self._update_status(
            "generating_story",
            15,
            story_description=story_description.description,
            story_description_prompt=response.choices[0].message.content,
        )
        return story_description

    async def get_scene_list(
        self, story_description: SceneDescription
    ) -> List[ScenePrompt]:
        """Generate a list of scenes from the story description"""
        self._update_status("generating_scenes", 20)
        system_prompt = """
        You are a helpful assistant that generates scenes for a generated video. Make the scenes funny, and follow the story description given by the user. Your output will be a JSON list of 7-8 scenes in the following format:

        {
            "data":[
                {
                    "image_prompt": "A prompt for the image",
                    "character_id": "The ID of the character",
                    "dialogue": "The dialogue for the scene"
                }
            ]
        }

        
        Make sure you are extremely creative, dramatic, and CONCISE. It is crucuial that you keep the dialogue concise and to the point. MAKE SURE YOU ONLY INCLUDE CHARACTERS THAT ARE IN THE AVAILABLE CHARACTERS LIST.
        """

        user_prompt = f"""
        Story description: {story_description.description}
        Available characters: {self.character_ids}
        """

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,
        )

        scene_prompts = json.loads(response.choices[0].message.content)["data"]
        scene_prompts = [
            ScenePrompt(
                image_prompt=scene["image_prompt"],
                character_id=scene["character_id"],
                dialogue=scene["dialogue"],
            )
            for scene in scene_prompts
        ]
        self._update_status(
            "generating_scenes",
            25,
            scene_prompts=[scene.dict() for scene in scene_prompts],
            scene_prompts_prompt=response.choices[0].message.content,
        )
        return scene_prompts

    async def generate_image(self, prompt: str, character_id: str) -> str:
        """Generate a single image using Replicate API for a given character and prompt"""
        if character_id not in character_map:
            raise ValueError(f"Invalid character ID: {character_id}")

        model_version = character_map[character_id]

        # Create prediction with Replicate API
        output = replicate_client.run(
            model_version,
            input={
                "prompt": prompt,
                "model": "dev",
                "go_fast": False,
                "lora_scale": 1,
                "megapixels": "1",
                "num_outputs": 1,
                "aspect_ratio": "1:1",
                "output_format": "webp",
                "guidance_scale": 3,
                "output_quality": 80,
                "prompt_strength": 0.8,
                "extra_lora_scale": 1,
                "num_inference_steps": 28,
            },
        )

        # Replicate returns a list with one URL for num_outputs=1
        image_url = output[0]
        return image_url

    async def get_images(self, scene_prompts: List[ScenePrompt]) -> List[str]:
        """Generate images for each scene prompt"""
        self._update_status("generating_images", 40)
        image_dir = Path(f"output/{self.video_id}/images")
        image_dir.mkdir(parents=True, exist_ok=True)

        # Generate images for each scene
        image_urls = []
        for i, scene in enumerate(scene_prompts):
            image_url = await self.generate_image(
                scene.image_prompt, scene.character_id
            )
            image_urls.append(image_url)

        self._update_status("generating_images", 45, image_paths=image_urls)
        return image_urls

    async def get_audios(self, scene_prompts: List[ScenePrompt]) -> List[str]:
        """Generate audio for each scene prompt"""
        self._update_status("generating_audio", 60)
        audio_dir = Path(f"output/{self.video_id}/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)

        await asyncio.sleep(2)  # Simulate async audio generation
        audio_paths = [
            str(audio_dir / f"scene_{i}.mp3") for i in range(len(scene_prompts))
        ]
        self._update_status("generating_audio", 65, audio_paths=audio_paths)
        return audio_paths

    async def get_video_urls(self, image_paths: List[str]) -> List[str]:
        """Generate videos from images"""
        self._update_status("generating_videos", 80)
        video_dir = Path(f"output/{self.video_id}/videos")
        video_dir.mkdir(parents=True, exist_ok=True)

        await asyncio.sleep(2)  # Simulate async video generation
        video_paths = [
            str(video_dir / f"scene_{i}.mp4") for i in range(len(image_paths))
        ]
        self._update_status("generating_videos", 85, video_paths=video_paths)
        return video_paths

    async def splice_videos(
        self, video_paths: List[str], audio_paths: List[str]
    ) -> str:
        """Combine videos and audio into final output"""
        self._update_status("splicing_video", 90)
        final_dir = Path(f"output/{self.video_id}/final")
        final_dir.mkdir(parents=True, exist_ok=True)
        final_path = str(final_dir / "final_video.mp4")

        await asyncio.sleep(2)  # Simulate async video splicing
        self._update_status("completed", 100, final_video_path=final_path)
        return final_path

    async def generate_video(self) -> str:
        """Main function to orchestrate the entire video generation process"""
        try:
            # Get story description
            story_description = await self.get_story_description(self.description)

            # Generate scenes
            scene_prompts = await self.get_scene_list(story_description)

            # Generate images and audio in parallel
            image_paths, audio_paths = await asyncio.gather(
                self.get_images(scene_prompts), self.get_audios(scene_prompts)
            )

            # Generate individual videos
            video_paths = await self.get_video_urls(image_paths)

            # Combine everything
            final_video_path = await self.splice_videos(video_paths, audio_paths)

            return final_video_path

        except Exception as e:
            self._update_status("failed", 0, str(e))
            raise e
