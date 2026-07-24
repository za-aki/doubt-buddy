import os
import pandas as pd
from typing import TypedDict, Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

# ============================================
# SETUP
# ============================================
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found. Check your .env file.")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0.2
)

# ============================================
# STATE
# ============================================
class AgentState(TypedDict):
    question: str
    language: str
    subject: Optional[str]
    solution: Optional[str]
    is_verified: Optional[bool]
    verification_feedback: Optional[str]
    explanation: Optional[str]
    quiz_question: Optional[str]
    retry_count: int

# ============================================
# NODES
# ============================================
def classify_node(state: AgentState) -> AgentState:
    prompt = f"""Classify this homework question into exactly one subject:
Math, Science, English, or Social Studies.
Question: {state['question']}
Reply with only the subject name."""
    result = llm.invoke(prompt)
    state["subject"] = result.content.strip()
    return state


def solve_node(state: AgentState) -> AgentState:
    feedback_note = ""
    if state.get("verification_feedback"):
        feedback_note = f"\nYour previous attempt had this issue: {state['verification_feedback']}. Fix it."

    prompt = f"""Solve this {state['subject']} question step by step, showing all working.
Question: {state['question']}{feedback_note}"""
    result = llm.invoke(prompt)
    state["solution"] = result.content
    return state


def verify_node(state: AgentState) -> AgentState:
    prompt = f"""Check this solution for correctness and internal consistency.
Question: {state['question']}
Solution: {state['solution']}
Reply with exactly one line starting with either "VALID" or "INVALID: <reason>"."""
    result = llm.invoke(prompt).content.strip()

    if result.startswith("VALID"):
        state["is_verified"] = True
    else:
        state["is_verified"] = False
        state["verification_feedback"] = result.replace("INVALID:", "").strip()
        state["retry_count"] = state.get("retry_count", 0) + 1
    return state


def route_after_verify(state: AgentState) -> str:
    if state["is_verified"]:
        return "explain"
    if state.get("retry_count", 0) >= 2:
        return "explain"  # avoid infinite loops
    return "solve"


def explain_node(state: AgentState) -> AgentState:
    prompt = f"""Explain this solution in simple, friendly language a school student would understand.
Translate the explanation into {state['language']}.
Question: {state['question']}
Solution: {state['solution']}"""
    result = llm.invoke(prompt)
    state["explanation"] = result.content
    return state


# ============================================
# TOPICS CSV
# ============================================
CSV_PATH = os.path.join(os.path.dirname(__file__), "topics.csv")

def _ensure_topics_csv():
    if os.path.exists(CSV_PATH):
        return
    data = [
        {"subject": "Math", "topic": "Linear Equations", "difficulty": "easy",
         "sample_quiz_question": "Solve for x: 2x + 4 = 10"},
        {"subject": "Math", "topic": "Fractions", "difficulty": "easy",
         "sample_quiz_question": "What is 3/4 + 1/2?"},
        {"subject": "Math", "topic": "Percentages", "difficulty": "medium",
         "sample_quiz_question": "What is 20% of 150?"},
        {"subject": "Science", "topic": "Photosynthesis", "difficulty": "easy",
         "sample_quiz_question": "Name the gas plants absorb from the air during photosynthesis."},
        {"subject": "Science", "topic": "States of Matter", "difficulty": "easy",
         "sample_quiz_question": "What is it called when a liquid turns into a gas?"},
        {"subject": "Science", "topic": "Newton's Laws", "difficulty": "medium",
         "sample_quiz_question": "According to Newton's first law, what happens to an object at rest with no force acting on it?"},
        {"subject": "English", "topic": "Parts of Speech", "difficulty": "easy",
         "sample_quiz_question": "Identify the verb in this sentence: 'The dog runs fast.'"},
        {"subject": "English", "topic": "Tenses", "difficulty": "medium",
         "sample_quiz_question": "Rewrite this sentence in past tense: 'She walks to school.'"},
        {"subject": "Social Studies", "topic": "Indian Independence", "difficulty": "easy",
         "sample_quiz_question": "In which year did India gain independence?"},
        {"subject": "Social Studies", "topic": "Types of Government", "difficulty": "medium",
         "sample_quiz_question": "Name one difference between a democracy and a monarchy."},
    ]
    pd.DataFrame(data).to_csv(CSV_PATH, index=False)

_ensure_topics_csv()
topics_df = pd.read_csv(CSV_PATH)

def quiz_node(state: AgentState) -> AgentState:
    subject_matches = topics_df[topics_df["subject"].str.lower() == state["subject"].lower()]
    if not subject_matches.empty:
        state["quiz_question"] = subject_matches.sample(1)["sample_quiz_question"].values[0]
    else:
        state["quiz_question"] = "No follow-up question available for this subject yet."
    return state

# ============================================
# BUILD THE GRAPH
# ============================================
graph = StateGraph(AgentState)

graph.add_node("classify", classify_node)
graph.add_node("solve", solve_node)
graph.add_node("verify", verify_node)
graph.add_node("explain", explain_node)
graph.add_node("quiz", quiz_node)

graph.set_entry_point("classify")
graph.add_edge("classify", "solve")
graph.add_edge("solve", "verify")
graph.add_conditional_edges("verify", route_after_verify, {
    "solve": "solve",
    "explain": "explain"
})
graph.add_edge("explain", "quiz")
graph.add_edge("quiz", END)

agent = graph.compile()

# ============================================
# TEST (only runs if this file is executed directly)
# ============================================
if __name__ == "__main__":
    test_questions = [
        {"question": "Solve for x: 2x + 4 = 10", "language": "English"},
        {"question": "Why do plants need sunlight?", "language": "Hindi"},
        {"question": "What is the past tense of 'run'?", "language": "English"},
        {"question": "In which year did India gain independence?", "language": "Tamil"},
    ]

    for t in test_questions:
        result = agent.invoke({
            "question": t["question"],
            "language": t["language"],
            "retry_count": 0
        })
        print("Q:", t["question"])
        print("Subject:", result["subject"])
        print("Verified:", result["is_verified"], "| Retries:", result["retry_count"])
        print("Explanation:", result["explanation"][:200], "...")
        print("Quiz:", result.get("quiz_question"))
        print("-" * 60)
