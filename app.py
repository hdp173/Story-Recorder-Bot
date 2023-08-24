from pydantic import BaseModel
from fastapi import FastAPI, Request, Form, Response
from typing import Optional
from twilio.twiml.voice_response import VoiceResponse, Gather
from fastapi.responses import PlainTextResponse
import json
import uvicorn
import openai
import os
import random
from dotenv import load_dotenv
import urllib.request
import asyncio

load_dotenv()

app = FastAPI()
openai.api_key = os.getenv("OPENAI_API_KEY")

def full_url(url):
    return "http://95.164.44.248:8000" + url


async def transcribe(recording_url):
    hash = str(random.getrandbits(32))
    try:
        urllib.request.urlretrieve(recording_url, hash + ".wav")
    except:
        return None

    audio_file = open(hash + ".wav", "rb")
    transcript = await openai.Audio.atranscribe("whisper-1", audio_file)

    os.remove(hash + ".wav")
    return transcript


@app.get("/greeting")
def handle_transcription(request: Request):
    _to = request.query_params.get("To")

    with open(f"./data/{_to}_question.json", "w") as f:
        f.write(json.dumps([
            "Please tell me who is involved in the story and their ages at the time.",
            "Please tell me what the setting of the story is and any descriptions that help set the mood.",
            "Okay, start from the beginning. What happened in the story?",
            "How did everyone feel after this?",
            "Did anyone take away any lessons from this?",
            "What was the funniest part of the story?",
            "",
            "",
            "",
            ""
        ]))

    with open(f"./data/{_to}_answer.json", "w") as f:
        f.write(json.dumps([""] * 10))
    response = VoiceResponse()
    response.say("Hello! Thank you for answering a call. Will you let me know if you're ready to record story for us?")
    # response.redirect(url="/test", method="GET")
    gather = Gather(action='/greeting-gather',
                    method='GET', numDigits=1, timeout=30)
    gather.say("If you're ready, please press 1 and otherwise, press other keys")
    response.append(gather)
    return Response(content=str(response), media_type="application/xml")


@app.get("/test")
def test(request: Request):
    print(request.query_params.get("To"))


@app.get("/greeting-gather")
def greeting_gather(request: Request):
    print(request.query_params.get("To"))
    Digits = request.query_params.get("Digits")
    if Digits == "1":
        response = VoiceResponse()
        response.say("I'm the Story Quilt bot and I'm here to record a story. I'll ask you ten questions about the story and record your answers. After you tell me the story I'll see if I understand what you told me and ask some clarifying questions. Okay, let's get started.")
        response.redirect("/question/0", method='GET')
        return Response(content=str(response), media_type="application/xml")
    else:
        response = VoiceResponse()
        response.say("Thank you. Please have a nice day.")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")


@app.get("/question/{questionIndex}")
def question(request: Request, questionIndex: int):
    _to = request.query_params.get("To")
    with open(f"./data/{_to}_question.json", "r") as f:
        questions = json.loads(f.read())

    response = VoiceResponse()
    response.say(questions[questionIndex])
    response.record(action=f"/recording/{questionIndex}",
                    questionIndex=questionIndex, finish_on_key="*", method="GET")
    return Response(content=str(response), media_type="application/xml")


async def save_transcribe_into_file(number: str, url: str, index: int):
    transcript = await transcribe(url)
    with open(f"./data/{number}_answer.json", "r") as f:
        answers = json.loads(f.read())
    answers[index] = transcript
    with open(f"./data/{number}_answer.json", "w") as f:
        f.write(json.dumps(answers))


@app.get("/recording/{questionIndex}")
async def recording(request: Request, questionIndex: int):
    _to = request.query_params.get("To")
    url = request.query_params.get("RecordingUrl")
    asyncio.create_task(save_transcribe_into_file(_to, url, questionIndex))
    response = VoiceResponse()
    if questionIndex < 2:
        response.say("Thank you for your answer. And here's my next question.")
        response.redirect(f"/question/{questionIndex + 1}", method="GET")
    else:
        response.say("Thank you for your help. Have a nice day!")
        response.hangup()
    return Response(content=str(response), media_type="application/xml")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
