from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
from dotenv import load_dotenv
import openai
import os
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

questions_db: Dict[int, Dict[str, str]] = {
    1: {
        "question": "สัดส่วนลูกค้า male มีกี่เปอร์เซ็น",
        "correct_sql": """with count_gender as(
                        select cast(count(customer_id)as float) as total_customer from banking.customer
                        where gender in ('Male', 'Female')
                        )
                        select cast(count(customer_id)/total_customer * 100 as float) as percent_male from banking.customer
                        cross join count_gender
                        where gender = 'Male'
                        group by total_customer"""
    },
    2: {
        "question": "จำนวนเงินรวมของ female มีค่าเท่าไหร่",
        "correct_sql": "select sum(balance) from banking.customer where gender = 'Female'"
    },
    3: {
        "question": "หาจำนวนลูกค้า ที่เป็น female, blue collar",
        "correct_sql": "select count(distinct customer_id) from banking.customer where gender = 'Female' and job_classification = 'Blue Collar'"
    },
    4: {
        "question": "หาจำนวนเงินของลูกค้า อาชีพ other ที่อยู่ใน england",
        "correct_sql": "select sum(balance) from banking.customer where job_classification = 'Other' and region = 'England'"
    },
    5: {
        "question": "หาจำนวนลูกค้า ที่เป็น female และอยู่ใน Northern Ireland ที่มีอายุ >= 20 and < 30",
        "correct_sql": """select count(distinct customer_id) from banking.customer
                        where gender = 'Female' and region = 'Northern Ireland'
                        and age >= 20 and age < 30"""
    },
}

class SQLRequest(BaseModel):
    question_id: int
    user_sql: str    

@app.get("/")
async def root():
    return {"message": "Server is running!"}

def validate_with_openai(question: str, user_sql: str, model="gpt-4o-mini"):

    prompt = f"""
    You are an SQL script validator. Your job is to check if the SQL script provided by the user is correct based on the given question. 

    Question: {question}
    User SQL Script: {user_sql}

    1. If the SQL script is correct, respond: "Correct: Your SQL script is valid."
    2. If the SQL script is incorrect, explain why and provide hints to fix it.
    3. Provide a score out of 10 based on the script's accuracy.

    Respond in this JSON format:
    {{
        "result": "Correct" or "Incorrect",
        "feedback": "Detailed explanation or hints to fix errors.",
        "score": "X/10"
    }}
    """
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system",
            "content": "You are academic professor assistant of university in Thailand who have responsibility to improve student learning experience."},
            {"role": "user", 
            "content": prompt},
        ],
        temperature=0.2,
        max_tokens=4096,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
    )
    return response.choices[0].message.content

# ตรวจคำตอบ
@app.post("/api/validate_sql")
async def validate_sql(data: SQLRequest):

    question = questions_db.get(data.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    openai_result = validate_with_openai(question["question"], data.user_sql)

    return {"response": openai_result}

# เอาไว้เช็คว่ามี question อะไรบ้าง
@app.get("/api/questions")
async def get_questions():
    return {
        "questions": [
            {"id": q_id, "question": q_data["question"]}
            for q_id, q_data in questions_db.items()
        ]
    }

allowed_origins = os.getenv("ALLOW_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # URL ของ Frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)