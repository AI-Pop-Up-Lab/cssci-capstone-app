# Writing persona files

This guide is for whoever writes the ~500 personas for the election-night chat. No coding needed:
each persona is one text file.

## In short

1. Copy [`personas/_TEMPLATE.md`](personas/_TEMPLATE.md) and name the copy `us_0001.md`, `us_0002.md`, … `us_0500.md`.
2. At the top, set the persona's five attributes, using exactly the values listed below.
3. Underneath, write the persona's profile: who they are, how they vote and why, how they talk.
4. Run the checker (or ask someone on the API side to run it) and fix anything it reports.
5. Put the files in `ai-popup-lab-backend/midterm_event_api/personas/` and commit them.

`personas/us_0001.md` is a finished sample to copy from. It's a placeholder: overwrite it with your own
persona 1.

## What a file looks like

```markdown
---
gender: Female
age_group: 43-47
education: Post-grad
state: FL
race: White
---

## Background

You are Dana, 45, and you live in a suburb of Tampa, Florida. ...

## Politics and this election

You're registered with no party affiliation. ...

## How you talk

Direct, a dry sense of humour. ...
```

The part between the two `---` lines is the **attributes** (in a format called YAML: one
`name: value` per line). Everything below the second `---` is the **profile**, which is given to the
model as the persona's identity.

The **filename is the persona's ID**: `us_0042.md` is persona `us_0042`, shown in the chat as
"Persona 42". Use only letters, numbers, `_` and `-` in filenames. Files whose name starts with `_`
(like `_TEMPLATE.md`) are ignored.

## The attributes

All five are required. They're what visitors pick from in the dropdowns, and they're used to match
visitors to a persona, so each must be one of these values (the same as the website's US dropdowns).
Capitalisation doesn't matter.

| Attribute | Allowed values |
|---|---|
| `gender` | `Female`, `Male` |
| `age_group` | `18-22`, `23-27`, `28-32`, `33-37`, `38-42`, `43-47`, `48-52`, `53-57`, `58-62`, `63-67`, `68-72`, `73-77`, `78-82`, `83+` |
| `education` | `No HS`, `HS grad`, `Some college`, `2-year`, `4-year`, `Post-grad` |
| `state` | Two-letter code (`FL`) or full name (`Florida`), including `DC` |
| `race` | `Asian`, `Black`, `Hispanic`, `Native American`, `Other/Multi`, `White` |

The age groups are fixed five-year bands: an "age 40-46" persona doesn't exist. Pick the band the
persona's age falls in (a 45-year-old is `43-47`) and put the exact age in the profile.

### Optional extras

- `display_name: Dana`: the name shown in the chat header instead of "Persona 42".
- Any other `name: value` line, e.g. `vote_2026: Democrat` or `religion: None`, is kept and passed to
  the frontend (which could display it), but **it isn't used for matching and isn't seen by the
  model**. If the model should know something, write it in the profile.
- Lines starting with `#` between the `---` lines are comments and are ignored.

## Writing the profile

The profile is pasted into the model's instructions under "Who you are", after the five attributes,
for every message. Some tips:

- **Write in the second person**: "You are…", "You grew up…", "You voted…". It reads as instructions
  to the model.
- **Aim for roughly 150 to 400 words.** The profile is sent with every message, so very long profiles
  make replies slower and more expensive. The checker warns above about 1,000 words.
- **Cover what visitors will ask about:**
  - Background: age, where they live, work, family, religion, daily life.
  - Politics: party identification, past votes, **how they're voting in this midterm and why**, the
    issues they care about, what they think of the parties.
  - Voice: tone, vocabulary, humour, how much they know about politics, how they react to
    disagreement.
- **Be specific and consistent.** The model sticks to what's written and is told not to contradict it.
  Gaps get filled in plausibly but unpredictably.
- **Don't write the general rules.** Things that apply to every persona are already in
  `prompts/base_system.md`, for example: keep replies short, no markdown, it's election night and
  results aren't known yet, no voting logistics, no slurs or hate. To change those for everyone, edit
  that file instead.
- **Don't base a persona on a real, identifiable person.** Opinions about real politicians are fine.
- **Notes to yourself** can go inside `<!-- -->`. They're removed before anything reaches the model:

  ```markdown
  <!-- based on sample row 1834, double-check the 2024 vote -->
  ```

Word, Google Docs and Windows formatting are fine: curly dashes in `43–47` and Windows line endings are
handled. Save files as plain text with the `.md` extension.

## How visitors get matched

A visitor picks values in the dropdowns (any of them can be left on "all") and gets the persona that
matches the most of their choices. If several match equally well, one is picked at random. When
nothing matches exactly, the closest age group and education level win.

With ~500 personas and about 50,000 possible combinations, most combinations won't have an exact match.
So it's worth spreading personas across states, age groups, education levels and races, so every
dropdown choice has at least a few personas. The checker lists any value that has no personas at all.

## Checking your files

From the `ai-popup-lab-backend` folder, with the project's Python environment set up (see
[README.md](README.md#quick-start)):

```bash
python -m midterm_event_api.validate_personas
```

It reports every file with a problem and what's wrong, for example:

```text
PROBLEMS (2 file(s) will be skipped by the API):
  - us_0017.md: '40-46' is not a valid age_group. Allowed values: 18-22, 23-27, ...
  - us_0230.md: missing required attribute(s): education

498 valid persona(s) in .../midterm_event_api/personas
  gender: Female: 251, Male: 247
  ...
  state: AL: 7, AK: 2, ...
    no personas for: DC, WY
```

A file with a problem is skipped by the live API (the rest still work), so make sure this shows
no problems before the files are deployed. `--values` prints the allowed values.

To check how a persona actually sounds, chat with it using the real model (needs the team's `.env`):

```bash
python -m midterm_event_api.scripts.try_chat --persona us_0042
python -m midterm_event_api.scripts.try_chat --persona us_0042 --probe   # tricky test questions
```

## Getting the files live

The personas are part of the API's code: committing them to the branch and merging to `main` deploys
them. Changes after that need another merge to `main`, so leave time before the event.
