from dotenv import load_dotenv
import os
from openai import OpenAI


load_dotenv()
gpt_model = OpenAI()

def get_response(prompt, model="gpt-4o-mini"):
    response = gpt_model.chat.completions.create(
                  model=model,
                  messages=[
                    {
                      "role": "system",
                      "content": [
                        {
                          "type": "text",
                          "text": "You are academic professor assistant of university in Thailand who have responsibility to improve student learning experience."
                        }
                      ]
                    },
                    {
                      "role": "user",
                      "content": [
                        {
                          "type": "text",
                          "text": prompt
                        }
                      ]
                    },
                  ],
                  temperature=0.2,
                  max_tokens=4096,
                  top_p=0.95,
                  frequency_penalty=0,
                  presence_penalty=0,
                  response_format={
                    "type": "text"
                  }
                )
    generated_text = response.choices[0].message.content
    return generated_text