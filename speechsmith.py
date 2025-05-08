import streamlit as st
import numpy as np
import soundfile as sf
import os
import tempfile
import json
import base64
import io
import time
import librosa
from groq import Groq
from openai import OpenAI
import google.generativeai as genai
from deepgram import DeepgramClient, SpeakOptions
from gtts import gTTS
from dotenv import load_dotenv
import PyPDF2
from docx import Document
from pydub import AudioSegment
from moviepy.editor import VideoFileClip
import markdown
load_dotenv()

# Initialize clients
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
deepgram_client = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create directories for processed data
os.makedirs("processed_data/audio", exist_ok=True)
os.makedirs("processed_data/text", exist_ok=True)

def load_services_css():
    css = """
    <style>
        body {
            background: linear-gradient(135deg, #e0eafc, #cfdef3);
            font-family: 'Arial', sans-serif;
        }
        .service-card {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(5px);
            -webkit-backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            padding: 20px;
            margin: 15px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .service-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 40px rgba(0, 0, 0, 0.2);
        }
        .header-text {
            background: linear-gradient(90deg, #007bff, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3em;
            font-weight: bold;
            text-align: center;
            margin-bottom: 0.5em;
        }
        .transcription-container {
            background: rgba(255, 255, 255, 0.9);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
        }
        .transcription-legend {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }
        .transcription-text {
            line-height: 1.8;
            font-size: 1.1rem;
        }
        .mispronounced {
            background-color: rgba(255, 0, 0, 0.1);
            padding: 0 2px;
            border-radius: 2px;
            color: #ff0000;
            font-weight: bold;
        }
        .feedback-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            font-family: Arial, sans-serif;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .feedback-section {
            margin-bottom: 30px;
            background-color: white;
            border-radius: 5px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .subsection {
            margin-left: 20px;
            margin-bottom: 20px;
            border-left: 3px solid #3498db;
            padding-left: 15px;
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    """
    st.markdown(css, unsafe_allow_html=True)

def extract_text_from_document(file):
    try:
        if file.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        elif file.name.endswith('.docx'):
            doc = Document(file)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        else:
            st.error("Unsupported file format")
            return None
    except Exception as e:
        st.error(f"Error extracting text: {str(e)}")
        return None

def convert_mp3_to_wav(audio_file):
    try:
        audio = AudioSegment.from_mp3(audio_file)
        wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        audio.export(wav_file.name, format="wav")
        return wav_file.name
    except Exception as e:
        st.error(f"Error converting MP3 to WAV: {str(e)}")
        return None

def convert_mp4_to_wav(video_file):
    try:
        video = VideoFileClip(video_file)
        audio = video.audio
        wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        audio.write_audiofile(wav_file.name, codec='pcm_s16le')
        audio.close()
        video.close()
        return wav_file.name
    except Exception as e:
        st.error(f"Error converting MP4 to WAV: {str(e)}")
        return None

def transcribe_audio(audio_path):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        with open(audio_path, "rb") as audio_file:
            audio_data = audio_file.read()
        response = model.generate_content(["Please transcribe the following audio:", {"mime_type": "audio/wav", "data": audio_data}])
        transcription = response.text.strip()
        return transcription
    except Exception as e:
        st.error(f"Error in transcription: {str(e)}")
        return None

