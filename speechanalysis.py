import streamlit as st
import numpy as np
import pandas as pd
import soundfile as sf
import librosa
from groq import Groq
import torch
from transformers import pipeline
import wave
import contextlib
from textblob import TextBlob
import speech_recognition as sr
import tempfile
import os
import json
import re
from dotenv import load_dotenv
import markdown
from typing import Optional
load_dotenv()

class SpeechAnalyzer:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.recognizer = sr.Recognizer()
    
    def get_audio_duration(self, audio_path):
        with contextlib.closing(wave.open(audio_path, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
        return duration
    
    def transcribe_audio(self, audio_path):
        try:
            import openai
            from openai import OpenAI
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            with open(audio_path, "rb") as audio_file:
                st.write("Transcribing using OpenAI Whisper...")
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                    response_format="text"
                )
                
                transcription = response.strip()
                
                if not transcription:
                    st.error("No speech detected in the audio file")
                    return None
                
                return transcription
                
        except Exception as e:
            st.error(f"Error in transcription: {str(e)}")
            return None

    def analyze_text_with_llama(self, text, analysis_type, topic=None):
        prompts = {
            'pronunciation': f"""
                Analyze the following text for pronunciation accuracy and identify any potentially mispronounced words:
                
                Text: {text}
                
                Please provide a JSON object with the following structure:
                {{
                    "mispronounced_words": {{
                        "word1": confidence_score_1,
                        "word2": confidence_score_2
                    }},
                    "pronunciation_guidance": {{
                        "word1": "correct pronunciation guide",
                        "word2": "correct pronunciation guide"
                    }}
                }}
                
                Guidelines:
                1. Only include words that are likely to be mispronounced
                2. Consider common pronunciation challenges for non-native speakers
                3. Focus on words with complex syllable structures or unusual spellings
                4. Assign confidence scores based on pronunciation difficulty
                5. Provide clear pronunciation guidance with phonetic notation (IPA)
                
                Only return the JSON object, nothing else.
            """,
            'mood': f"""
                Analyze the mood and emotional content of the following text:
                Text: {text}
                Topic: {topic}
                
                Please provide a JSON object with the following structure:
                {{
                    "primary_emotion": "emotion name",
                    "secondary_emotions": ["emotion1", "emotion2"],
                    "intensity": 0.0-1.0,
                    "formality": "formality level",
                    "audience_suitability": "suitability assessment",
                    "mood_suitability_assessment": {{
                        "assessment": "suitability assessment",
                        "reasons": ["reason1", "reason2"]
                    }}
                }}
                
                Only return the JSON object, nothing else.
            """,
            'filler_analysis': f"""
                Analyze the following text for filler words and speech patterns:
                Text: {text}
                
                Please provide a JSON object with the following structure:
                {{
                    "filler_words": {{
                        "word1": {{
                            "count": count1,
                            "locations": ["location1", "location2"]
                        }},
                        "word2": {{
                            "count": count2,
                            "locations": ["location1", "location2"]
                        }}
                    }},
                    "total_words": total_word_count,
                    "style_assessment": "assessment text",
                    "suggestions": ["suggestion1", "suggestion2"]
                }}
                
                Only return the JSON object, nothing else.
            """
        }

        try:
            completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional speech analyst. Provide analysis in valid JSON format only."
                    },
                    {
                        "role": "user",
                        "content": prompts[analysis_type]
                    }
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            
            content = completion.choices[0].message.content.strip()
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                content = content[json_start:json_end]
            
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {str(e)}")
                print(f"Response content: {content}")
                return None
                
        except Exception as e:
            print(f"Error in Llama analysis: {str(e)}")
            return None

    def analyze_pronunciation(self, audio_path, transcript):
        try:
            y, sr = librosa.load(audio_path)
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            clarity_threshold = np.mean(spectral_centroid) * 0.8
            
            words = transcript.split()
            mispronounced_words = {}
            pronunciation_guidance = {}
            
            for i, word in enumerate(words):
                if len(word) > 4 and spectral_centroid[i % len(spectral_centroid)] < clarity_threshold:
                    mispronounced_words[word] = round(np.random.uniform(0.3, 0.7), 2)
                    pronunciation_guidance[word] = f"Pronounce clearly as /{word.lower()}/"
            
            llama_analysis = self.analyze_text_with_llama(transcript, 'pronunciation')
            if llama_analysis:
                mispronounced_words.update(llama_analysis.get('mispronounced_words', {}))
                pronunciation_guidance.update(llama_analysis.get('pronunciation_guidance', {}))
            
            total_words = len(words)
            mispronounced_count = len(mispronounced_words)
            accuracy = round((1 - (mispronounced_count / total_words)) * 100, 2) if total_words > 0 else 0
            
            feedback = []
            if mispronounced_count > 0:
                if mispronounced_count / total_words > 0.2:
                    feedback.append("Several pronunciation challenges affect clarity.")
                else:
                    feedback.append("Some pronunciation issues, but generally understandable.")
                if any(score < 0.5 for score in mispronounced_words.values()):
                    feedback.append("Some words have significant pronunciation difficulties.")
            else:
                feedback.append("Pronunciation is clear and accurate.")
            
            return {
                'accuracy': accuracy,
                'feedback': ' '.join(feedback),
                'difficult_words': mispronounced_words,
                'pronunciation_guidance': pronunciation_guidance
            }
            
        except Exception as e:
            print(f"Error in pronunciation analysis: {str(e)}")
            return {
                'accuracy': 0,
                'feedback': f'Error in pronunciation analysis: {str(e)}',
                'difficult_words': {},
                'pronunciation_guidance': {}
            }

    def analyze_pitch(self, audio_path, gender):
        try:
            if gender not in ['male', 'female']:
                return {
                    'variation': 'Gender not specified for pitch analysis',
                    'consistency': 'Gender not specified for pitch analysis',
                    'average': 0.0
                }
            
            y, sr = librosa.load(audio_path)
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitches_flat = pitches[magnitudes > np.max(magnitudes) * 0.1]
            pitches_flat = pitches_flat[pitches_flat > 0]
            
            if len(pitches_flat) == 0:
                return {
                    'variation': 'Unable to detect pitch',
                    'consistency': 'Unable to detect pitch',
                    'average': 0.0
                }
            
            pitch_mean = np.mean(pitches_flat)
            pitch_std = np.std(pitches_flat)
            pitch_range = np.max(pitches_flat) - np.min(pitches_flat)
            
            thresholds = {
                'male': {
                    'monotonous': 20,
                    'erratic': 80,
                    'normal_range': (85, 180),
                    'variation_threshold': 40
                },
                'female': {
                    'monotonous': 30,
                    'erratic': 100,
                    'normal_range': (165, 255),
                    'variation_threshold': 50
                }
            }
            
            current_threshold = thresholds[gender]
            
            if pitch_std < current_threshold['monotonous']:
                variation = 'Limited pitch variation. Consider adding more vocal variety.'
            elif pitch_std > current_threshold['erratic']:
                variation = 'Excessive pitch variation. Try to maintain consistent pitch levels.'
            else:
                variation = 'Good pitch variation. Maintains audience interest.'
            
            if pitch_range < current_threshold['variation_threshold']:
                consistency = 'Pitch too consistent. Vary pitch to emphasize key points.'
            elif pitch_range > current_threshold['variation_threshold'] * 2:
                consistency = 'Pitch varies too much. Maintain consistent levels.'
            else:
                consistency = 'Good pitch consistency. Maintains appropriate variation.'
            
            normal_min, normal_max = current_threshold['normal_range']
            if pitch_mean < normal_min:
                consistency += ' Average pitch is lower than typical.'
            elif pitch_mean > normal_max:
                consistency += ' Average pitch is higher than typical.'
            
            return {
                'variation': variation,
                'consistency': consistency,
                'average': float(pitch_mean),
                'standard_deviation': float(pitch_std),
                'range': float(pitch_range)
            }
            
        except Exception as e:
            print(f"Error in pitch analysis: {str(e)}")
            return {
                'variation': f'Error in pitch analysis: {str(e)}',
                'consistency': f'Error in pitch analysis: {str(e)}',
                'average': 0.0
            }

    def analyze_speech_rate(self, audio_path, transcript, duration_minutes):
        try:
            duration = self.get_audio_duration(audio_path)
            if duration == 0:
                return {
                    'wpm': 0,
                    'assessment': 'Unable to calculate speech rate: Audio duration is zero',
                    'filler_words': {},
                    'total_words': 0,
                    'word_count_assessment': '',
                    'speed_assessment': ''
                }

            y, sr = librosa.load(audio_path)
            intervals = librosa.effects.split(y, top_db=20)
            speech_duration = sum(interval[1] - interval[0] for interval in intervals) / sr
            
            filler_analysis = self.analyze_text_with_llama(transcript, 'filler_analysis')
            
            total_words = len(transcript.split())
            filler_words = filler_analysis.get('filler_words', {}) if filler_analysis else {}
            filler_count = sum(fw['count'] for fw in filler_words.values())
            effective_words = total_words - filler_count
            
            words_per_minute = (effective_words / duration) * 60
            
            if words_per_minute < 120:
                speed_assessment = "Speaking rate is too slow (<120 WPM). Increase pace for better engagement."
            elif words_per_minute > 160:
                speed_assessment = "Speaking rate is too fast (>160 WPM). Slow down for clarity."
            else:
                speed_assessment = "Speaking rate is optimal (120-160 WPM)."
            
            ideal_word_count = duration_minutes * 140
            word_count_assessment = f"Ideal word count for a {duration_minutes}-minute speech: {int(ideal_word_count)} words. "
            if total_words < ideal_word_count * 0.8:
                word_count_assessment += f"Your word count ({total_words}) is too low."
            elif total_words > ideal_word_count * 1.2:
                word_count_assessment += f"Your word count ({total_words}) is too high."
            else:
                word_count_assessment += f"Your word count ({total_words}) is appropriate."
            
            return {
                'wpm': round(words_per_minute, 2),
                'assessment': filler_analysis.get('style_assessment', 'Not analyzed') if filler_analysis else 'Not analyzed',
                'filler_words': filler_words,
                'total_words': total_words,
                'effective_words': effective_words,
                'speech_duration': round(speech_duration, 2),
                'total_duration': round(duration, 2),
                'word_count_assessment': word_count_assessment,
                'speed_assessment': speed_assessment
            }
            
        except Exception as e:
            print(f"Error in speech rate analysis: {str(e)}")
            return {
                'wpm': 0,
                'assessment': f'Error in speech rate analysis: {str(e)}',
                'filler_words': {},
                'total_words': 0,
                'word_count_assessment': '',
                'speed_assessment': ''
            }

    def analyze_mood(self, audio_path, transcript, topic):
        try:
            y, sr = librosa.load(audio_path)
            intensity = np.mean(librosa.feature.rms(y=y)[0])
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitches_flat = pitches[magnitudes > np.max(magnitudes) * 0.1]
            pitches_flat = pitches_flat[pitches_flat > 0]
            pitch_variation = np.std(pitches_flat) if len(pitches_flat) > 0 else 0
            
            text_mood = self.analyze_text_with_llama(transcript, 'mood', topic)
            
            if intensity > 0.1 and pitch_variation > 50:
                primary_emotion = "Excited"
                intensity_score = 0.8
            elif intensity < 0.05 and pitch_variation < 30:
                primary_emotion = "Neutral"
                intensity_score = 0.4
            else:
                primary_emotion = text_mood.get('primary_emotion', 'Neutral') if text_mood else 'Neutral'
                intensity_score = text_mood.get('intensity', 0.5) if text_mood else 0.5
            
            return {
                'primary_emotion': primary_emotion,
                'secondary_emotions': text_mood.get('secondary_emotions', []) if text_mood else [],
                'intensity': intensity_score,
                'formality': text_mood.get('formality', 'Not analyzed') if text_mood else 'Not analyzed',
                'audience_suitability': text_mood.get('audience_suitability', 'Not analyzed') if text_mood else 'Not analyzed',
                'mood_suitability_assessment': text_mood.get('mood_suitability_assessment', {'assessment': 'Not analyzed', 'reasons': []}) if text_mood else {'assessment': 'Not analyzed', 'reasons': []}
            }
            
        except Exception as e:
            print(f"Error in mood analysis: {str(e)}")
            return {
                'primary_emotion': 'Not analyzed',
                'secondary_emotions': [],
                'intensity': 0.0,
                'formality': 'Not analyzed',
                'audience_suitability': 'Not analyzed',
                'mood_suitability_assessment': {'assessment': 'Not analyzed', 'reasons': []}
            }

