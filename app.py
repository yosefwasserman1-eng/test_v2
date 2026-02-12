
import chainlit as cl
import re
import os
import asyncio
import logging
from pathlib import Path
from chat_service import ChatService
from tools.wrapper import run_script

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Chat Service
chat_service = ChatService()

@cl.on_chat_start
async def start():
    # Welcome Message
    await cl.Message(
        content="🎬 **Miri Production System Online!**\n\nI am ready for your commands. Try:\n* 'Generate Shot 5'\n* 'What is the project status?'\n* 'Check prompt for Shot 10'"
    ).send()

@cl.on_message
async def main(message: cl.Message):
    user_input = message.content
    
    # Send "Thinking..." message
    msg = cl.Message(content="")
    await msg.send()

    # 1. Intent Detection
    # If user wants to generate, we bypass Gemini for speed and stability
    
    # Pattern: "shot X" or "generate" + "shot X"
    is_generation_request = "generate" in user_input.lower() or "ייצר" in user_input
    shot_match = re.search(r'(?:shot|שוט)[_ ]?(\d+)', user_input, re.IGNORECASE)

    if is_generation_request and shot_match:
        shot_num = shot_match.group(1)
        shot_id = f"SHOT_{int(shot_num):03d}"
        
        await run_generation_flow(shot_id, msg)
        return

    # 2. Standard Chat with Gemini
    # Run in thread executor if chat_service.send_message is blocking (it is synchronous in the refactor)
    # chainlit.make_async helps here, or we can use loop.run_in_executor
    response_text = await cl.make_async(chat_service.send_message)(user_input)
    
    # Update response
    msg.content = response_text
    await msg.update()

async def run_generation_flow(shot_id: str, msg_element: cl.Message):
    """
    Manages the generation flow: Run Script -> Wait -> Display Image
    """
    msg_element.content = f"🎨 Starting generation for **{shot_id}**... (Sending to Flux)"
    await msg_element.update()

    async with cl.Step(name="Flux Generator") as step:
        step.input = f"Target: {shot_id}"
        
        # Run script via wrapper (wrapper uses subprocess, which is blocking, so run_script is synchronous)
        # We wrap it in make_async to not block the event loop
        result = await cl.make_async(run_script)("03_img_gen.py", args=[shot_id])
        
        if result["success"]:
            output_log = result["output"]
            
            # Parse log for image path
            # Looking for "production/images/SHOT_001.jpg"
            match = re.search(r'(production[\\/].+\.jpg)', output_log)
            
            if match:
                # Normalize path using pathlib
                raw_path = match.group(1).replace("\\", "/") # Initial cleanup
                # We need to ensure it matches the actual OS file system
                # wrapper ensures CWD is root.
                
                # Convert to Path object for verification using make_async to avoid blocking
                # though os.path.exists is fast, best practice in async heavy apps
                img_rel_path = raw_path
                img_abs_path = Path(os.getcwd()) / img_rel_path
                
                # Check existence asynchronously
                loop = asyncio.get_running_loop()
                file_exists = await loop.run_in_executor(None, img_abs_path.exists)
                
                if file_exists:
                    # --- Display Image ---
                    # Chainlit expects a path string
                    image = cl.Image(path=str(img_abs_path), name=shot_id, display="inline")
                    
                    await cl.Message(
                        content=f"✅ **{shot_id}** is ready!",
                        elements=[image]
                    ).send()
                    
                    step.output = "Success. Image displayed."
                else:
                    step.output = f"File created but not found at: {img_abs_path}"
                    logger.error(f"Image not found at {img_abs_path}")
            else:
                step.output = "Script ran successfully but no image path found in output."
                await cl.Message(content=f"```\n{output_log}\n```").send()
        else:
            step.output = f"Execution Error: {result.get('error', 'Unknown error')}"
            await cl.Message(content=f"❌ Error:\n```\n{result['output']}\n```").send()

    # Reset/Finalize "Thinking" message
    msg_element.content = "Process finished."
    await msg_element.update()
