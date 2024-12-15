from dotenv import load_dotenv
import os
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
print(os.getenv("OPENAI_API_KEY"))

def get_response(prompt, model="gpt-4o-mini"):
    response = openai.ChatCompletion.create(
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