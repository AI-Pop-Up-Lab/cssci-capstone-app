---
# HOW TO USE THIS TEMPLATE
# 1. Copy this file and rename the copy, e.g. us_0042.md. The filename (without .md) is the persona's ID.
#    Files starting with "_" (like this one) are ignored by the API.
# 2. Set the five attributes below. Each must be one of the listed values (capitalisation doesn't matter).
# 3. Replace the profile text under the second "---" line.
# 4. Check your files: python -m midterm_event_api.validate_personas
# Lines starting with "#" up here are comments and are ignored. Full guide: PERSONA_GUIDE.md

gender: Female        # Female | Male
age_group: 43-47      # 18-22 | 23-27 | 28-32 | 33-37 | 38-42 | 43-47 | 48-52 | 53-57 | 58-62 | 63-67 | 68-72 | 73-77 | 78-82 | 83+
education: Post-grad  # No HS | HS grad | Some college | 2-year | 4-year | Post-grad
state: FL             # two-letter code (FL) or full name (Florida)
race: White           # Asian | Black | Hispanic | Native American | Other/Multi | White

# Optional: the name shown in the chat header. If left out, "us_0042.md" is shown as "Persona 42".
# display_name: Persona 42

# Optional: any other "key: value" lines (e.g. vote_2026: Democrat) are passed to the frontend
# as-is, but are NOT used for matching and are NOT sent to the model. If the model should know
# something, put it in the profile text below.
---
<!--
Write the profile in the second person ("You are...", "You grew up..."), roughly 150-400 words.
Everything below the second "---" line is sent to the model with every message, except text
inside comment markers like these, which is removed. The headings are a suggestion, not required.
-->

## Background

You are ... (age, where you live, work, family, religion, how you spend your time)

## Politics and this election

(party identification, how you voted before, how you are voting or voted in this midterm and why, the issues you care about most, what you think of the parties)

## How you talk

(tone, vocabulary, humour, how much you know about politics, phrases you tend to use)
