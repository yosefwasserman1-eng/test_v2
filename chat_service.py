
import os
import time
from typing import List, Dict, Any
from google import genai
from google.genai import types
from tools.wrapper import run_script
from tools.system_prompts import SYSTEM_INSTRUCTION
from dotenv import load_dotenv
import datetime

load_dotenv()

# Model Configuration
MODEL_NAME = "gemini-1.5-flash-002"
CACHE_TTL_MINUTES = 60

class ChatService:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.chat_id = None
        self.cached_content_name = None
        self._init_model()

    def _get_project_context(self) -> str:
        """
        Aggregates key files to build the context.
        """
        context = []
        
        # 1. Config
        try:
            with open("config.yaml", "r", encoding="utf-8") as f:
                context.append(f"--- config.yaml ---\n{f.read()}")
        except: pass

        # 2. Key Scripts
        scripts = os.listdir("scripts")
        context.append(f"--- Available Scripts ---\n{', '.join(scripts)}")

        # 3. Current Task State (Shots Board)
        try:
            with open("shots_board.json", "r", encoding="utf-8") as f:
                 context.append(f"--- shots_board.json ---\n{f.read()}")
        except: pass

        return "\n\n".join(context)

    def _create_cache(self):
        """
        Creates a context cache for the immutable/bulk parts of the system prompt.
        """
        print("💾 Creating/Updating Context Cache...")
        
        project_context = self._get_project_context()
        
        # Create the cache
        # Note: The new SDK uses client.caches.create
        try:
            cache = self.client.caches.create(
                model=MODEL_NAME,
                config=types.CreateCachedContentConfig(
                    display_name="movie_production_context",
                    system_instruction=SYSTEM_INSTRUCTION,
                    contents=[project_context],
                    ttl=f"{CACHE_TTL_MINUTES}m",
                )
            )
            self.cached_content_name = cache.name
            print(f"✅ Cache created: {cache.name}")
        except Exception as e:
            print(f"⚠️ Cache creation failed (falling back to normal context): {e}")
            self.cached_content_name = None

    def _init_model(self):
        # Tools Definition
        # In new SDK, we pass the functions directly to the client/chat
        self.tools = [self.tool_run_img_gen, self.tool_check_status]
        
        if not self.cached_content_name:
            self._create_cache()

        # We don't start a chat session object in the same way, but we keep history.
        self.history = []

    # --- TOOLS IMPLEMENTATION ---
    def tool_run_img_gen(self, shot_range: str = ""):
        """
        Runs the Flux Image Generation script.
        Args:
            shot_range: The range of shots to generate (e.g., "1-5" or "SHOT_003"). Leave empty for ALL.
        """
        print(f"🛠️ Tool Triggered: run_image_generation({shot_range})")
        # Ensure we don't pass 'ALL' literal if the script expects empty string for all
        args = [shot_range] if shot_range and shot_range.lower() != "all" else []
        result = run_script("03_img_gen.py", args=args, timeout=600)
        return result["output"]

    def tool_check_status(self):
        """
        Checks the status of the production.
        """
        print(f"🛠️ Tool Triggered: check_status")
        try:
            import json
            with open("shots_board.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                stats = {"TOTAL": len(data), "APPROVED": 0, "PENDING": 0, "IMAGE_READY": 0}
                for k, v in data.items():
                    s = v.get("stills", {}).get("status", "UNKNOWN")
                    stats[s] = stats.get(s, 0) + 1
                return str(stats)
        except Exception as e:
            return f"Error reading status: {e}"

    def send_message(self, user_input: str):
        """
        Sends a message to the model and handles tool calls.
        """
        config_args = {
            "temperature": 0.4,
            "tools": self.tools,
        }
        
        # If we have a cache, we use it. If not, we pass system instruction directly (if not cached).
        # Actually, if cache is used, model is implicitly bound to it in the generate_content call
        # via 'cached_content' argument ONLY if we don't pass the model name (or pass a specially formatted model name).
        # But in new SDK, we usually pass 'model' AND 'cached_content'.
        
        if self.cached_content_name:
            # When using cache, the system instruction is IN the cache.
            model_id = MODEL_NAME # The base model
            cached_content = self.cached_content_name
            sys_instruct = None 
        else:
            model_id = MODEL_NAME
            cached_content = None
            sys_instruct = SYSTEM_INSTRUCTION

        # The new SDK's chat interface
        chat = self.client.chats.create(
            model=model_id,
            config=types.GenerateContentConfig(
                temperature=0.4,
                system_instruction=sys_instruct,
                tools=self.tools,
                cached_content=cached_content, 
            ),
            history=self.history
        )

        response = chat.send_message(user_input)
        
        # Capture history (The chat object updates its own history, but if we recreate it every time... 
        # wait, we shouldn't recreate it every time if we want multi-turn.
        # But 'client.chats.create' creates a new session.
        # We should store `self.chat`.)
        
        # Fix: Store the chat session.
        if not hasattr(self, "chat_session") or self.chat_session is None:
            self.chat_session = chat
        else:
            # Start a new session if config changed? No, just keep it.
            # But wait, if I used 'create' locally, I lost the previous history if I don't persist it.
            # Let's persist self.chat_session
            pass
            
        # Actually, if I created it above locally, I just overwrote the history handling.
        # I should initialize `chat_session` in `__init__` or lazy load it.
        # But `cached_content` might change.
        # For this PoC, I'll initialize it once.
        
        return response.text

    def _lazy_init_chat(self):
        if hasattr(self, "chat_session") and self.chat_session:
            return

        if self.cached_content_name:
            sys_instruct = None
            cached_content = self.cached_content_name
        else:
            sys_instruct = SYSTEM_INSTRUCTION
            cached_content = None

        self.chat_session = self.client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                temperature=0.4,
                system_instruction=sys_instruct,
                tools=self.tools,
                cached_content=cached_content
            ),
            history=self.history
        )

    def send_message_v2(self, user_input: str):
        self._lazy_init_chat()
        response = self.chat_session.send_message(user_input)
        return response.text
