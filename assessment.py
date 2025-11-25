from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any

app = FastAPI(title="Risk Profile Assessment Service")

GL_SCORING_KEY: Dict[int, Dict[str, int]] = {
    1: {"A": 4, "B": 3, "C": 2, "D": 1},
    2: {"A": 1, "B": 2, "C": 3, "D": 4},
    3: {"A": 1, "B": 2, "C": 3, "D": 4},
    4: {"A": 1, "B": 2, "C": 3},
    5: {"A": 1, "B": 2, "C": 3},
    6: {"A": 1, "B": 2, "C": 3, "D": 4},
    7: {"A": 1, "B": 2, "C": 3, "D": 4},
    8: {"A": 1, "B": 2, "C": 3, "D": 4},
    9: {"A": 1, "B": 3},        
    10: {"A": 1, "B": 3},    
    11: {"A": 1, "B": 2, "C": 3, "D": 4},
    12: {"A": 1, "B": 2, "C": 3, "D": 4},
    13: {"A": 1, "B": 2, "C": 3, "D": 4},
}

BIBIT_ALLOCATIONS: Dict[float, Dict[str, Any]] = {
    1.0: {"profile": "Konservatif", "money_market": 70, "obligation": 20, "stocks": 10},
    1.5: {"profile": "Konservatif", "money_market": 70, "obligation": 20, "stocks": 10},
    2.0: {"profile": "Konservatif", "money_market": 58, "obligation": 32, "stocks": 10},
    2.5: {"profile": "Konservatif", "money_market": 47, "obligation": 43, "stocks": 10},
    3.0: {"profile": "Konservatif", "money_market": 36, "obligation": 54, "stocks": 10},
    3.5: {"profile": "Konservatif", "money_market": 27, "obligation": 62, "stocks": 11},
    4.0: {"profile": "Konservatif", "money_market": 18, "obligation": 69, "stocks": 13},
    4.5: {"profile": "Moderat", "money_market": 12, "obligation": 70, "stocks": 18},
    5.0: {"profile": "Moderat", "money_market": 10, "obligation": 65, "stocks": 25},
    5.5: {"profile": "Moderat", "money_market": 10, "obligation": 59, "stocks": 31},
    6.0: {"profile": "Moderat", "money_market": 10, "obligation": 53, "stocks": 37},
    6.5: {"profile": "Moderat", "money_market": 10, "obligation": 48, "stocks": 42},
    7.0: {"profile": "Moderat", "money_market": 10, "obligation": 43, "stocks": 47},
    7.5: {"profile": "Agresif", "money_market": 10, "obligation": 38, "stocks": 52},
    8.0: {"profile": "Agresif", "money_market": 10, "obligation": 34, "stocks": 56},
    8.5: {"profile": "Agresif", "money_market": 10, "obligation": 29, "stocks": 61},
    9.0: {"profile": "Agresif", "money_market": 10, "obligation": 24, "stocks": 66},
    9.5: {"profile": "Agresif", "money_market": 10, "obligation": 20, "stocks": 70},
    10.0: {"profile": "Agresif", "money_market": 10, "obligation": 20, "stocks": 70},
}

class Answer(BaseModel):
    question: int = Field(..., ge=1, le=13)
    answer: Literal["A", "B", "C", "D"] 

class RiskAssessmentPayload(BaseModel):
    answers: List[Answer] = Field(..., min_length=13, max_length=13)

class AllocationResponse(BaseModel):
    gl_score: float = Field(..., description="Calculated Grable-Lytton Score (0-47)")
    risk_profile_score: float = Field(..., description="Scaled Bibit Score using linear scaling and rounding (1.0-10.0 in 0.5 increments)")
    profile: str = Field(..., description="Risk profile based on Bibit Score (Konservatif, Moderat, Agresif)")
    allocations: Dict[str, float]



def calculate_gl_score(answers: List[Answer]) -> float:
    score = 0
    answered_questions = set()
    
    for item in answers:
        q_num = item.question
        ans = item.answer
   
        if q_num in answered_questions:
            raise HTTPException(status_code=400, detail=f"Question {q_num} answered more than once.")
        answered_questions.add(q_num)

        if q_num not in GL_SCORING_KEY:
            raise HTTPException(status_code=400, detail=f"Invalid question number: {q_num}")
 
        if ans not in GL_SCORING_KEY[q_num]:
             raise HTTPException(status_code=400, detail=f"Invalid answer choice '{ans}' for Question {q_num}. Choices: {list(GL_SCORING_KEY[q_num].keys())}")

        score += GL_SCORING_KEY[q_num][ans]
        
    if len(answered_questions) != 13:
        raise HTTPException(status_code=400, detail="Must provide answers for all 13 unique questions.")
        
    return float(score)

def scale_to_bibit_score(gl_score: float) -> float:
    # Linear Scaling Formula: Y = Y_min + ((X - X_min) * (Y_max - Y_min)) / (X_max - X_min)
    X_min, X_max = 0.0, 47.0
    Y_min, Y_max = 1.0, 10.0

    if gl_score <= X_min:
        return Y_min
    if gl_score >= X_max:
        return Y_max
        
    unrounded_b_score = Y_min + (gl_score * (Y_max - Y_min) / (X_max - X_min))
    
    step = 0.5
    rounded_b_score = round(unrounded_b_score / step) * step

    return max(Y_min, min(Y_max, rounded_b_score))

def get_allocations(bibit_score: float) -> Dict[str, Any]:
    if bibit_score not in BIBIT_ALLOCATIONS:
        raise HTTPException(status_code=500, detail=f"Bibit score {bibit_score} not found in allocation table.")
        
    return BIBIT_ALLOCATIONS[bibit_score]


@app.post("/assess-risk", response_model=AllocationResponse)
async def assess_risk(payload: RiskAssessmentPayload):
    gl_score = calculate_gl_score(payload.answers)

    bibit_score = scale_to_bibit_score(gl_score)
    
    allocation_data = get_allocations(bibit_score)
  
    return AllocationResponse(
        gl_score=gl_score,
        risk_profile_score=bibit_score,
        profile=allocation_data["profile"],
        allocations={
            "money_market": allocation_data["money_market"],
            "obligation": allocation_data["obligation"],
            "stocks": allocation_data["stocks"],
        }
    )