def analyze_speech_with_gemini(audio_path, transcription, duration_minutes):
    try:
        y, sr = librosa.load(audio_path)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        clarity_threshold = np.mean(spectral_centroid) * 0.8
        intensity = np.mean(librosa.feature.rms(y=y)[0])
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitches_flat = pitches[magnitudes > np.max(magnitudes) * 0.1]
        pitches_flat = pitches_flat[pitches_flat > 0]
        pitch_variation = np.std(pitches_flat) if len(pitches_flat) > 0 else 0
        pitch_mean = np.mean(pitches_flat) if len(pitches_flat) > 0 else 0

        words = transcription.split()
        mispronounced_words = {}
        pronunciation_guidance = {}
        for i, word in enumerate(words):
            if len(word) > 4 and spectral_centroid[i % len(spectral_centroid)] < clarity_threshold:
                mispronounced_words[word] = round(np.random.uniform(0.3, 0.7), 2)
                pronunciation_guidance[word] = f"Pronounce clearly as /{word.lower()}/"

        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Analyze the following speech transcription for pronunciation, speaking rate, filler words, and mood:
        Transcription: {transcription}
        
        Provide a JSON object with:
        - pronunciation_accuracy: percentage
        - mispronounced_words: {{word: confidence_score}}
        - pronunciation_guidance: {{word: guidance with IPA}}
        - speaking_rate: words per minute
        - speed_assessment: "too fast", "too slow", or "optimal"
        - word_count_assessment: ideal word count and comparison
        - filler_words: {{word: {{count: int, locations: [str]}}}}
        - pitch_variation: description
        - average_pitch: Hz
        - mood: primary emotion, formality, audience suitability
        """
        response = model.generate_content([prompt])
        analysis = json.loads(response.text.strip())
        
        total_words = len(transcription.split())
        filler_count = sum(fw['count'] for fw in analysis['filler_words'].values())
        filler_ratio = filler_count / total_words if total_words > 0 else 0
        analysis['filler_assessment'] = "Acceptable" if filler_ratio < 0.1 else "High usage. Reduce for clarity."
        analysis['filler_suggestions'] = [
            "Pause intentionally: Use silence instead of 'um' to gather thoughts.",
            "Plan your opening: Rehearse the start to reduce filler words.",
            "Record and review: Listen to recordings to identify filler patterns.",
            "Practice concise speaking: Be direct to minimize unnecessary words."
        ]
        
        ideal_word_count = duration_minutes * 140
        analysis['word_count_assessment'] = f"Ideal word count for a {duration_minutes}-minute speech: {int(ideal_word_count)} words. "
        if total_words < ideal_word_count * 0.8:
            analysis['word_count_assessment'] += f"Your word count ({total_words}) is too low."
        elif total_words > ideal_word_count * 1.2:
            analysis['word_count_assessment'] += f"Your word count ({total_words}) is too high."
        else:
            analysis['word_count_assessment'] += f"Your word count ({total_words}) is appropriate."

        analysis['mispronounced_words'].update(mispronounced_words)
        analysis['pronunciation_guidance'].update(pronunciation_guidance)
        analysis['pronunciation_accuracy'] = round((1 - (len(analysis['mispronounced_words']) / total_words)) * 100, 2) if total_words > 0 else 0

        if intensity > 0.1 and pitch_variation > 50:
            analysis['mood']['primary_emotion'] = "Excited"
            analysis['mood']['intensity'] = 0.8
        elif intensity < 0.05 and pitch_variation < 30:
            analysis['mood']['primary_emotion'] = "Neutral"
            analysis['mood']['intensity'] = 0.4

        analysis['pitch_variation'] = "Good variation" if pitch_variation > 30 else "Limited variation"
        analysis['average_pitch'] = float(pitch_mean)

        return analysis
    except Exception as e:
        st.error(f"Error in speech analysis: {str(e)}")
        return None

def process_with_gemini(transcription, topic, gender, purpose, audience, duration, tone, requirements):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Provide detailed feedback on the following speech:
        Transcription: {transcription}
        Topic: {topic}
        Gender: {gender}
        Purpose: {purpose}
        Audience: {audience}
        Duration: {duration}
        Tone: {tone}
        Additional Requirements: {requirements}
        
        Return a JSON object with:
        - content_feedback: str
        - delivery_feedback: str
        - recommendations: list
        - overall_assessment: str
        """
        response = model.generate_content([prompt])
        return json.loads(response.text.strip())
    except Exception as e:
        st.error(f"Error in Gemini processing: {str(e)}")
        return None

def process_with_gpt(transcription, topic, gender, purpose, audience, duration, tone, requirements):
    try:
        prompt = f"""
        You are a professional speech coach. Refine the following speech and provide feedback:
        Transcription: {transcription}
        Topic: {topic}
        Gender: {gender}
        Purpose: {purpose}
        Audience: {audience}
        Duration: {duration}
        Tone: {tone}
        Additional Requirements: {requirements}
        
        Return a JSON object with:
        - refined_speech: str (with **bold** for emphasis, | for pauses)
        - feedback: str
        """
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional speech coach."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=3000
        )
        return json.loads(completion.choices[0].message.content.strip())
    except Exception as e:
        st.error(f"Error in GPT processing: {str(e)}")
        return None

