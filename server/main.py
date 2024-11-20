from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

from src.graph.LLMGraph import LLMGraph

llmGraph = LLMGraph()

config = {
    "configurable": {
        "user_id": "13wldjf",
        "thread_id": "22390230jas;dfj"
    }
}

app = None

class Message(BaseModel):
    content: str


def create_app() -> FastAPI:
    global app
    app = FastAPI()

    origins = [
        "http://localhost",
        "http://localhost:5000",
        "http://localhost:3000",
        "http://localhost:5001",
        "http://localhost:443"
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    @app.post("/stream")
    async def stream_response(message: Message):
        content = message.content
        async def generate_response():
            async for msg, metadata in llmGraph.graph.astream({"messages": ("user", content)}, config, stream_mode="messages"):
                if msg.content:
                    yield msg.content
            
        return StreamingResponse(generate_response(), media_type="text/event-stream")
    
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)