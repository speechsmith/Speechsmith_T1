import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import tempfile
import json

# Load environment variables
load_dotenv()

# Configure Gemini client
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class TranscriptionService:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def transcribe_audio(self, audio_file):
        """Transcribe audio file to text using Gemini"""
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
                temp_audio.write(audio_file.read())
                temp_audio_path = temp_audio.name
            
            # Upload the file to Gemini
            uploaded = genai.upload_file(temp_audio_path)
            
            # Transcribe the audio
            response = self.model.generate_content(["Please transcribe the following audio:", uploaded])
            transcription_text = response.text
            
            # Clean up temp file
            os.remove(temp_audio_path)
            
            return transcription_text
            
        except Exception as e:
            st.error(f"Error in transcription: {str(e)}")
            return None
    
    def analyze_filler_words(self, transcription_text):
        """Analyze transcription for filler words using Gemini"""
        try:
            analysis_prompt = f"""Here is a transcription text:
            
{transcription_text}

Analyze this text and provide:
1. A list of all filler words used
2. The count of each filler word
3. A percentage of filler words relative to total words
4. Suggestions for improvement

Return the analysis in JSON format with the following structure:
{{
    "filler_words": {{
        "word1": count1,
        "word2": count2
    }},
    "total_words": total_word_count,
    "filler_word_percentage": percentage,
    "suggestions": [
        "suggestion1",
        "suggestion2"
    ]
}}"""

            analysis_response = self.model.generate_content(analysis_prompt)
            
            try:
                # Try to parse the response as JSON
                return json.loads(analysis_response.text)
            except json.JSONDecodeError:
                # If not valid JSON, return the raw text
                return {
                    "raw_analysis": analysis_response.text,
                    "filler_words": {},
                    "total_words": 0,
                    "filler_word_percentage": 0,
                    "suggestions": []
                }
                
        except Exception as e:
            st.error(f"Error in filler word analysis: {str(e)}")
            return None

def main():
    st.set_page_config(page_title="SpeechSmith: Smart Transcription & Analysis", page_icon="🎙️")
    st.title("🎙️ SpeechSmith - Smart Audio Transcription & Analysis")
    
    # Initialize the service
    service = TranscriptionService()
    
    # File uploader
    uploaded_file = st.file_uploader("Upload your audio file (.mp3, .wav, .ogg)", type=["mp3", "wav", "ogg"])
    
    if uploaded_file is not None:
        with st.spinner("Processing your audio file..."):
            # Step 1: Transcribe audio
            transcription_text = service.transcribe_audio(uploaded_file)
            
            if transcription_text:
                st.subheader("📝 Transcribed Text:")
                st.success(transcription_text)
                
                # Step 2: Analyze filler words
                with st.spinner("Analyzing filler words..."):
                    analysis_results = service.analyze_filler_words(transcription_text)
                    
                    if analysis_results:
                        st.subheader("🔎 Filler Word Analysis")
                        
                        # Display filler words and counts
                        if "filler_words" in analysis_results:
                            st.write("**Filler Words Detected:**")
                            for word, count in analysis_results["filler_words"].items():
                                st.write(f"- {word}: {count} times")
                        
                        # Display statistics
                        if "total_words" in analysis_results and "filler_word_percentage" in analysis_results:
                            st.write(f"\n**Statistics:**")
                            st.write(f"- Total Words: {analysis_results['total_words']}")
                            st.write(f"- Filler Word Percentage: {analysis_results['filler_word_percentage']:.1f}%")
                        
                        # Display suggestions
                        if "suggestions" in analysis_results and analysis_results["suggestions"]:
                            st.write("\n**Suggestions for Improvement:**")
                            for suggestion in analysis_results["suggestions"]:
                                st.write(f"- {suggestion}")
                        
                        # If raw analysis is present (in case JSON parsing failed)
                        if "raw_analysis" in analysis_results:
                            st.write("\n**Detailed Analysis:**")
                            st.info(analysis_results["raw_analysis"])
                
                # Allow download of transcription
                st.download_button(
                    "📥 Download Transcription",
                    data=transcription_text,
                    file_name="transcription.txt",
                    mime="text/plain"
                )

if __name__ == "__main__":
    main() 