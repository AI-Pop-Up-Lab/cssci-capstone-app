import time
import pandas as pd
from pathlib import Path

from .chat import send_message

try:
    from tqdm import tqdm
except Exception:
    def tqdm(iterable, total=None):
        return iterable

def populate_panel(panel, country, delay_seconds: float = 1.0, checkpoint_path: str = 'data/panels/sweden_panel_active.csv'):
    # input: pd dataframe; output: pd dataframe
    # each panelist contains columns: age, gender, municipality, education_level
    # this function populates each panelist with a generated biography
    # it does so by calling the chat function and prompting it to generate a biography based on the panelist's characteristics
    # If a row already has a biography, skip it (allows resuming after timeout)
    iter_with_progress = tqdm(panel.iterrows(), total=len(panel))

    for index, row in iter_with_progress:
        # Skip rows that already have a biography (resume checkpoint)
        if pd.notna(row.get('biography')):
            continue

        prompt = f"""You are a synthetic persona in a synthetic survey panel. You live in {country}. You have the following demographic characteristics: \n
        Age: {row['age']}\n
        Gender: {row['gender']}\n
        Municipality: {row['municipality']}\n
        Education Level: {row['education_level']}\n
        Past vote: {row['past_vote']}\n

        Please provide a short biography for yourself, in the range of 300-600 words. The biography should be consistent with the demographic characteristics provided, and should provide some additional context about your life, interests, and values. The biography should be written in a way that is engaging and informative, and should provide a sense of who you are as a person. Please do not include any information that is not consistent with the demographic characteristics provided. Write in the first person, and do not include a name. Always write in English. 
        """

        biography = send_message(prompt)
        panel.at[index, 'biography'] = biography

        # Persist each successful row so reruns can resume after timeout/errors.
        panel.to_csv(checkpoint_path, index=False)
        
        # Add delay to avoid rate limiting
        time.sleep(delay_seconds)
    return panel


def system_prompt(row):
    return (
        f"You are a synthetic persona in a synthetic survey panel. Your demographic characteristics are: \n"
        f"Age: {row['age']}\n"
        f"Gender: {row['gender']}\n"
        f"Municipality: {row['municipality']}\n"
        f"Education Level: {row['education_level']}\n"
        f"Past vote: {row['past_vote']}\n"
        f"Only ever respond with information that is consistent with these characteristics. Always write in English and the first person. ALWAYS respond exactly as your persona, talking in the style that it would, unless asked to respond in a very specific format."
        f"Consider how political you are as a person, and that your party identity might not be entirely fixed."
        f"Below is a biography that you have previously written for yourself. This is a fixed part of your identity, and should be consistent with your demographic characteristics. It should provide a sense of who you are as a person, your life, interests, and values. \n"
    )
