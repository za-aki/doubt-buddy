from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import the compiled LangGraph agent from your agent.py file
from agent import agent

app = FastAPI(
    title="Homework Helper API",
    description="An AI agent that solves, explains, and quizzes students on homework questions.",
    version="1.0.0"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://doubt-buddy-tau.vercel.app",
                   "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the request JSON payload structure
class AskRequest(BaseModel):
    question: str
    language: str

# Define the response JSON payload structure
class AskResponse(BaseModel):
    subject: str
    explanation: str
    quiz_question: str
@app.get("/")
async def root():
    return {"message": "Homework Helper API is running successfully!"}

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    try:
        # Invoke the compiled LangGraph agent
        # Passing initial state to the graph
        result = agent.invoke({
            "question": request.question,
            "language": request.language,
            "retry_count": 0
        })
        
        # Return only the requested fields
        return AskResponse(
            subject=result.get("subject", "Unknown"),
            explanation=result.get("explanation", "Could not generate an explanation."),
            quiz_question=result.get("quiz_question", "No follow-up question available.")
        )
        
    except Exception as e:
        # Catch errors from Groq API or graph execution
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")

if __name__ == "__main__":
    # Run the server locally on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
