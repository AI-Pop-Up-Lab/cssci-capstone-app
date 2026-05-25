from ast import literal_eval
from pathlib import Path
import os
import random
import pandas as pd


def _questions_path() -> Path:
    """
    Resolve questions.csv.
    Can be overridden with QUESTIONS_PATH env var.
    Default: backend_root/country_data/questions.csv
    """
    override = os.getenv("QUESTIONS_PATH")
    if override:
        return Path(override)
    # __file__ = data_generation/panel/survey.py
    # parents[0] = data_generation/panel/
    # parents[1] = data_generation/
    # parents[2] = backend root
    return Path(__file__).resolve().parents[2] / "country_data" / "questions.csv"


def generate_question(question_id: str, initial: bool) -> str:
    questions_df = pd.read_csv(_questions_path())
    question_rows = questions_df[questions_df["id"] == question_id]

    if question_rows.empty:
        raise ValueError(f"Unknown question id: {question_id}")

    question_row = question_rows.iloc[0]
    question = question_row["question"]
    options = literal_eval(question_row["options"])
    random.shuffle(options)

    formatted_options = "\n".join(
        f"{i + 1}. {opt}" for i, opt in enumerate(options)
    )

    if not initial:
        return (
            f"{question}\n"
            "I will now repeat the question. Consider all your previous thought processes "
            "and potentially any additional context. These might have changed your mind, or not. "
            "The options are below. Only respond with the exact format of the option you choose, "
            "do not include any other text. Do not include the number of the response. "
            "You must include a response. Do not include any styling for the response (e.g. bold). "
            "In this final response, consider all previous chats, as well as any additional context "
            "that has been provided.\n"
            f"{formatted_options}"
        )

    return (
        f"{question}\n"
        "The options are below. Do not provide an answer right now. Interpret the question, "
        "provide your reasoning in understanding what is meant by the question and what kind of "
        "information you need to answer this. Fully embody the person you are representing. "
        "You may be provided with more information later. Consider what options you are seriously "
        "thinking about, which ones you might be immediately discarding, what it would take to "
        "swing your mind one way or another. This should be in the range of 300-600 words. "
        "Express the thoughts in the first person. The options are:\n"
        f"{formatted_options}"
    )