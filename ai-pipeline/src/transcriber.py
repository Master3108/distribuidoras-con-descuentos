import os
import openai


def transcribe_audio(video_path: str) -> str:
    """Transcribe el audio del video con OpenAI Whisper API.
    Devuelve string vacío si falla o no hay audio."""
    if not video_path or not os.path.exists(video_path):
        return ''
    try:
        client = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        with open(video_path, 'rb') as f:
            result = client.audio.transcriptions.create(
                model='whisper-1',
                file=f,
                language='es',
            )
        return result.text
    except Exception as e:
        print(f'Whisper transcription failed: {e}')
        return ''
