import asyncio, os, wave, speech_recognition as sr, requests, io
from pydub import AudioSegment
from pydub.playback import play
from yt_dlp import YoutubeDL
import time
import sys
import aiohttp
import json
import datetime
sessions = []



def clear_console(): os.system('cls' if os.name == 'nt' else 'clear')
def print_ascii_art(): print(f"\033[1;32m{r''' ______ __      _____       _____         
___  //_/_________(_)________  /_____  __
__  ,<  __  ___/_  /__  ___/  __/_  / / /
_  /| | _  /   _  / _(__  )/ /_ _  /_/ / 
/_/ |_| /_/    /_/  /____/ \__/ _\__, /  
                                     /____/   '''}\033[0m")
def loading_animation(message="Loading", end_message="Done!"):
 for i in range(4): sys.stdout.write(f"\r{message} {'.' * (i % 4)}   "); sys.stdout.flush(); time.sleep(0.5)
 sys.stdout.write(f"\r{end_message}   \n"); sys.stdout.flush()

def set_timer(duration): loading_animation("Setting timer", "Timer started!"); print(f"⏳  Timer started for {duration} seconds..."); time.sleep(duration); say("Time's up!")
def set_reminder(time_str):
 try:
  reminder_time = time.strptime(time_str, "%H:%M")
  current_time = time.localtime()
  reminder_seconds = time.mktime(reminder_time) - time.mktime(current_time)
  if reminder_seconds < 0: print("❌  Please enter a future time!")
  else: loading_animation("Setting reminder", "Reminder set!"); print(f"⏰  Reminder set for {time_str}"); time.sleep(reminder_seconds); say(f"Reminder: It's time for your scheduled event at {time_str}!")
 except Exception as e: print("❌  Error setting reminder:", e)

def say(text):
 try:
  r = requests.post("https://api.sws.speechify.com/v1/audio/stream", json={"input":text,"voice_id":"kristy"}, headers={"Authorization":"Bearer 3daLU0CQEuA8hHu1XM3Kz4xDrxHSTPjiZl7UX1Xlip4=","Content-Type":"application/json"})
  if r.ok: play(AudioSegment.from_file(io.BytesIO(r.content),format="mp3"))
  else: print("❌  speechify failed")
 except Exception as e: print("❌  Error:", e)

def listen():
 r = sr.Recognizer()
 with sr.Microphone() as source:
  r.energy_threshold = 300
  r.pause_threshold = 1.0
  print("🎙️  Listening...")
  audio = r.listen(source)
 try: return r.recognize_google(audio, language="en-US").lower()
 except: return ""

async def ask(q):
 try:
  sessions.append({"role":"user","parts":[{"text":q}]})
  system_instruction={"role":"user","parts":[{"text":f"Kristy, an AI assistant. Respond clearly, helpfully, and professionally. Be concise, informative, and assist SatzzDev."}]}
  url="https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key=AIzaSyAobbUUggorIsYzVkp9Dt26ud0CvghVFPU"
  data={"contents":sessions,"systemInstruction":system_instruction}
  async with aiohttp.ClientSession() as session:
   async with session.post(url,json=data,headers={'Content-Type':'application/json'}) as r:
    if r.status==200:
     response_data=await r.json()
     reply_text=response_data['candidates'][0]['content']['parts'][0]['text']
     sessions.append({"role":"assistant","parts":[{"text":reply_text}]})
     print(f"Kristy: {reply_text}")
     say(reply_text)
    else:
     print(f"Failed to fetch from Gemini API. Status: {r.status}")
     say("I don't understand")
 except Exception as e:
  print(f"❌ Error: {e}")

def get_mp3(url):
 try:
  r = requests.get(f"https://kaiz-apis.gleeze.com/api/ytdown-mp3?url={url}")
  if r.ok:
   data = r.json()
   audio_url = data.get('download_url')
   if audio_url:
    print("🎵 Song found from Kaiz API, playing..."); audio = AudioSegment.from_file(io.BytesIO(requests.get(audio_url).content), format="mp3"); play(audio)
   else: raise Exception("No download URL found in Kaiz response")
  else: raise Exception("Failed to fetch from Kaiz API")
 except Exception as e:
  print(f"❌ Kaiz API failed: {e}, trying Kaiz API v2...")
  try:
   r = requests.get(f"https://kaiz-apis.gleeze.com/api/ytmp3?url={url}")
   if r.ok:
    data = r.json()
    audio_url = data.get('download_url')
    if audio_url:
     print("🎵 Song found from Kaiz API v2, playing..."); audio = AudioSegment.from_file(io.BytesIO(requests.get(audio_url).content), format="mp3"); play(audio)
    else: raise Exception("No download URL found in Kaiz API v2 response")
   else: raise Exception("Failed to fetch from Kaiz API v2")
  except Exception as e:
   print(f"❌ Kaiz API v2 failed: {e}, trying Mypy API...")
   try:
    r = requests.get(f"https://mypyapi.up.railway.app/yt?url={url}")
    if r.ok: audio = AudioSegment.from_file(io.BytesIO(r.content), format="mp3"); play(audio)
    else: print("❌ Failed to fetch from Mypy API")
   except Exception as e: print(f"❌ Mypy API failed: {e}")

def ytplay(q):
 if q and "play" in q:
  say("Just a moment, I'm fetching the song"); loading_animation("Fetching song", "Song ready!")
  try:
   ydl_opts = {'format': 'bestaudio', 'quiet': True, 'outtmpl': os.devnull}
   with YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(f"ytsearch:{q}", download=False)['entries'][0]
    t = info['title']
    url = info['webpage_url']
    say(f"I'm going to play a song titled {t}")
    get_mp3(url)
  except Exception as e: print("❌ Error during YouTube search:", e)

def speaks(text): print(text); say(text)
def get_greeting():
    now = datetime.datetime.now()
    hour = now.hour
    day_of_week = now.strftime("%A")  # Nama hari dalam bahasa Inggris
    current_date = now.strftime("%B %d, %Y")  # Format: April 15, 2025

    # Tentukan sapaan berdasarkan jam
    if 5 <= hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 18:
        greeting = "Good afternoon"
    elif 18 <= hour < 22:
        greeting = "Good evening"
    else:
        greeting = "Good night"

    speaks(f"{greeting} SatzzDev, Iam Kristy, Your Personal Assistant. How can I assist you today in {day_of_week}, {current_date}?")
if __name__ == "__main__":
 clear_console(); print_ascii_art(); get_greeting()
 while True:
  command = listen(); print(command)
  if "exit" in command: break
  elif "play" in command: ytplay(command)
  elif "reminder" in command: 
   say("Please say the time for your reminder in HH:MM format.")
   reminder_time = listen(); set_reminder(reminder_time)
  elif "timer" in command:
   say("Please say the number of seconds for the timer.")
   timer_duration = listen()
   if timer_duration.isdigit(): set_timer(int(timer_duration))
   else: say("❌ Please provide a valid number of seconds.")
  elif command: asyncio.run(ask(command))
