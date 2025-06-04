import sys
print("Python utilisé :", sys.executable)

import streamlit as st
from moviepy.editor import VideoFileClip, AudioFileClip
import whisper
from transformers import MarianMTModel, MarianTokenizer
from TTS.api import TTS
import time
import os
import tempfile
from yt_dlp import YoutubeDL


# === TÉLÉCHARGEMENT YOUTUBE ===
def download_youtube_video(youtube_url):
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, 'video.%(ext)s')

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
        'quiet': True
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    for f in os.listdir(temp_dir):
        if f.endswith(".mp4"):
            return os.path.join(temp_dir, f)
    raise Exception("Téléchargement YouTube échoué.")


# === TRANSCRIPTION ===
def transcribe_audio(video_path):
    model = whisper.load_model("small")
    clip = VideoFileClip(video_path)
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        clip.audio.write_audiofile(temp_audio.name)
        clip.close()
        result = model.transcribe(temp_audio.name)
    finally:
        temp_audio.close()
        time.sleep(1)
        try:
            os.unlink(temp_audio.name)
        except Exception:
            pass
    return result["text"], result["segments"]


# === DIVISER LE TEXTE ===
def split_text_into_chunks(text, max_length=500):
    words = text.split()
    chunks, current_chunk, current_length = [], [], 0
    for word in words:
        current_length += len(word) + 1
        if current_length > max_length:
            chunks.append(" ".join(current_chunk))
            current_chunk, current_length = [], len(word) + 1
        current_chunk.append(word)
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks


# === TRADUCTION ===
def translate_text(text, src_lang="en", tgt_lang="fr", max_length=500):
    if src_lang == tgt_lang:
        return text

    model_name = f"Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}"
    try:
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
    except Exception as e:
        raise RuntimeError(f"Erreur de chargement du modèle de traduction : {e}")

    chunks = split_text_into_chunks(text, max_length)
    translated_chunks = []
    for chunk in chunks:
        tokens = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True)
        translated = model.generate(**tokens)
        translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
        translated_chunks.append(translated_text)
    return " ".join(translated_chunks)


# === SYNTHÈSE VOCALE ===
def generate_audio(text, language, output_path):
    model_name = f"tts_models/{language}/css10/vits"
    tts = TTS(model_name)
    tts.tts_to_file(text=text, file_path=output_path)


# === REMPLACER L'AUDIO ===
def replace_audio_in_video(video_path, audio_path, output_path):
    video = VideoFileClip(video_path)
    new_audio = AudioFileClip(audio_path)
    video = video.set_audio(new_audio)
    video.write_videofile(output_path, codec="libx264", audio_codec="aac")
    video.close()
    new_audio.close()


# === TRAITEMENT VIDÉO PRINCIPAL ===
def process_video(video_path, src_lang, tgt_lang, output_video_path=None, output_audio_path=None):
    st.write("🔍 Transcription de la vidéo...")
    transcription, _ = transcribe_audio(video_path)

    st.write("📝 Texte transcrit :")
    st.text_area("Texte extrait de la vidéo", transcription, height=300)

    if src_lang != tgt_lang:
        st.write("🌍 Traduction en cours...")
        translated_text = translate_text(transcription, src_lang, tgt_lang)

        st.write("📝 Texte traduit :")
        st.text_area("Texte traduit", translated_text, height=300)

        if output_video_path or output_audio_path:
            st.write("🎙️ Génération de l'audio...")
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            generate_audio(translated_text, tgt_lang, temp_audio.name)

            if output_video_path:
                st.write("🎬 Remplacement de l'audio dans la vidéo...")
                replace_audio_in_video(video_path, temp_audio.name, output_video_path)

            if output_audio_path:
                audio = AudioFileClip(temp_audio.name)
                audio.write_audiofile(output_audio_path)
                audio.close()

            try:
                os.unlink(temp_audio.name)
            except Exception:
                pass


# === INTERFACE STREAMLIT ===
st.set_page_config(page_title="Traducteur Vidéo IA", layout="wide")

col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    st.image("amin.jpg", width=80)
with col2:
    st.markdown("<h1 style='text-align: center;'>Traducteur de vidéos MP4 avec l'IA</h1>", unsafe_allow_html=True)
with col3:
    st.markdown("""<div style='text-align: right;'><strong>BOUAROUROU</strong></div>""", unsafe_allow_html=True)

st.write("Téléchargez une vidéo MP4 **ou collez un lien YouTube**, choisissez la langue d'origine et la langue cible, puis cliquez sur **Run**.")

uploaded_video = st.file_uploader("📁 Téléchargez une vidéo MP4", type=["mp4"])
video_url = st.text_input("📺 Ou entrez un lien YouTube (https://...)")

src_lang = st.selectbox("Langue d'origine", ["en", "fr", "es", "de"])
tgt_lang = st.selectbox("Langue cible", ["en", "fr", "es", "de"])
output_option = st.radio("Format de sortie", ["Aucun (juste le texte)", "Vidéo traduite (MP4)", "Audio seulement (MP3)", "Les deux (MP4 et MP3)"])

if st.button("Run"):
    temp_video_path = None
    output_video_path = None
    output_audio_path = None

    if uploaded_video:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
            temp_video.write(uploaded_video.read())
            temp_video_path = temp_video.name
    elif video_url:
        try:
            st.write("📥 Téléchargement de la vidéo depuis YouTube...")
            temp_video_path = download_youtube_video(video_url)
        except Exception as e:
            st.error(f"Erreur de téléchargement YouTube : {e}")
    else:
        st.error("Veuillez uploader une vidéo ou fournir un lien YouTube.")

    if temp_video_path:
        if output_option in ["Vidéo traduite (MP4)", "Les deux (MP4 et MP3)"]:
            output_video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        if output_option in ["Audio seulement (MP3)", "Les deux (MP4 et MP3)"]:
            output_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

        try:
            process_video(temp_video_path, src_lang, tgt_lang, output_video_path, output_audio_path)

            if output_video_path and os.path.exists(output_video_path):
                st.success("✅ Vidéo traduite générée avec succès !")
                with open(output_video_path, "rb") as f:
                    st.download_button("📥 Télécharger la vidéo traduite (MP4)", f, file_name="translated_video.mp4")

            if output_audio_path and os.path.exists(output_audio_path):
                st.success("✅ Audio traduit généré avec succès !")
                with open(output_audio_path, "rb") as f:
                    st.download_button("🎧 Télécharger l'audio traduit (MP3)", f, file_name="translated_audio.mp3")

        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")

        finally:
            time.sleep(1)
            for path in [temp_video_path, output_video_path, output_audio_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception:
                        st.warning(f"⚠️ Impossible de supprimer {path}. Fichier encore utilisé.")
