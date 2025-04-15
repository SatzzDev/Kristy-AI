# Kristy - Your Personal AI Assistant

Kristy is an AI-powered personal assistant that can help you with various tasks. You can interact with it through voice commands to set timers, reminders, and even play music from YouTube. Kristy responds clearly and concisely to your queries.

## Features
- Voice recognition to listen to commands and queries.
- Text-to-speech functionality to respond to the user.
- Set reminders, timers, and fetch songs from YouTube.
- Uses APIs to process your commands and give real-time feedback.

## Requirements
To run Kristy, make sure you have the following libraries installed:
- `requests`
- `pydub`
- `yt-dlp`
- `speechrecognition`
- `pyaudio`
- `aiohttp`

You can install all dependencies by running:
```bash
pip install -r requirements.txt
```

## Setup
- Clone this repository.
- Install the required dependencies:
```bash
pip install -r requirements.txt
```
- Run the script:
```bash
python assistant.py
```
- Enjoy your personal assistant!

## Usage
- Play music: Say "play" followed by the song name (e.g., "play Shape of You").
- Set a timer: Say "set timer" and specify the number of seconds.
- Set a reminder: Say "set reminder" and specify the time in HH:MM format.
- Exit the assistant: Say "exit".

## Notes
- The assistant uses speech-to-text and text-to-speech to interact with you.
- Make sure you have an active internet connection for the assistant to fetch songs and interact with APIs.
```
Let me know if this works!
```