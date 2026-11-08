# Whisper Free

A free and open-source Windows voice-dictation app written in Python. It records from your microphone, transcribes locally with `faster-whisper`, copies the result, and can paste it into the active app.

> Independent project inspired by modern voice-dictation workflows. Not affiliated with Wispr Flow or Whisper Flow.

## Features

- Offline/local transcription after the speech model is downloaded
- Danish plus many other Whisper-supported languages
- Automatic language detection
- Global push-to-toggle hotkey: `Ctrl+Shift+Space`
- Automatic punctuation from Whisper
- Optional filler-word cleanup
- Automatic copy and paste into the active app
- Model choices from `tiny` through `large-v3`
- Dark/light system theme
- Windows EXE built automatically by GitHub Actions

## Download the EXE

1. Open **Releases** on the right side of this repository.
2. Open **Whisper Free latest build**.
3. Download `WhisperFree.exe`.

The first transcription downloads the selected speech model. The default `small` model is a good balance for Danish. Models are cached for later use.

## Run from source

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## Build locally

```powershell
pip install pyinstaller
pyinstaller --clean --noconfirm WhisperFree.spec
```

The EXE will be in `dist/WhisperFree.exe`.

## Privacy and cost

The app has no paid API and no account requirement. Transcription runs on your computer. Internet access is needed only to download a model the first time.

## License

MIT