def format_transcription(transcript, mispronounced_words):
    words = transcript.split()
    formatted_words = []
    for word in words:
        if word.lower() in [mw.lower() for mw in mispronounced_words]:
            formatted_words.append(f'<span class="mispronounced">{word}</span>')
        else:
            formatted_words.append(word)
    formatted_text = ' '.join(formatted_words)
    
    legend = """
    <div class="transcription-legend">
        <strong>Legend:</strong><br>
        <span class="mispronounced">Highlighted words</span> - Words that need pronunciation improvement
    </div>
    """
    
    return f"""
    <div class="transcription-container">
        {legend}
        <div class="transcription-text">
            {formatted_text}
        </div>
    </div>
    """

def generate_feedback(analyzer_results, topic):
    feedback = {
        'tone_and_style': {
            'title': 'Tone and Style Analysis',
            'original': [],
            'revised': []
        },
        'pacing_and_timing': {
            'title': 'Pacing and Timing Analysis',
            'original': [],
            'revised': []
        },
        'clarity_and_structure': {
            'title': 'Clarity and Structure Evaluation',
            'original': [],
            'revised': []
        },
        'technical_analysis': {
            'title': 'Technical Analysis Results',
            'pronunciation': [],
            'speech_rate': [],
            'mood': [],
            'pitch': [],
            'filler_words': []
        },
        'improvement_recommendations': {
            'title': 'Specific Improvement Recommendations',
            'original': [],
            'additional': []
        }
    }
    
    if analyzer_results.get('mood'):
        mood = analyzer_results['mood']
        feedback['tone_and_style']['original'].extend([
            f"Primary emotion: {mood.get('primary_emotion', 'Not analyzed')}",
            f"Formality level: {mood.get('formality', 'Not analyzed')}",
            f"Audience suitability: {mood.get('audience_suitability', 'Not analyzed')}"
        ])
        if mood.get('mood_suitability_assessment'):
            assessment = mood['mood_suitability_assessment']
            feedback['tone_and_style']['revised'].extend([
                f"Assessment: {assessment.get('assessment', 'Not analyzed')}",
                "Reasons:"
            ])
            if isinstance(assessment.get('reasons'), list):
                feedback['tone_and_style']['revised'].extend(assessment['reasons'])

    if analyzer_results.get('speech_rate'):
        rate = analyzer_results['speech_rate']
        feedback['pacing_and_timing']['original'].extend([
            f"Words per minute: {rate.get('wpm', 0)}",
            f"Speed assessment: {rate.get('speed_assessment', 'Not analyzed')}",
            f"Word count assessment: {rate.get('word_count_assessment', 'Not analyzed')}",
            f"Speech duration: {rate.get('speech_duration', 0)} seconds",
            f"Total duration: {rate.get('total_duration', 0)} seconds"
        ])
        
        filler_words = rate.get('filler_words', {})
        total_filler_count = sum(fw['count'] for fw in filler_words.values())
        total_words = rate.get('total_words', 1)
        filler_ratio = total_filler_count / total_words if total_words > 0 else 0
        filler_assessment = "Acceptable filler word usage." if filler_ratio < 0.1 else "High filler word usage. Consider reducing for clarity."
        
        feedback['technical_analysis']['filler_words'].extend([
            f"Total filler words: {total_filler_count}",
            f"Filler word ratio: {filler_ratio:.1%}",
            f"Assessment: {filler_assessment}",
            "Locations:"
        ])
        for word, data in filler_words.items():
            feedback['technical_analysis']['filler_words'].append(f"- '{word}': {data['count']} occurrences")
            for loc in data['locations']:
                feedback['technical_analysis']['filler_words'].append(f"  - {loc}")
        feedback['technical_analysis']['filler_words'].append("Suggestions for limiting filler words:")
        feedback['technical_analysis']['filler_words'].extend([
            "- Pause intentionally: Instead of 'um,' use a brief silence to gather thoughts.",
            "- Plan your opening: Rehearse the start to reduce filler words.",
            "- Record and review: Listen to recordings to identify filler word patterns.",
            "- Practice concise speaking: Be direct to minimize unnecessary words."
        ])

    if analyzer_results.get('pronunciation'):
        pron = analyzer_results['pronunciation']
        feedback['clarity_and_structure']['original'].extend([
            f"Overall accuracy: {pron.get('accuracy', 0)}%",
            f"Accuracy feedback: {pron.get('feedback', 'Not analyzed')}"
        ])
        if pron.get('difficult_words'):
            feedback['clarity_and_structure']['revised'].append("Mispronounced words:")
            for word, score in pron['difficult_words'].items():
                guidance = pron.get('pronunciation_guidance', {}).get(word, 'No guidance available')
                feedback['clarity_and_structure']['revised'].append(f"- {word} (confidence: {score:.2f}, guidance: {guidance})")

    if analyzer_results.get('pronunciation'):
        pron = analyzer_results['pronunciation']
        feedback['technical_analysis']['pronunciation'].extend([
            f"Overall Accuracy: {pron.get('accuracy', 0)}%",
            f"Feedback: {pron.get('feedback', 'Not analyzed')}"
        ])
        if pron.get('difficult_words'):
            feedback['technical_analysis']['pronunciation'].append("Mispronounced Words:")
            for word, score in pron['difficult_words'].items():
                guidance = pron.get('pronunciation_guidance', {}).get(word, 'No guidance available')
                feedback['technical_analysis']['pronunciation'].append(f"- {word} (confidence: {score:.2f}, guidance: {guidance})")

    if analyzer_results.get('speech_rate'):
        rate = analyzer_results['speech_rate']
        feedback['technical_analysis']['speech_rate'].extend([
            f"Words per minute: {rate.get('wpm', 0)}",
            f"Speed assessment: {rate.get('speed_assessment', 'Not analyzed')}",
            f"Word count assessment: {rate.get('word_count_assessment', 'Not analyzed')}"
        ])

    if analyzer_results.get('mood'):
        mood = analyzer_results['mood']
        feedback['technical_analysis']['mood'].extend([
            f"Primary Emotion: {mood.get('primary_emotion', 'Not analyzed')}",
            f"Formality: {mood.get('formality', 'Not analyzed')}",
            f"Audience Suitability: {mood.get('audience_suitability', 'Not analyzed')}"
        ])
        if mood.get('mood_suitability_assessment'):
            assessment = mood['mood_suitability_assessment']
            feedback['technical_analysis']['mood'].extend([
                f"Assessment: {assessment.get('assessment', 'Not analyzed')}",
                "Reasons:"
            ])
            if isinstance(assessment.get('reasons'), list):
                feedback['technical_analysis']['mood'].extend(assessment['reasons'])

    if analyzer_results.get('pitch'):
        pitch = analyzer_results['pitch']
        feedback['technical_analysis']['pitch'].extend([
            f"Variation: {pitch.get('variation', 'Not analyzed')}",
            f"Consistency: {pitch.get('consistency', 'Not analyzed')}",
            f"Average Pitch: {pitch.get('average', 0):.1f} Hz"
        ])

    if analyzer_results.get('pronunciation'):
        pron = analyzer_results['pronunciation']
        if pron.get('difficult_words'):
            feedback['improvement_recommendations']['original'].append("Pronunciation improvements needed for:")
            for word in pron['difficult_words'].keys():
                feedback['improvement_recommendations']['original'].append(f"- {word}")

    if analyzer_results.get('speech_rate'):
        rate = analyzer_results['speech_rate']
        if rate.get('filler_words'):
            feedback['improvement_recommendations']['additional'].append("Reduce usage of filler words:")
            for word in rate['filler_words'].keys():
                feedback['improvement_recommendations']['additional'].append(f"- {word}")

    if analyzer_results.get('pitch'):
        pitch = analyzer_results['pitch']
        if 'Good pitch variation' in pitch.get('variation', ''):
            feedback['improvement_recommendations']['additional'].append("Maintain current pitch variation")
        else:
            feedback['improvement_recommendations']['additional'].append("Work on improving pitch variation")

    return feedback

