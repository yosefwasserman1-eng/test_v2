
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from chat_service import ChatService

app = FastAPI()

# Database / Service Instance
# In a real app, this should be a dependency injection or singleton pattern
chat_service = ChatService()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Using the v2 methods we defined
        response_text = chat_service.send_message_v2(request.message)
        return {"response": response_text}
    except Exception as e:
        print(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/{file_path:path}")
async def get_file(file_path: str):
    """
    Securely serves files from the 'production' or 'assets' directories.
    Prevents Path Traversal.
    """
    # Normalize paths
    safe_roots = [
        os.path.abspath("production"),
        os.path.abspath("assets"),
        # Add 'scripts' if we want to show code, but maybe unsafe.
    ]
    
    requested_path = os.path.abspath(file_path)
    
    # Check if the requested path starts with any of the safe roots
    is_safe = any(requested_path.startswith(root) for root in safe_roots)
    
    if not is_safe:
        raise HTTPException(status_code=403, detail="Access denied: File outside allowed directories.")
    
    if not os.path.exists(requested_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(requested_path)

@app.post("/api/context/refresh")
async def refresh_context():
    chat_service._create_cache()
    chat_service.chat_session = None # Force recreation
    return {"status": "Cache refreshing..."}

if __name__ == "__main__":
    import uvicorn
    # 0.0.0.0 for Cloud Run / Docker
    uvicorn.run(app, host="0.0.0.0", port=8080)
