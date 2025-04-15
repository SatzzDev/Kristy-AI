import requests
from pydub import AudioSegment
from pydub.playback import play

url='https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key=APIKEY'
headers={'Content-Type':'application/json'}
data={
 'contents':[{'role':'user','parts':[{'text':'halo, siapa namamu?'}]}],
 'generationConfig':{
  'responseMimeType':'audio/mpeg',
  'textToSpeechConfig':{
   'voice':{'name':'en-US-Wavenet-F'},
   'audioEncoding':'MP3'
  }
 }
}
res=requests.post(url,json=data,headers=headers)
with open('output.mp3','wb') as f:f.write(res.content)

audio=AudioSegment.from_mp3('output.mp3')
play(audio)
