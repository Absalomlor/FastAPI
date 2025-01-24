from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import json

load_dotenv()
client = OpenAI()

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

def validate_with_openai(question: str, user_sql: str, correct_sql: str, model="gpt-4o-mini"):
    prompt = f'''
    Question: {question}
    User SQL: {user_sql}
    Example Correct SQL: {correct_sql}

    Instruction:
    You are a professor with years of experience reviewing SQL scripts. Your task is to provide detailed Feedback, Hints, and an accurate Score after evaluating the SQL script submitted by a student.
    
    Requirements:
    - Evaluate the SQL script based on correctness of column selection, use of commands, and alignment with the problem requirements.
    - Ensure the script is syntactically correct and logically complete.
    - If the script contains **critical syntax errors that prevent execution, provide a score of 0 in relevant sections and include hints on how to fix them.
    - Check the efficiency of the script, such as avoiding unnecessary operations or including optimizations.
    - Differentiate between minor mistakes and major errors:
    - Minor mistakes (e.g., missing alias) should lead to partial score deductions.
    - Major errors (e.g., using the wrong table or incorrect JOIN type) should significantly lower the score.
    - Assign a score from 0 to 1 based on the following detailed scoring criteria.
    - Provide detailed feedback explaining the reasoning behind the score and hints for improvement.

    Scoring Criteria: 
    1. Column Selection & Query Structure (15%)
    - (3%) Column Selection: Are the selected columns correct?  
    - (6%) JOIN & ON Conditions: Are the joins correctly structured?  
    - (6%) Subquery & CTE Usage: Are subqueries/CTEs appropriately used?  

    2. Command Usage & Logic (35%)  
    - (10%) SQL Commands (WHERE, GROUP BY, HAVING, ORDER BY, etc.): Are the commands used correctly?  
    - (15%) Logical Flow: Does the logic of the query match the problem's intent?  
    - (10%) SQL Functions (CASE, COUNT, SUM, AVG, etc.): Are functions used appropriately?  

    3. Correctness (30%)  
    - (15%) Query Output: Does the query return the correct output?  
    - (15%) Data Coverage: Does the query handle all required data conditions?  

    4. Optimization & Best Practices (10%)  
    - (5%) Query Performance: Is the query optimized?  
    - (5%) Code Readability: Is the query formatted clearly and logically?  

    5. Handling Edge Cases (10%)
    - (5%) NULL & Missing Data Handling: Are missing values managed correctly?  
    - (5%) Duplicate & Data Integrity Checks: Are duplicates and inconsistencies handled?  

    Thinking Step-by-Step
    1. Analyze the problem statement and identify the expected output.  
    2. Check the column selection and overall structure of the query.  
    3. Verify SQL commands and logical flow within the script.  
    4. Check for syntax errors and execution feasibility. If the query cannot execute due to syntax issues, provide a score of 0 in relevant sections.  
    5. Ensure correctness by comparing the result with the expected output. If necessary, simulate sample data to validate the query logic.  
    6. Evaluate optimization and best practices to check for efficiency.  
    7. Assess handling of edge cases, including NULL values and duplicates.  
    8. Automatically calculate a weighted score based on the criteria above. If a category receives 0, adjust other scores accordingly.  
    9. Provide constructive feedback with step-by-step hints for improvement.   

    Response Format:  
    {{
        "score": "0-1",
        "feedback": {{
            "column_selection": {{
                "score": "0-1",
                "details": "Explain issues with column selection, JOINs, or subqueries."
            }},
            "command_logic": {{
                "score": "0-1",
                "details": "Describe issues with SQL commands or logical errors."
            }},
            "correctness": {{
                "score": "0-1",
                "details": "Explain whether the query produces the correct results."
            }},
            "optimization": {{
                "score": "0-1",
                "details": "Provide feedback on performance and best practices."
            }},
            "handling_edge_cases": {{
                "score": "0-1",
                "details": "Evaluate whether the query properly handles NULL values, duplicates, and missing data."
            }},
        "Final_Comments": "Summarize all Feedback to use to suggest where adjustments or corrections should be made."
        }}
    }}
'''

    response = client.chat.completions.create(
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
    json_response = json.loads(response.choices[0].message.content)
    return json_response

# ตรวจคำตอบ
@app.post("/api/validate_sql")
async def validate_sql(data: SQLRequest):

    question = questions_db.get(data.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    correct_sql = question["correct_sql"]
    openai_result = validate_with_openai(question["question"], data.user_sql, correct_sql)

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