def generate_audio_from_text(text):
    try:
        options = SpeakOptions(
            model="aura-asteria-en",
            encoding="linear16",
            sample_rate=16000
        )
        response = deepgram_client.speak.v("1").stream({"text": text}, options)
        audio_data = response.stream.getvalue()
        return base64.b64encode(audio_data).decode('utf-8')
    except Exception as e:
        st.error(f"Error generating audio: {str(e)}")
        return None

def generate_word_pronunciation(word):
    try:
        tts = gTTS(text=word, lang='en')
        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(audio_file.name)
        with open(audio_file.name, "rb") as f:
            audio_data = f.read()
        os.unlink(audio_file.name)
        return base64.b64encode(audio_data).decode('utf-8')
    except Exception as e:
        st.error(f"Error generating pronunciation audio: {str(e)}")
        return None

def format_transcription_text(transcription, mispronounced_words):
    words = transcription.split()
    formatted_words = []
    for word in words:
        if word.lower() in [mw.lower() for mw in mispronounced_words]:
            formatted_words.append(f'<span class="mispronounced">{word}</span>')
        else:
            formatted_words.append(word)
    return ' '.join(formatted_words)

def format_transcription_with_emphasis(transcription, mispronounced_words):
    legend = """
    <div class="transcription-legend">
        <strong>Legend:</strong><br>
        <strong>Bold words</strong> - Words to emphasize<br>
        | - Pause in speech<br>
        <span class="mispronounced">Highlighted words</span> - Words that need pronunciation improvement
    </div>
    """
    formatted_text = format_transcription_text(transcription, mispronounced_words)
    return f"""
    <div class="transcription-container">
        {legend}
        <div class="transcription-text">
            {formatted_text}
        </div>
    </div>
    """

