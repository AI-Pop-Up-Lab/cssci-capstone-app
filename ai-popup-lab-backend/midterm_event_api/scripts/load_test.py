"""
Simulate many visitors chatting at the same time against a RUNNING API, to check that the
server and the Azure model quota keep up. Uses the real model: 150 visitors x 3 messages is
450 model calls, so it costs money. Start small.

Run from the ai-popup-lab-backend folder, with the API running (uvicorn main:app):

    python -m midterm_event_api.scripts.load_test --visitors 10 --messages 2
    python -m midterm_event_api.scripts.load_test --url https://<api-host> --visitors 150 --messages 3

Each simulated visitor gets a persona from /match, then sends its messages one after another,
like a person would. Prints how long replies took and how many failed. If many fail with
errors, the Azure deployment's tokens-per-minute quota is the first thing to check.
"""

import argparse
import asyncio
import json
import random
import statistics
import time

import httpx

QUESTIONS = [
    "Hi! How are you voting this year?",
    "What issue matters most to you?",
    "What do you think of the two parties?",
    "Are you nervous about tonight?",
    "What would change your mind?",
]


async def send(client: httpx.AsyncClient, url: str, persona_id: str, message: str, history: list):
    started = time.monotonic()
    body = {"persona_id": persona_id, "message": message, "chat_history": history}
    text, failed = "", False
    async with client.stream("POST", f"{url}/api/midterm_event/chat", json=body) as response:
        if response.status_code != 200:
            return time.monotonic() - started, True, f"HTTP {response.status_code}"
        event = "message"
        async for line in response.aiter_lines():
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: ") and line != "data: [DONE]":
                piece = json.loads(line[len("data: "):])["text"]
                if event == "error":
                    failed, text = True, piece
                else:
                    text += piece
                event = "message"
    return time.monotonic() - started, failed, text


async def visitor(client, url, messages, results):
    response = await client.get(f"{url}/api/midterm_event/match")
    persona_id = response.json()["persona"]["id"]
    history = []
    for question in random.sample(QUESTIONS, k=min(messages, len(QUESTIONS))):
        seconds, failed, reply = await send(client, url, persona_id, question, history)
        results.append((seconds, failed, reply))
        history += [{"role": "user", "content": question}, {"role": "assistant", "content": reply}]


async def run(url, visitors, messages):
    results = []
    async with httpx.AsyncClient(timeout=120) as client:
        started = time.monotonic()
        await asyncio.gather(*(visitor(client, url, messages, results) for _ in range(visitors)))
        total = time.monotonic() - started

    times = sorted(seconds for seconds, failed, _ in results if not failed)
    failures = [reply for _, failed, reply in results if failed]
    print(f"{len(results)} messages from {visitors} visitors in {total:.1f}s")
    if times:
        p95 = times[min(len(times) - 1, int(len(times) * 0.95))]
        print(f"reply time: median {statistics.median(times):.1f}s, 95th percentile {p95:.1f}s, max {times[-1]:.1f}s")
    print(f"failed: {len(failures)}")
    for reply in sorted(set(failures))[:5]:
        print(f"  e.g. {reply}")


def main():
    parser = argparse.ArgumentParser(description="Load test the midterm event chat API.")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--visitors", type=int, default=10)
    parser.add_argument("--messages", type=int, default=2, help="messages per visitor (max 5)")
    args = parser.parse_args()
    asyncio.run(run(args.url.rstrip("/"), args.visitors, args.messages))


if __name__ == "__main__":
    main()
