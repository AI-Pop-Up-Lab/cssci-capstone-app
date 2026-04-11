"""LLM-backed biography generation for synthetic personas."""

import os
import random

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# =============================================================================
# Prompt Definition
# =============================================================================

BIO_SYS_PROMPT = (
    "You generate rich, realistic biographies for synthetic voters used in social and political simulations.\n\n"
    "Rules:\n"
    "- Write in the first person.\n"
    "- The biography must include specific, concrete personal details that meaningfully constrain the persona. It will be in two parts, a general personal one and a political one. The first part is below.\n"
    "- Avoid vague statements.\n"
    "- You may invent personal details such as occupation, family situation, daily routines, interests and personal values.\n"
    "- Invented details must be plausible given the demographic information.\n"
    "- Avoid stereotypes, clichés, or generic personality traits.\n"
    "- Avoid political slogans or explicit ideological language.\n"
    "- Keep the tone natural and human.\n"
    "- The biography should feel like something a real person might write in a short personal profile.\n"
    "- Do not mention being an AI or a synthetic persona.\n"
    "- Length: 150-200 words.\n"
    "The second part, the political one, is below. \n"
    "- Write in the first person.\n"
    "- This is PART 2 of a biography.\n"
    "- You are given the full neutral biography (PART 1) as context.\n"
    "- Do NOT repeat, summarize, or paraphrase the neutral biography.\n"
    "- Do NOT restate demographic, occupational, or family details.\n"
    "- Use the neutral biography ONLY to ground political attitudes in lived experience.\n"
    "- Focus on political views, priorities, reasoning, and voting behavior.\n"
    "- Explain how experiences shape opinions, not abstract ideology.\n"
    "- Avoid slogans, campaign language, or activist rhetoric.\n"
    "- Keep the tone reflective, pragmatic, and personal.\n"
    "- Do not mention being an AI or a synthetic persona.\n"
    "- State the party you voted for."
    "- Length: 120-180 words.\n"
    "- Do not mention anything about being an AI or persona. Speak directly as yourself.\n"
    "In total, both together should be roughly 300-400 words."
)


AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")
AZURE_OPENAI_BASE_URL = os.getenv("AZURE_OPENAI_BASE_URL")


# =============================================================================
# Prompt Construction
# =============================================================================

def generate_bio_prompt(age_group, gender, vote_2030, education, municipality, country):
    """Build the user prompt used to generate a single persona biography."""
    age = random.randint(int(age_group.split("-")[0]), int(age_group.split("-")[1]))
    if age < 18:
        age = 18
    return (
        f"You are a {age} year old {gender}. You have a {education} education and live in "
        f"{municipality}, in the country {country}. If the 2030 Dutch general election "
        f"(the next general election) were held today, you will vote for {vote_2030}. "
        f"Thus your (intended vote is) {vote_2030}\n\nWrite a detailed biography of "
        "yourself following the rules above."
    )


# =============================================================================
# Model Invocation
# =============================================================================

def get_ai_response(messages, json_mode=False):
    """Request a non-streaming biography completion from the configured model."""
    client = OpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        base_url=AZURE_OPENAI_BASE_URL,
    )
    format_type = {"type": "json_object"} if json_mode else None
    response = client.chat.completions.create(
        model=AZURE_OPENAI_MODEL,
        messages=messages,
        response_format=format_type,
        temperature=0.67,
    )
    return response.choices[0].message.content


# =============================================================================
# Public Engine Entry Point
# =============================================================================

def generate_biography(age_group, gender, vote_2030, education, municipality, country):
    """Generate a biography string from demographic and voting attributes."""
    prompt = generate_bio_prompt(age_group, gender, vote_2030, education, municipality, country)
    messages = [
        {"role": "system", "content": BIO_SYS_PROMPT},
        {"role": "user", "content": prompt},
    ]
    return get_ai_response(messages)