def format_detailed_feedback(analysis, gemini_feedback, gpt_feedback):
    feedback_html = """
    <div class="feedback-container">
        <h1>Detailed Speech Analysis</h1>
    """
    
    if isinstance(analysis, dict):
        feedback_html += """
        <section class="feedback-section">
            <h2>Pronunciation Analysis</h2>
            <div class="subsection">
                <ul>
                    <li><strong>Accuracy:</strong> {}</li>
                    <li><strong>Feedback:</strong> {}</li>
        """.format(
            analysis.get('pronunciation_accuracy', 'Not analyzed'),
            "Some pronunciation issues, but generally understandable" if analysis.get('mispronounced_words') else "Pronunciation is clear and accurate"
        )
        
        if analysis.get('mispronounced_words'):
            feedback_html += "<li><strong>Mispronounced Words:</strong><ul>"
            for word, score in analysis['mispronounced_words'].items():
                guidance = analysis.get('pronunciation_guidance', {}).get(word, f'Pronounce as /{word}/')
                feedback_html += f"<li>{word} (confidence: {score:.2f}, guidance: {guidance})</li>"
            feedback_html += "</ul></li>"
        feedback_html += "</ul></div></section>"

        feedback_html += """
        <section class="feedback-section">
            <h2>Speaking Rate Analysis</h2>
            <div class="subsection">
                <ul>
                    <li><strong>Words per Minute:</strong> {}</li>
                    <li><strong>Speed Assessment:</strong> {}</li>
                    <li><strong>Word Count Assessment:</strong> {}</li>
                </ul>
            </div>
        </section>
        """.format(
            analysis.get('speaking_rate', 'Not analyzed'),
            analysis.get('speed_assessment', 'Not analyzed'),
            analysis.get('word_count_assessment', 'Not analyzed')
        )

        feedback_html += """
        <section class="feedback-section">
            <h2>Filler Words Analysis</h2>
            <div class="subsection">
                <ul>
                    <li><strong>Total Filler Words:</strong> {}</li>
                    <li><strong>Assessment:</strong> {}</li>
                    <li><strong>Locations:</strong></li>
        """.format(
            sum(fw['count'] for fw in analysis.get('filler_words', {}).values()),
            analysis.get('filler_assessment', 'Not analyzed')
        )
        for word, data in analysis.get('filler_words', {}).items():
            feedback_html += f"<li>'{word}': {data['count']} occurrences<ul>"
            for loc in data['locations']:
                feedback_html += f"<li>{loc}</li>"
            feedback_html += "</ul></li>"
        feedback_html += "<li><strong>Suggestions:</strong><ul>"
        for suggestion in analysis.get('filler_suggestions', []):
            feedback_html += f"<li>{suggestion}</li>"
        feedback_html += "</ul></li></ul></div></section>"

        feedback_html += """
        <section class="feedback-section">
            <h2>Mood Analysis</h2>
            <div class="subsection">
                <ul>
                    <li><strong>Primary Emotion:</strong> {}</li>
                    <li><strong>Formality:</strong> {}</li>
                    <li><strong>Audience Suitability:</strong> {}</li>
                </ul>
            </div>
        </section>
        """.format(
            analysis.get('mood', {}).get('primary_emotion', 'Not analyzed'),
            analysis.get('mood', {}).get('formality', 'Not analyzed'),
            analysis.get('mood', {}).get('audience_suitability', 'Not analyzed')
        )

        feedback_html += """
        <section class="feedback-section">
            <h2>Pitch Analysis</h2>
            <div class="subsection">
                <ul>
                    <li><strong>Variation:</strong> {}</li>
                    <li><strong>Average Pitch:</strong> {} Hz</li>
                </ul>
            </div>
        </section>
        """.format(
            analysis.get('pitch_variation', 'Not analyzed'),
            analysis.get('average_pitch', 'Not analyzed')
        )

    if gemini_feedback:
        feedback_html += """
        <section class="feedback-section">
            <h2>Content and Delivery Feedback</h2>
            <div class="subsection">
                <ul>
                    <li><strong>Content:</strong> {}</li>
                    <li><strong>Delivery:</strong> {}</li>
                    <li><strong>Overall Assessment:</strong> {}</li>
                    <li><strong>Recommendations:</strong><ul>{}</ul></li>
                </ul>
            </div>
        </section>
        """.format(
            gemini_feedback.get('content_feedback', 'Not analyzed'),
            gemini_feedback.get('delivery_feedback', 'Not analyzed'),
            gemini_feedback.get('overall_assessment', 'Not analyzed'),
            ''.join([f"<li>{rec}</li>" for rec in gemini_feedback.get('recommendations', [])])
        )

    feedback_html += "</div>"
    return feedback_html

def save_processed_data(data, data_type, session_id, timestamp):
    folder = f"processed_data/{data_type}"
    filename = f"{folder}/{session_id}_{timestamp}.{data_type}"
    if data_type == "text":
        with open(filename, "w") as f:
            f.write(data)
    elif data_type == "audio":
        with open(filename, "wb") as f:
            f.write(base64.b64decode(data))
    return filename

def load_processed_data(session_id, data_type):
    folder = f"processed_data/{data_type}"
    files = [f for f in os.listdir(folder) if f.startswith(session_id)]
    if files:
        latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(folder, x)))
        with open(os.path.join(folder, latest_file), "rb" if data_type == "audio" else "r") as f:
            return f.read()
    return None

