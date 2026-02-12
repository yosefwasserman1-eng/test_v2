
import os
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from google import genai
from google.genai import types
from tools.wrapper import run_script
from tools.system_prompts import SYSTEM_INSTRUCTION
from utils.config_loader import get_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("GEMINI_API_KEY not found in environment variables.")
            raise ValueError("GEMINI_API_KEY not found")
            
        self.client = genai.Client(api_key=self.api_key)
        self.chat_id = None
        self.cached_content_name = None
        
        # Load config values
        self.model_name = get_config("models.gemini", "gemini-1.5-flash-002")
        self.cache_ttl = int(get_config("pipeline.cache_ttl_minutes", 60))
        
        self._init_model()

    def _get_project_context(self) -> str:
        """
        Aggregates key files to build the context.
        """
        context = []
        root_dir = Path(os.getcwd())
        
        # 1. Config
        config_path = root_dir / "config.yaml"
        if config_path.exists():
            try:
                context.append(f"--- config.yaml ---\n{config_path.read_text(encoding='utf-8')}")
            except Exception as e:
                logger.error(f"Failed to read config.yaml: {e}")

        # 2. Key Scripts
        scripts_dir = root_dir / "scripts"
        if scripts_dir.exists() and scripts_dir.is_dir():
            try:
                scripts = [f.name for f in scripts_dir.glob("*.py")]
                context.append(f"--- Available Scripts ---\n{', '.join(scripts)}")
            except Exception as e:
                logger.error(f"Failed to list scripts: {e}")

        # 3. Current Task State (Shots Board)
        shots_board_path = root_dir / "shots_board.json"
        if shots_board_path.exists():
            try:
                 context.append(f"--- shots_board.json ---\n{shots_board_path.read_text(encoding='utf-8')}")
            except Exception as e:
                logger.error(f"Failed to read shots_board.json: {e}")

        return "\n\n".join(context)

    def _create_cache(self):
        """
        Creates a context cache for the immutable/bulk parts of the system prompt.
        """
        logger.info("💾 Creating/Updating Context Cache...")
        
        project_context = self._get_project_context()
        
        try:
            cache = self.client.caches.create(
                model=self.model_name,
                config=types.CreateCachedContentConfig(
                    display_name="movie_production_context",
                    system_instruction=SYSTEM_INSTRUCTION,
                    contents=[project_context],
                    ttl=f"{self.cache_ttl}m",
                )
            )
            self.cached_content_name = cache.name
            logger.info(f"✅ Cache created: {cache.name}")
        except Exception as e:
            logger.warning(f"⚠️ Cache creation failed (falling back to normal context): {e}")
            self.cached_content_name = None

    def _init_model(self):
        # Tools Definition
        self.tools = [self.tool_run_img_gen, self.tool_check_status]
        
        if not self.cached_content_name:
            self._create_cache()

        self.history = []

    # --- TOOLS IMPLEMENTATION ---
    def tool_run_img_gen(self, shot_range: str = ""):
        """
        Runs the Flux Image Generation script.
        Args:
            shot_range: The range of shots to generate (e.g., "1-5" or "SHOT_003"). Leave empty for ALL.
        """
        logger.info(f"🛠️ Tool Triggered: run_image_generation({shot_range})")
        args = [shot_range] if shot_range and shot_range.lower() != "all" else []
        
        # run_script should be robust enough, but let's wrap it just in case
        try:
            result = run_script("03_img_gen.py", args=args, timeout=600)
            return result["output"]
        except Exception as e:
            logger.error(f"Error running image generation tool: {e}")
            return f"Error: {str(e)}"

    def tool_check_status(self):
        """
        Checks the status of the production.
        """
        logger.info(f"🛠️ Tool Triggered: check_status")
        try:
            import json
            shots_board_path = Path("shots_board.json")
            if not shots_board_path.exists():
                return "shots_board.json not found."
                
            with open(shots_board_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                stats = {"TOTAL": len(data), "APPROVED": 0, "PENDING": 0, "IMAGE_READY": 0}
                for k, v in data.items():
                    s = v.get("stills", {}).get("status", "UNKNOWN")
                    stats[s] = stats.get(s, 0) + 1
                return str(stats)
        except Exception as e:
            logger.error(f"Error reading status: {e}")
            return f"Error reading status: {e}"

    def _lazy_init_chat(self):
        if hasattr(self, "chat_session") and self.chat_session:
            return

        if self.cached_content_name:
            sys_instruct = None
            cached_content = self.cached_content_name
        else:
            sys_instruct = SYSTEM_INSTRUCTION
            cached_content = None

        try:
            self.chat_session = self.client.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    system_instruction=sys_instruct,
                    tools=self.tools,
                    cached_content=cached_content
                ),
                history=self.history
            )
        except Exception as e:
            logger.error(f"Failed to create chat session: {e}")
            raise

    def send_message(self, user_input: str) -> str:
        """
        Sends a message to the model and handles tool calls.
        """
        try:
            self._lazy_init_chat()
            response = self.chat_session.send_message(user_input)
            return response.text
        except Exception as e:
            logger.error(f"Error sending message to Gemini: {e}")
            return f"An error occurred while communicating with the AI: {str(e)}"
