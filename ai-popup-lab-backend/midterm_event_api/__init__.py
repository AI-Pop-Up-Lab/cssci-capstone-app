"""
Persona chat API for the AI Pop-Up Lab's US midterms election-night event (3 November 2026).

Visitors pick demographic attributes, get matched to one of ~1000 pre-written personas
(markdown files in `personas/`), and chat with it. See README.md in this folder for how
it works and PERSONA_GUIDE.md for how to write persona files.

This package is separate from the older `_persona_chat` package and does not import it.
The HTTP routes live in `api_endpoints/midterm_event_endpoints.py`.
"""