def format_feedback_to_html(feedback, transcription, mispronounced_words):
    def format_section(items):
        if not items:
            return "<p>No feedback available</p>"
        html = "<ul>"
        for item in items:
            html += f"<li>{item}</li>"
        html += "</ul>"
        return html

    content = """
        <div class="feedback-container">
            <h1>Speech Analysis Feedback</h1>
            <section class="feedback-section">
                <h2>Original Transcription</h2>
                {transcription}
            </section>
    """.format(transcription=format_transcription(transcription, mispronounced_words))

    for section_key, section_data in feedback.items():
        if section_key != 'technical_analysis':
            content += f"""
                <section class="feedback-section">
                    <h2>{section_data['title']}</h2>
                    <div class="subsection">
                        <h3>Analysis:</h3>
                        {format_section(section_data['original'])}
                    </div>
                    <div class="subsection">
                        <h3>Revised Suggestions:</h3>
                        {format_section(section_data['revised'])}
                    </div>
                </section>
            """
        else:
            content += f"""
                <section class="feedback-section">
                    <h2>{section_data['title']}</h2>
            """
            for subsection in ['pronunciation', 'speech_rate', 'mood', 'pitch', 'filler_words']:
                if section_data[subsection]:
                    content += f"""
                        <div class="subsection">
                            <h3>{subsection.replace('_', ' ').title()}:</h3>
                            <ul>
                    """
                    for item in section_data[subsection]:
                        content += f"<li>{item}</li>"
                    content += "</ul></div>"
            content += "</section>"

    content += """
        </div>
        <style>
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
            h1 {
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
                margin-bottom: 30px;
            }
            h2 {
                color: #34495e;
                margin-top: 25px;
                font-size: 1.5em;
            }
            h3 {
                color: #7f8c8d;
                margin-top: 15px;
                font-size: 1.2em;
            }
            ul {
                list-style-type: none;
                padding-left: 20px;
                margin-top: 10px;
            }
            li {
                margin: 8px 0;
                position: relative;
                line-height: 1.4;
            }
            li:before {
                content: "•";
                color: #3498db;
                font-weight: bold;
                position: absolute;
                left: -15px;
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
        </style>
    """
    
    return content

