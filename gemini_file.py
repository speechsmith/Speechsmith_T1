import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import tempfile

# Load environment variables
load_dotenv()

# Configure Gemini client
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Streamlit app
st.set_page_config(page_title="SpeechSmith: Smart Filler Word Detector", page_icon="🎙️")
st.title("🎙️ SpeechSmith - Smart Audio to Text + Filler Word Finder")

uploaded_file = st.file_uploader("Upload your audio file (.mp3, .wav, .ogg)", type=["mp3", "wav", "ogg"])

if uploaded_file is not None:
    with st.spinner("Processing your audio file..."):
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_audio.write(uploaded_file.read())
            temp_audio_path = temp_audio.name
        
        # Upload the file
        uploaded = genai.upload_file(temp_audio_path)

        # Step 1: Convert Audio to Text
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(["Please transcribe the following audio:", uploaded])

        transcription_text = response.text

        st.subheader("📝 Transcribed Text:")
        st.success(transcription_text)

        # Step 2: Find Filler Words using Gemini
        with st.spinner("Analyzing filler words using AI..."):
            analysis_prompt = f"""Here is a transcription text:
            
{transcription_text}


Identify and list all filler words used in the text.
Also tell how many times each filler word appears.

Return in a clean bullet point format."""

            analysis_response = model.generate_content(analysis_prompt)

            filler_word_report = analysis_response.text

            st.subheader("🔎 AI Detected Filler Words:")
            st.info(filler_word_report)

        # Allow download of transcription
        st.download_button("📥 Download Transcription", data=transcription_text, file_name="transcription.txt", mime="text/plain")

    # Clean up temp file
    os.remove(temp_audio_path)
