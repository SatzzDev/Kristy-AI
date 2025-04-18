import os
import sys
import logging
import io
import base64
import requests
from typing import Optional
from openai import OpenAI
from pydub import AudioSegment
from pydub.playback import play
import speech_recognition as sr
from tenacity import retry, stop_after_attempt, wait_exponential
from logging_spinner import SpinnerHandler
import configparser
import yt_dlp as youtube_dl
from datetime import datetime

# ========== Custom Exceptions ==========
class YouTubeSearchError(Exception):
    pass

class DownloadAPIError(Exception):
    pass

class AudioPlaybackError(Exception):
    pass

class APIError(Exception):
    pass

# ========== Configuration ==========
class Config:
    def __init__(self, config_path: str = 'config.ini'):
        self._config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        self._config.read(config_path)

    @property
    def api_settings(self) -> dict:
        return {
            'url': self._config.get('API', 'url'),
            'key': self._config.get('API', 'key'),
            'model': self._config.get('API', 'model')
        }

    @property
    def assistant_settings(self) -> dict:
        return {
            'max_history': self._config.getint('Assistant', 'max_history', fallback=10),
            'phrase_timeout': self._config.getint('Assistant', 'phrase_timeout', fallback=5),
            'enable_audio': self._config.getboolean('Assistant', 'enable_audio', fallback=True)
        }

    @property
    def yt_max_results(self) -> int:
        return self._config.getint('YouTube', 'max_results', fallback=5)

# ========== Utilities ==========
class AudioProcessor:
    @staticmethod
    def play_audio(data: bytes) -> None:
        if not data:
            raise AudioPlaybackError("No audio data provided")
        try:
            bio = io.BytesIO(data)
            audio = AudioSegment.from_file(bio).set_frame_rate(44100).set_channels(1)
            play(audio)
        except Exception as e:
            raise AudioPlaybackError(f"Failed to play audio: {str(e)}")

class SpeechRecognizer:
    def __init__(self, phrase_timeout: int = 5):
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.5
        self.phrase_timeout = phrase_timeout

    def listen(self) -> Optional[str]:
        with sr.Microphone() as mic:
            print("\033[90m🔊 Listening...\033[0m")
            try:
                audio = self.recognizer.listen(
                    mic, 
                    timeout=3,
                    phrase_time_limit=self.phrase_timeout
                )
                return self.recognizer.recognize_google(audio, language="id-ID").lower()
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                print("\033[90m❓ Audio unclear\033[0m")
                return None
            except Exception as e:
                logging.error(f"SpeechRecognitionError: {e}")
                return None

