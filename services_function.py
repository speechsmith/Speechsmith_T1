def services():
    analyzer = SpeechAnalyzer()
    
    if 'usage_count' not in st.session_state:
        st.session_state.usage_count = 0
    
    if st.session_state.usage_count >= 5 and not st.session_state.get('is_authenticated', False):
        st.error("""
            You have reached the free trial limit of 5 uses.
            Please fill out the Contact Us form to request access credentials.
            Our team will review your request and provide you with login details.
            Thank you for trying out SpeechSmith!
        """)
        return

    load_services_css()
    
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"session_{time.strftime('%Y%m%d%H%M%S')}"
    
    if 'text_filepath' not in st.session_state:
        st.session_state.text_filepath = None
    if 'audio_filepath' not in st.session_state:
        st.session_state.audio_filepath = None
    
    st.markdown('<h1 class="gradient-text">Our Services</h1>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">At speechsmith, we offer a seamless and effective way to refine your speech delivery, ensuring it meets your specific goals and resonates with your audience.</p>', unsafe_allow_html=True)
    
    if not st.session_state.get('is_authenticated', False):
        remaining_uses = 5 - st.session_state.usage_count
        st.info(f"You have {remaining_uses} free trial uses remaining. Please contact us for full access.")
    
    content = """
        <div class="content-section"> 
        <h2>Speech Analysis and Feedback</h2>
        <p>Upload your speech as an audio or video file, and receive comprehensive feedback across several parameters:</p>
        <ul>
            <li><strong>Pronunciation:</strong> Precision scoring and suggestions to enhance clarity.</li>
            <li><strong>Posterior Score:</strong> Analysis of fluency and coherence.</li>
            <li><strong>Semantic Analysis:</strong> Checking the alignment of your speech content with your intended message and audience.</li>
            <li><strong>Words Per Minute (WPM):</strong> Insights on the ideal pace for engaging delivery.</li>
            <li><strong>Articulation Rate:</strong> Evaluating clarity and emphasis on key points.</li>
            <li><strong>Filler Words:</strong> Identifying unnecessary fillers and providing strategies to minimize them.</li>
        </ul>

        <h2>Personalized Improvement Tips</h2>
        <p>Based on the analysis, we provide actionable feedback on how you can enhance specific areas of your speech, whether that's clarity, pace, or vocabulary usage. You'll receive structured advice to help you sound more confident and professional.</p>

        <h2>Script Refinement</h2>
        <p>Receive an edited version of your script that aligns with your requirements and intended audience. Our suggestions will help tailor your content to maximize impact, ensuring that your speech resonates with your listeners.</p>

        <h2>Comprehensive Progress Reports</h2>
        <p>Track your improvement over time! Our platform keeps a record of your past uploads, allowing you to see your progress in metrics like articulation rate, pronunciation, and speech pace. With regular practice, watch your confidence grow with every upload.</p>

        <h2>Speech Crafting for Diverse Scenarios</h2>
        <p>We support users in creating and refining speeches for various purposes, including:</p>
        <ul>
            <li><strong>Debates and Competitions:</strong> Get debate-ready with speech pacing, rebuttal framing, and structured delivery feedback.</li>
            <li><strong>Presentations:</strong> Improve your presentation style for maximum engagement in team meetings, client pitches, or school projects.</li>
            <li><strong>Public Speaking Practice:</strong> For those simply wanting to refine their public speaking, SpeechSmith offers ongoing feedback to strengthen and elevate your speaking style.</li>
        </ul>
        </div>
    """
    st.html(content)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div class="service-card">
                <i class="fas fa-microphone service-icon"></i>
                <h3>AUDIO UPLOAD</h3>
                <p>Easily upload your speech recordings to our platform for comprehensive analysis.</p>
            </div>
            
            <div class="service-card">
                <i class="fas fa-tasks service-icon"></i>
                <h3>CUSTOMIZED SPEECH GOALS</h3>
                <p>Tailor your speech refinement by selecting your target audience and the intent of your speech.</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="service-card">
                <i class="fas fa-comments service-icon"></i>
                <h3>DETAILED FEEDBACK</h3>
                <p>Receive in-depth feedback on your speech, including insights on tone, pacing, and clarity.</p>
            </div>
            
            <div class="service-card">
                <i class="fas fa-edit service-icon"></i>
                <h3>REFORMED SPEECH</h3>
                <p>Get a refined version of your speech that aligns perfectly with your chosen audience and intent.</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<h2 class="gradient-text">Upload Your Speech</h2>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload your audio file", type=['mp3', 'wav', 'mp4'])
    uploaded_document = st.file_uploader("Upload the script as a pdf/word document (optional, but suggested)", type=['pdf', 'docx'])
    
    if uploaded_file:
        st.subheader("Original Speech")
        st.audio(uploaded_file, format='audio/wav')
        st.session_state.original_audio = uploaded_file

    topic_of_speech = ""
    
    if uploaded_file is not None or uploaded_document is not None:
        topic_of_speech = st.text_input("Enter the topic of the speech")
        gender = st.selectbox("Select Gender", ['male', 'female', 'Other', 'Prefer not to say'])
        purpose = st.selectbox("What is the purpose of your speech?", ["Inform", "Persuade/Inspire", "Entertain", "Other"])
        if purpose == "Other":
            purpose = st.text_input("Please specify the purpose")

        audience = st.selectbox("Who is your target audience?", ["Classmates/Colleagues", "Teachers/Professors", "General public", "Other"])
        if audience == "Other":
            audience = st.text_input("Please specify the audience")

        duration = st.selectbox("How long is your speech intended to be?", ["Less than 1 minute", "1-3 minutes", "3-5 minutes", "More than 5 minutes"])
        tone = st.selectbox("What tone do you wish to adopt?", ["Formal", "Informal", "Humorous", "Other"])
        if tone == "Other":
            tone = st.text_input("Please specify the tone")
        
        additional_requirements = st.text_area("Any additional requirements or preferences? (Optional)", height=100)
        
        if st.button("Process Speech"):
            if not purpose or not audience or not duration or not tone:
                st.error("Please fill out all required fields before processing.")
                st.stop()
            
            if not st.session_state.get('is_authenticated', False):
                st.session_state.usage_count += 1
            
            status_container = st.empty()
            
            try:
                status_container.markdown("""
                    <div class="stStatusContainer stInfo">
                        <span class="step-counter">1</span>
                        Transcribing your speech using Gemini...
                    </div>
                """, unsafe_allow_html=True)
                
                if uploaded_file:
                    transcription = transcribe_audio(uploaded_file)
                    if not transcription or not transcription.strip():
                        st.error("No speech detected in the audio file")
                        st.stop()
                    
                    st.session_state.transcription = transcription
                    
                    status_container.markdown("""
                        <div class="stStatusContainer stInfo">
                            <span class="step-counter">2</span>
                            Identifying mispronounced words...
                        </div>
                    """, unsafe_allow_html=True)
                    
                    uploaded_file.seek(0)
                    mispronounced_words = identify_mispronounced_words(uploaded_file, transcription)
                    
                    try:
                        st.info("Generating AI version of your speech...")
                        tts = gTTS(text=transcription, lang='en')
                        ai_audio_io = io.BytesIO()
                        tts.write_to_fp(ai_audio_io)
                        ai_audio_io.seek(0)
                        ai_audio_bytes = ai_audio_io.getvalue()
                        
                        st.session_state.ai_audio_io = ai_audio_io
                        st.session_state.ai_audio_bytes = ai_audio_bytes
                        st.success("AI version generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating AI version: {str(e)}")
                    
                    status_container.markdown("""
                        <div class="stStatusContainer stInfo">
                            <span class="step-counter">3</span>
                            Analyzing speech metrics...
                        </div>
                    """, unsafe_allow_html=True)
                    
                    results = analyze_speech_with_gemini(transcription, topic_of_speech, duration, uploaded_file)
                    if not results:
                        st.error("Failed to analyze speech")
                        st.stop()
                    
                else:
                    transcription = extract_text_from_document(uploaded_document)
                    if not transcription or not transcription.strip():
                        st.error("No text found in the document")
                        st.stop()
                    results = analyze_speech_with_gemini(transcription, topic_of_speech, duration)
                    mispronounced_words = []
                
                status_container.markdown("""
                    <div class="stStatusContainer stInfo">
                        <span class="step-counter">4</span>
                        Generating refined speech and detailed feedback...
                    </div>
                """, unsafe_allow_html=True)
                
                original, refined, _ = process_with_gpt(
                    openai_api_key, transcription, purpose, audience, duration, tone, additional_requirements, topic_of_speech, results
                )
                
                _, _, feedback = process_with_gemini(
                    transcription, purpose, audience, duration, tone, additional_requirements, topic_of_speech, results
                )

                status_container.markdown("""
                    <div class="stStatusContainer stInfo">
                        <span class="step-counter">5</span>
                        Generating and saving refined speech...
                    </div>
                """, unsafe_allow_html=True)
                
                text_filepath = save_processed_data(st.session_state.session_id, 'text', refined)
                st.session_state.text_filepath = text_filepath

                status_container.markdown("""
                    <div class="stStatusContainer stInfo">
                        <span class="step-counter">6</span>
                        Generating audio from refined speech...
                    </div>
                """, unsafe_allow_html=True)
                
                cleaned_speech = re.sub(r'\*\*|\*_pause_\*|_|#|<[^>]*>', '', refined)
                cleaned_speech = cleaned_speech.strip()
                
                if not cleaned_speech:
                    st.error("No text available for audio generation")
                    st.stop()

                tts = gTTS(text=cleaned_speech)
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                audio_io.seek(0)
                audio_base64 = base64.b64encode(audio_io.read()).decode()

                if audio_base64:
                    audio_bytes = base64.b64decode(audio_base64)
                    audio_filepath = save_processed_data(st.session_state.session_id, 'audio', audio_bytes)
                    st.session_state.audio_filepath = audio_filepath

                status_container.markdown("""
                    <div class="stStatusContainer stSuccess">
                        <span class="step-counter">✓</span>
                        Processing complete! Showing results...
                    </div>
                """, unsafe_allow_html=True)

                content = f"""
                <div class="content-section">
                    <h3>Original Transcription</h3>
                    <div class="transcription-container">
                        <div class="transcription-legend">
                            <strong>Legend:</strong><br>
                            <span class="bold-word">Bold words</span> - Words to emphasize<br>
                            <span class="pause-marker">|</span> - Pause in speech<br>
                            <span class="mispronounced">Highlighted words</span> - Words that need pronunciation improvement
                        </div>
                        <div class="transcription-text">
                            {format_transcription_text(transcription, [item['word'] for item in mispronounced_words])}
                        </div>
                    </div>
                    
                    <h3>Refined Speech</h3>
                    {format_transcription_with_emphasis(refined, [item['word'] for item in mispronounced_words])}
                </div>
                {format_detailed_feedback(results, mispronounced_words)}
                """
                st.html(content)
                
                st.markdown("""
                    <style>
                        .mispronounced {
                            background-color: rgba(255, 0, 0, 0.1);
                            padding: 0 2px;
                            border-radius: 2px;
                            color: #ff0000;
                            font-weight: bold;
                        }
                        .transcription-text {
                            white-space: pre-wrap;
                            word-wrap: break-word;
                            font-size: 16px;
                            line-height: 1.6;
                            padding: 15px;
                            background-color: #f8f9fa;
                            border-radius: 5px;
                        }
                    </style>
                """, unsafe_allow_html=True)
                
                if audio_base64:
                    content = """
                        <div class="generate-speech">
                            <h3>Generated Speech Audio</h3>
                        </div>
                        """
                    st.html(content)
                    st.audio(io.BytesIO(audio_bytes), format="audio/wav")
                
                    if st.session_state.get('ai_audio_bytes'):
                        st.subheader("AI Version of Original Speech")
                        try:
                            ai_audio_io = io.BytesIO(st.session_state.ai_audio_bytes)
                            ai_audio_io.seek(0)
                            st.audio(ai_audio_io, format='audio/mp3')
                            
                            download_container = st.container()
                            
                            with download_container:
                                st.markdown(
                                    f'<a href="data:audio/mp3;base64,{base64.b64encode(st.session_state.ai_audio_bytes).decode()}" download="ai_version.mp3" style="text-decoration: none;">'
                                    '<button style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%;">'
                                    'Download AI Version'
                                    '</button>'
                                    '</a>',
                                    unsafe_allow_html=True
                                )
                            
                            with download_container:
                                st.markdown(
                                    f'<a href="data:audio/wav;base64,{audio_base64}" download="refined_speech.wav" style="text-decoration: none;">'
                                    '<button style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%;">'
                                    'Download Refined Speech Audio'
                                    '</button>'
                                    '</a>',
                                    unsafe_allow_html=True
                                )
                        except Exception as e:
                            st.error(f"Error displaying AI audio: {str(e)}")
                            st.write("Debug info - Audio data length:", len(st.session_state.ai_audio_bytes) if st.session_state.get('ai_audio_bytes') else "No audio data")
            
            except Exception as e:
                if not st.session_state.get('is_authenticated', False):
                    st.session_state.usage_count -= 1
                status_container.error(f"An error occurred: {str(e)}")
                st.stop()
            
    if st.session_state.get('results'):
        st.subheader("Analysis Results")
        
        if uploaded_file:
            st.subheader("Original Speech")
            st.audio(uploaded_file, format='audio/wav')
            
            if st.session_state.get('ai_audio_bytes'):
                st.subheader("AI Version of Original Speech")
                try:
                    ai_audio_io = io.BytesIO(st.session_state.ai_audio_bytes)
                    ai_audio_io.seek(0)
                    st.audio(ai_audio_io, format='audio/mp3')
                    st.download_button(
                        label="Download AI Version",
                        data=st.session_state.ai_audio_bytes,
                        file_name="ai_version.mp3",
                        mime="audio/mp3"
                    )
                except Exception as e:
                    st.error(f"Error displaying AI audio: {str(e)}")