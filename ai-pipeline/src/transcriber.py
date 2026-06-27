import os
import openai

# gpt-4o-mini-transcribe: ~mitad de precio que whisper-1 y muy preciso.
# Configurable por entorno para poder cambiarlo sin tocar código.
TRANSCRIBE_MODEL = os.environ.get('OPENAI_TRANSCRIBE_MODEL', 'gpt-4o-mini-transcribe')


def transcribe_audio(video_path: str) -> str:
    """Transcribe el audio del video con la API de transcripción de OpenAI.
    Devuelve string vacío si falla o no hay audio."""
    if not video_path or not os.path.exists(video_path):
        return ''
    try:
        client = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        with open(video_path, 'rb') as f:
            result = client.audio.transcriptions.create(
                model=TRANSCRIBE_MODEL,
                file=f,
                language='es',
            )
        return result.text
    except Exception as e:
        print(f'Transcripción ({TRANSCRIBE_MODEL}) falló: {e}')
        return ''