# ========== YouTube Handler ==========
class YouTubeHandler:
    def __init__(self, max_results: int = 5):
        self.max_results = max_results

    def search(self, query: str) -> list:
        ydl_opts = {
            'format': 'bestaudio',
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True,
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                result = ydl.extract_info(
                    f'ytsearch{self.max_results}:{query}',
                    download=False
                )
                entries = result.get('entries', [])
                
                valid_results = []
                for entry in entries:
                    if not entry.get('url'):
                        continue
                        
                    duration = entry.get('duration', 0)
                    valid_results.append({
                        'title': entry.get('title', 'Unknown'),
                        'url': entry['url'],
                        'duration': duration
                    })
                
                return valid_results
            except Exception as e:
                raise YouTubeSearchError(f"Search failed: {str(e)}")

    def download_via_api(self, url: str) -> bytes:
        try:
            encoded_url = requests.utils.quote(url)
            endpoints = [
                f"https://web-production-afed4.up.railway.app/yt?url={encoded_url}",
                f"https://mypyapi.up.railway.app/yt?url={encoded_url}"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, timeout=15)
                    if response.status_code == 200 and response.content:
                        return response.content
                except:
                    continue
            
            raise DownloadAPIError("All download endpoints failed")
        except Exception as e:
            raise DownloadAPIError(f"Download error: {str(e)}")

# ========== Conversation Manager ==========
class ConversationManager:
    def __init__(self, max_history: int = 10):
        self.history = []
        self.max_history = max_history

    def add_message(self, role: str, content: str) -> None:
        self.history.append({'role': role, 'content': content})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def get_formatted_history(self, num_messages: int = 5) -> list:
        return self.history[-num_messages:]

# ========== AI Service ==========
class AIService:
    def __init__(self, config: Config):
        if not config.api_settings['key']:
            raise ValueError("API key not configured")
            
        self.client = OpenAI(
            base_url=config.api_settings['url'],
            api_key=config.api_settings['key']
        )
        self.model = config.api_settings['model']

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_response(self, messages: list) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            msg = response.choices[0].message
            audio_data = None
            
            if getattr(msg, 'audio', None) and getattr(msg.audio, 'data', None):
                audio = msg.audio.data
                audio_data = base64.b64decode(audio) if isinstance(audio, str) else audio
            
            return {
                'text': msg.content.strip() if msg.content else '',
                'audio': audio_data
            }
        except Exception as e:
            raise APIError(f"API request failed: {str(e)}")

# ========== Main Assistant ==========
class KristyAI:
    def __init__(self):
        self.config = Config()
        self.convo_mgr = ConversationManager(self.config.assistant_settings['max_history'])
        self.ai_service = AIService(self.config)
        self.yt_handler = YouTubeHandler(self.config.yt_max_results)
        self.speech_recognizer = SpeechRecognizer(self.config.assistant_settings['phrase_timeout'])
        self.audio_processor = AudioProcessor()
        self.current_search_results = []
        self._setup_logging()
        self._init_base_prompt()
        
        self.number_map = {
            'satu': 1, 'pertama': 1, 'one': 1, 'first': 1,
            'dua': 2, 'kedua': 2, 'two': 2, 'second': 2,
            'tiga': 3, 'ketiga': 3, 'three': 3, 'third': 3,
            'empat': 4, 'keempat': 4, 'four': 4, 'fourth': 4,
            'lima': 5, 'kelima': 5, 'five': 5, 'fifth': 5
        }

    def _setup_logging(self):
        self.logger = logging.getLogger('KristyAI')
        self.logger.setLevel(logging.INFO)
        handler = SpinnerHandler()
        handler.setLevel(logging.INFO)
        self.logger.addHandler(handler)

    def _init_base_prompt(self):
        today = datetime.now().strftime("%d %B %Y")
        self.base_prompt = [
            {'role': 'system', 'content': 'Anda adalah asisten AI bernama Kristy'},
            {'role': 'system', 'content': 'Gaya bicara: Gaul Jakarta, friendly, pakai emoji'},
            {'role': 'system', 'content': f'Hari ini tanggal: {today}'}
        ]

    def _speak(self, text: str, with_text: bool = True) -> None:
        if with_text:
            print(f"\n\033[94m🤖 {text}\033[0m")
        try:
            messages = [{
                'role': 'system', 
                'content': 'Bacakan dengan suara jelas dan ekspresif seperti asisten virtual profesional'
            }, {
                'role': 'user',
                'content': f"Bacakan ini dengan intonasi yang tepat: {text}"
            }]
            response = self.ai_service.get_response(messages)
            if response.get('audio'):
                self.audio_processor.play_audio(response['audio'])
        except Exception as e:
            self.logger.error(f"Voice generation error: {str(e)}")

    def start(self):
        self._clear_screen()
        self._speak("Kristy AI - Katakan 'keluar' untuk keluar")
        
        while True:
            try:
                user_input = self._get_input()
                if not user_input:
                    continue
                
                if 'keluar' in user_input:
                    self._speak("Sampai jumpa! 👋")
                    break
                
                response = self._process_input(user_input)
                self._present_response(response)
            
            except KeyboardInterrupt:
                self._handle_shutdown()
            except Exception as e:
                self.logger.error(f"Error: {str(e)}")
                self._speak("🤖 Ada masalah, coba lagi...")

    def _get_input(self) -> Optional[str]:
        return self.speech_recognizer.listen()

    def _process_input(self, user_input: str) -> dict:
        if 'cari lagu' in user_input or 'putar musik' in user_input or 'play':
            return self._handle_music_request(user_input)
        
        self.convo_mgr.add_message('user', user_input)
        messages = self.base_prompt + self.convo_mgr.get_formatted_history()
        response = self.ai_service.get_response(messages)
        self.convo_mgr.add_message('assistant', response['text'])
        return response

    def _handle_music_request(self, query: str) -> dict:
        search_query = query.replace('cari lagu', '').replace('putar musik', '').strip()
        
        try:
            results = self.yt_handler.search(search_query)
            self.current_search_results = results
            
            if not results:
                return {'text': "❌ Gak ketemu lagunya, coba kata kunci lain dong"}
            
            list_items = "\n".join(
                [f"{i+1}. {res['title']} ({res['duration']//60}:{res['duration']%60:02})" 
                 for i, res in enumerate(results)]
            )
            
            return {
                'text': f"🔍 Hasil pencarian '{search_query}':\n{list_items}\n\nSebut nomor lagu (contoh: 'nomor satu')",
                'type': 'music_search'
            }
            
        except YouTubeSearchError as e:
            return {'text': f"❌ Gagal mencari lagu: {str(e)}"}

    def _present_response(self, response: dict):
        if response.get('type') == 'music_search':
            print(f"\n\033[94m🤖 {response['text']}\033[0m")
            self._handle_music_selection()
        else:
            self._speak(response['text'], with_text=self.config.assistant_settings['enable_audio'])

    def _handle_music_selection(self):
        self._speak("🎧 Sebut nomor lagu atau 'batal'", with_text=True)
        
        while True:
            selection = self._get_input()
            if not selection:
                continue
            
            if 'batal' in selection:
                self._speak("❌ Pencarian dibatalkan", with_text=True)
                return
            
            selected_num = None
            for word, num in self.number_map.items():
                if word in selection:
                    selected_num = num
                    break
            
            if not selected_num:
                self._speak("❌ Tidak ada nomor yang dikenali", with_text=True)
                continue
            
            index = selected_num - 1
            if not (0 <= index < len(self.current_search_results)):
                self._speak("❌ Nomor tidak valid", with_text=True)
                continue
            
            selected = self.current_search_results[index]
            self._speak(f"⏳ Memutar lagu nomor {selected_num}, {selected['title']}", with_text=True)
            
            try:
                audio_data = self.yt_handler.download_via_api(selected['url'])
                self.audio_processor.play_audio(audio_data)
                self._speak("✅ Selesai memutar!", with_text=True)
                return
            
            except DownloadAPIError as e:
                self._speak(f"❌ Gagal memutar: {str(e)}", with_text=True)
                if index + 1 < len(self.current_search_results):
                    self._speak("⏳ Mencoba lagu berikutnya...", with_text=True)
                    self.current_search_results.pop(index)
                    continue
                return

    def _clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def _handle_shutdown(self):
        self._speak("Dihentikan oleh pengguna", with_text=True)
        sys.exit(0)

# ========== Main Execution ==========
if __name__ == "__main__":
    try:
        KristyAI().start()
    except Exception as e:
        print(f"🔥 Startup error: {str(e)}")
        sys.exit(1)
