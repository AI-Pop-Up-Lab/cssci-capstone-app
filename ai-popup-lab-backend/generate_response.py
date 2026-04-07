import random
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv() 

RESPONSE_SYS_PROMPT = (
    "You are a synthetic persona designed to explain the rationale behind voter choices. You will be given a biography about your persona. Users will ask you questions about your political behaviour, and you will respond as the persona, referencing your biography if suitable.\n" 
    "- Fully embody the persona in the biography. \n"
    "- Do NOT contradict details present in your biography. \n"
    "- DO NOT include markdown in your response (e.g. no bold messages). \n"
    "- Try not to respond in long paragraphs unless absolutely necessary, respond as though you are engaging in casual conversation, thus do not respond in long paragraphs. \n"
    "- If the chat is not related to your political behaviour whatsoever, respond that you can't help the user with that. If the topic is tangentially related, then either respond in a way that is related to your political behaviour, or suggest an alternative question to ask, try to be more lenient than not.\n"
    "- If the user asks you a question about a characteristic of yours which is not in your biography, do NOT respond as if their statement is true (e.g. asking why you voted for party A, if you actually voted for party B).\n"
    "- Stick only with the vote that is in your persona. Do not invent another vote, or contradict it.\n"
    "- If the user greets you, greet them and ask what they would like to ask.\n"
    "- Always respond in English.\n"
    "Your biography is:"
)


AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")
AZURE_OPENAI_BASE_URL = os.getenv("AZURE_OPENAI_BASE_URL")
print(AZURE_OPENAI_BASE_URL)


def get_AI_response(messages,  json_mode=False):
    client = OpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    base_url=AZURE_OPENAI_BASE_URL
    )

    format_type = {"type": "json_object"} if json_mode else None

    response = client.chat.completions.create(
        model=AZURE_OPENAI_MODEL,
        messages=messages,
        response_format=format_type,
        temperature=0.67,
        stream=True
    )
    
    for chunk in response:
        if not chunk.choices:  # ← skip empty chunks
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content

def create_system_prompt(biography):
    return f'{RESPONSE_SYS_PROMPT}\n{biography}'

def generate_response(persona_biography, user_message, chat_history):

    sys_prompt = create_system_prompt(persona_biography)

    messages = [
        {"role":"system", "content":sys_prompt},
        *chat_history,
        {"role":"user","content":user_message}
        ]
    return get_AI_response(messages)