# Story-Recorder-Bot
This is a story recorder bot that calls people with Twilio phone number and ask questions and record answers, and generate questions based on answers up to 10 questions.
You call a number who you want to record story from and our bot will take responsibility of the call completely.

Enjoy it yourself!

# How-To-Run
1. Copy .env.example file and name it as .env.
2. Set values in .env file.
3. Create virtual environment and activate it.
4. Install libraries with ```pip install -r requirements.txt```
5. Run the Twilio webhook server with ```python app.py```
6. Open main.py file and change the server ```url``` and ```to``` value as you want.
   Note: Server must be accessible through the internet.
7. Make a phone call using ```python main.py```
8. Answer a call and follow the guide as the bot says.
