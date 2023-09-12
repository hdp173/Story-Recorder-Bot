from pydantic import BaseModel
from fastapi import FastAPI, Request, Form, Response
from typing import Optional
from twilio.twiml.voice_response import VoiceResponse, Gather
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
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


@app.get("/make-call/{phoneNumber}")
def make_call(request: Request, phoneNumber: str):
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
    client = Client(account_sid, auth_token)

    call = client.calls.create(
        url=request.base_url + "greeting",
        method="GET",
        to=phoneNumber,
        from_=twilio_number
    )
    print(call.sid)


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
    response.say(
        "Hello! Thank you for answering a call. Will you let me know if you're ready to record story for us?")
    # response.redirect(url="/test", method="GET")
    gather = Gather(action='/greeting-gather',
                    method='GET', numDigits=1, timeout=10)
    gather.say("If you're ready, please press 1 and otherwise, press other keys")
    response.append(gather)
    response.redirect("/finish-without-answer", method='GET')
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
        response.redirect("/finish-without-answer", method='GET')
        return Response(content=str(response), media_type="application/xml")


@app.get("/finish-without-answer")
def finish_without_answer(request: Request):
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
                    questionIndex=questionIndex, finish_on_key="*", method="GET", timeout=10)
    # response.redirect(f"/question/{questionIndex + 1}", method='GET')
    return Response(content=str(response), media_type="application/xml")


async def generate_question(text):
    instructor = """
    You are a Question generator for personal story recording.
    Your role is to generate 4 questions to make the story given by user more clear.
    User will give you base story in question and answer format.
    Given 3 questions and answers are a list of characters with a bit of information about each one, the scene the story takes place in with some details, and the basic story.
    You must generate 4 follow up questions to ask to clarify any areas of the story that are not clear or need more details.
    Questions must not sound like bot generated and must as friendly as possible.
    Just like as if you listen to the user's story and answer questions that arises in your mind to get more clear vision of the story.
    Also, questions must be story specific and not generic questions since you already have a basic story.
    
    *****One thing to note*****
    Here's the list of questions we already asked.
    So don't generate similar questions with these.
    1. Please tell me who is involved in the story and their ages at the time.,
    2. Please tell me what the setting of the story is and any descriptions that help set the mood.,
    3. Okay, start from the beginning. What happened in the story?,
    4. How did everyone feel after this?,
    5. Did anyone take away any lessons from this?,
    6. What was the funniest part of the story?,
    ***************************

    Please follow this format for response.
    These are sample outputs.
    Sample Output 1: 
    ["Can you describe a specific moment in the story that had a significant impact on you or other characters involved?", "What emotions were you or the other characters feeling at different points in the story?", "Were there any challenges or obstacles faced during the events of the story? How were they overcome?", "How did the events of this story change or affect you or the other characters in the long run?"]
    
    Sample Output 2:
    ["Can you describe a specific moment in the story that had a significant impact on you or other characters involved?", "What emotions were you or the other characters feeling at different points in the story?", "Were there any challenges or obstacles faced during the events of the story? How were they overcome?", "How did the events of this story change or affect you or the other characters in the long run?"]
    
    Sample Output 3:
    ["Can you describe a specific moment in the story that had a significant impact on you or other characters involved?", "What emotions were you or the other characters feeling at different points in the story?", "Were there any challenges or obstacles faced during the events of the story? How were they overcome?", "How did the events of this story change or affect you or the other characters in the long run?"]

    """
    print(text)
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instructor},
            {"role": "user", "content": text},
        ]
    )
    questions = json.loads(response.choices[0].message.content)
    print(questions)
    return questions


async def save_transcribe_into_file(number: str, url: str, index: int):
    transcript = await transcribe(url)
    with open(f"./data/{number}_question.json", "r") as f:
        questions = json.loads(f.read())
    with open(f"./data/{number}_answer.json", "r") as f:
        answers = json.loads(f.read())
    answers[index] = transcript["text"]
    with open(f"./data/{number}_answer.json", "w") as f:
        f.write(json.dumps(answers))

    # when get third answer, generate 4 follow up questions
    if index == 2:
        text = ""
        for i in range(0, 3):
            text = text + f"Question {i + 1}: {questions[i]}\n"
            text = text + f"Answer {i + 1}: {answers[i]}\n\n"
        generated_questions = await generate_question(text)
        for i in range(0, 4):
            questions[i + 6] = generated_questions[i]
        with open(f"./data/{number}_question.json", "w") as f:
            f.write(json.dumps(questions))


@app.get("/recording/{questionIndex}")
async def recording(request: Request, questionIndex: int):
    _to = request.query_params.get("To")
    url = request.query_params.get("RecordingUrl")
    asyncio.create_task(save_transcribe_into_file(_to, url, questionIndex))
    response = VoiceResponse()
    if questionIndex < 9:
        response.say("Thank you.")
        response.redirect(f"/question/{questionIndex + 1}", method="GET")
    else:
        response.say("Thank you for your help. Have a nice day!")
        response.hangup()
    return Response(content=str(response), media_type="application/xml")

# asyncio.run(generate_question("""
# Question 1: Please tell me who is involved in the story and their ages at the time.
# Answer 1: The story involves my grandfather, John, who was 70 years old at the time, and myself, who was around 10 years old. We were the main characters of this story.

# Question 2: Please tell me what the setting of the story is and any descriptions that help set the mood.
# Answer 2: The setting of the story is in a small, quiet town in the countryside. It's the kind of place where everyone knows everyone, and life moves at a slower pace. The story took place in the summer, so there's a feeling of warmth, freedom, and a sense of adventure in the air. Our house, a charming old cottage, sat at the edge of a large, serene lake, which was the heart of all our summer activities.

# Question 3: Okay, start from the beginning. What happened in the story?
# Answer 3: It was the summer of 2000. My parents had sent me to live with my grandfather for the holidays. He was a man of few words but had a heart full of stories. One day, we decided to build a small wooden boat. It was my grandfather's idea; he wanted to teach me about patience, hard work, and the rewards that followed. We spent weeks working on that boat, under the hot summer sun, with nothing but the cool lake water to comfort us. Once the boat was ready, we took it for a sail in the lake. That day, just the vast blue sky above, the gentle lapping of the lake against our boat, and the sense of accomplishment in my grandfather's eyes, is a memory that remains etched in my heart. It was a simple story of a boy, his grandfather, a boat, and a summer of lessons and memories.
# """))


# asyncio.run(generate_question("""
# Question 1: Please tell me who is involved in the story and their ages at the time.
# Answer 1: I don't wanna answer this qustion.

# Question 2: Please tell me what the setting of the story is and any descriptions that help set the mood.
# Answer 2: I don't wanna answer this qustion.

# Question 3: Okay, start from the beginning. What happened in the story?
# Answer 3: I don't wanna answer this qustion.
# """))

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8030, reload=True)