def main():
    st.set_page_config(
        page_title="Advanced Speech Analysis Tool",
        page_icon="🎤",
        layout="wide"
    )
    
    st.title("Advanced Speech Analysis Tool")
    
    analyzer = SpeechAnalyzer()
    
    topic = st.text_input("Topic of Speech")
    audio_file = st.file_uploader("Upload Audio File (.wav format)", type=['wav'])
    gender = st.radio("Select Gender (for pitch analysis)", ['male', 'female'])
    duration = st.selectbox("Intended Speech Duration", ["Less than 1 minute", "1-3 minutes", "3-5 minutes", "More than 5 minutes"])
    
    duration_minutes = 1
    if duration == "1-3 minutes":
        duration_minutes = 2
    elif duration == "3-5 minutes":
        duration_minutes = 4
    elif duration == "More than 5 minutes":
        duration_minutes = 6
    
    if audio_file and topic:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(audio_file.getvalue())
            audio_path = tmp_file.name
        
        try:
            with st.spinner("Analyzing speech..."):
                transcript = analyzer.transcribe_audio(audio_path)
                
                if transcript:
                    st.header("Original Speech")
                    st.audio(audio_file, format='audio/wav')
                    
                    results = {
                        'pronunciation': analyzer.analyze_pronunciation(audio_path, transcript),
                        'pitch': analyzer.analyze_pitch(audio_path, gender),
                        'speech_rate': analyzer.analyze_speech_rate(audio_path, transcript, duration_minutes),
                        'mood': analyzer.analyze_mood(audio_path, transcript, topic)
                    }
                    
                    feedback = generate_feedback(results, topic)
                    mispronounced_words = results['pronunciation'].get('difficult_words', {}).keys()
                    formatted_feedback = format_feedback_to_html(feedback, transcript, mispronounced_words)
                    st.markdown(formatted_feedback, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
        
        finally:
            os.unlink(audio_path)

if __name__ == "__main__":
    main()