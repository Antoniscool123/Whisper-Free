# Whisper Free quick start (Windows)

## Download the ready-made app

1. Open the repository's **Actions** tab.
2. Select the newest successful **Build Windows EXE** run.
3. Download the **WhisperFree-Windows** artifact.
4. Extract the ZIP and run `WhisperFree.exe`.
5. If Windows SmartScreen appears, choose **More info** and then **Run anyway** only if the file came from this repository's GitHub Actions build.

## First use

1. Allow microphone access when Windows asks.
2. Keep **Dansk** selected, or choose another language.
3. Start with the **small** model for a good speed/quality balance.
4. Click **Start dictation**, speak, then click **Stop and transcribe**.
5. For dictation into another app, put the cursor in the target text box and press `Ctrl+Shift+Space`. Speak, then press the same shortcut again. The app transcribes, copies, and inserts the result.

The first transcription downloads the selected model. Later transcriptions use the cached model and run locally.

## If insertion does not work

The transcript is still copied to the clipboard. Press `Ctrl+V` in the target app. Some elevated or protected applications may block simulated typing.

## Microphone troubleshooting

Open **Windows Settings > Privacy & security > Microphone** and enable microphone access for desktop apps. Close other programs that have exclusive control of the microphone, then restart Whisper Free.