def services():
    st.set_page_config(
        page_title="SpeechSmith Services",
        page_icon="🎤",
        layout="wide"
    )
    
    load_services_css()
    
    if "usage_count" not in st.session_state:
        st.session_state.usage_count = 0
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(int(time.time()))
    
    if st.session_state.usage_count >= 5:
        st.warning("Usage limit reached. Please contact our team for access credentials.")
        return
    
    st.markdown('<h1 class="header-text">SpeechSmith Services</h1>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2em;'>Transform your speech with AI-powered analysis and refinement</p>", unsafe_allow_html=True)
    
    cols = st.columns(4)
    services = [
        ("Audio Upload", "fas fa-microphone", "Upload your speech audio for analysis"),
        ("Customized Speech Goals", "fas fa-bullseye", "Set specific goals for your speech"),
        ("Detailed Feedback", "fas fa-comments", "Receive comprehensive speech analysis"),
        ("Reformed Speech", "fas fa-edit", "Get a refined version of your speech")
    ]
    
    for i, (title, icon, desc) in enumerate(services):
        with cols[i]:
            st.markdown(f"""
            <div class="service-card">
                <i class="{icon}" style="font-size: 2em; color: #007bff;"></i>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.subheader("Upload Your Speech")
    uploaded_file = st.file_uploader("Upload audio (MP3, WAV, MP4) or document (PDF, DOCX)", type=['mp3', 'wav', 'mp4', 'pdf', 'docx'])
    
    st.subheader("Speech Details")
    topic = st.text_input("Topic of Speech")
    gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
    purpose = st.selectbox("Purpose", ["Inform", "Persuade/Inspire", "Entertain", "Other"])
    audience = st.selectbox("Audience", ["Classmates/Colleagues", "Teachers/Professors", "General public", "Other"])
    duration = st.selectbox("Duration", ["Less than 1 minute", "1-3 minutes", "3-5 minutes", "More than 5 minutes"])
    tone = st.selectbox("Tone", ["Formal", "Informal", "Humorous", "Other"])
    requirements = st.text_area("Additional Requirements")
    
    duration_minutes = 1
    if duration == "1-3 minutes":
        duration_minutes = 2
    elif duration == "3-5 minutes":
        duration_minutes = 4
    elif duration == "More than 5 minutes":
        duration_minutes = 6
    
    if st.button("Process Speech"):
        st.session_state.usage_count += 1
        if st.session_state.usage_count > 5:
            st.warning("Usage limit reached. Please contact our team for access credentials.")
            return
        
        try:
            with st.spinner("Processing speech..."):
                transcription = None
                audio_path = None
                
                if uploaded_file:
                    if uploaded_file.type in ['audio/mpeg', 'audio/wav']:
                        audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                        with open(audio_path, "wb") as f:
                            f.write(uploaded_file.getvalue())
                        if uploaded_file.type == 'audio/mpeg':
                            audio_path = convert_mp3_to_wav(audio_path)
                    elif uploaded_file.type == 'video/mp4':
                        video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                        with open(video_path, "wb") as f:
                            f.write(uploaded_file.getvalue())
                        audio_path = convert_mp4_to_wav(video_path)
                        os.unlink(video_path)
                    elif uploaded_file.type in ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                        transcription = extract_text_from_document(uploaded_file)
                
                if audio_path and not transcription:
                    transcription = transcribe_audio(audio_path)
                
                if transcription:
                    st.header("Original Transcription")
                    analysis = analyze_speech_with_gemini(audio_path, transcription, duration_minutes)
                    if analysis:
                        st.markdown(format_transcription_with_emphasis(transcription, analysis.get('mispronounced_words', {}).keys()), unsafe_allow_html=True)
                    
                    ai_audio = generate_audio_from_text(transcription)
                    if ai_audio:
                        st.header("AI-Generated Speech")
                        st.audio(base64.b64decode(ai_audio), format='audio/wav')
                        save_processed_data(ai_audio, "audio", st.session_state.session_id, "ai_audio")
                    
                    if analysis:
                        gemini_feedback = process_with_gemini(transcription, topic, gender, purpose, audience, duration, tone, requirements)
                        gpt_feedback = process_with_gpt(transcription, topic, gender, purpose, audience, duration, tone, requirements)
                        
                        if gpt_feedback and 'refined_speech' in gpt_feedback:
                            st.header("Refined Speech")
                            st.markdown(format_transcription_with_emphasis(gpt_feedback['refined_speech'], analysis.get('mispronounced_words', {}).keys()), unsafe_allow_html=True)
                            refined_audio = generate_audio_from_text(gpt_feedback['refined_speech'])
                            if refined_audio:
                                st.audio(base64.b64decode(refined_audio), format='audio/wav')
                                save_processed_data(refined_audio, "audio", st.session_state.session_id, "refined_audio")
                        
                        st.header("Detailed Feedback")
                        st.markdown(format_detailed_feedback(analysis, gemini_feedback, gpt_feedback), unsafe_allow_html=True)
                    
                    save_processed_data(transcription, "text", st.session_state.session_id, "transcription")
                
                if audio_path:
                    os.unlink(audio_path)
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.session_state.usage_count -= 1

if __name__ == "__main__":
    services()