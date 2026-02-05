
import os
import azure.cognitiveservices.speech as speechsdk
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureGrader:
    def __init__(self, speech_key, service_region):
        if not speech_key or not service_region:
            raise ValueError("API Key and Region are required.")
            
        self.speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        self.speech_config.speech_recognition_language = 'ko-KR'
        
        # Set output format to detailed to get phonemes if needed (though PronunciationAssessmentConfig handles most)
        self.speech_config.output_format = speechsdk.OutputFormat.Detailed

    def grade(self, audio_file_path, reference_text):
        """
        Evaluates the pronunciation of the audio file against the reference text.
        Returns a dictionary with scores and details.
        
        :param audio_file_path: Absolute path to the WAV file (16kHz, 16bit, Mono recommended)
        :param reference_text: The Korean text to evaluate against
        """
        logger.info(f"Grading audio: {audio_file_path} against '{reference_text}'")
        
        if not os.path.exists(audio_file_path):
            return {"status": "error", "message": "Audio file not found."}

        # Configure audio input
        audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)

        # Initialize recognizer
        recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=audio_config)

        # Configure pronunciation assessment parameters (matching K-Pronouncer settings)
        # grading_system=HundredMark, granularity=Phoneme, enable_miscue=True
        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True
        )
        pronunciation_config.apply_to(recognizer)

        try:
            # Perform recognition (Blocking for simplicity in this script, or use async.get())
            result_future = recognizer.recognize_once_async()
            result = result_future.get()

            # Process result
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                pronunciation_result = speechsdk.PronunciationAssessmentResult(result)
                
                # Basic Scores
                scores = {
                    "accuracy": pronunciation_result.accuracy_score,
                    "fluency": pronunciation_result.fluency_score,
                    "completeness": pronunciation_result.completeness_score,
                    "pronunciation": pronunciation_result.pronunciation_score
                }

                # Word-level details
                word_details = []
                for word in pronunciation_result.words:
                    word_info = {
                        "word": word.word,
                        "accuracy": word.accuracy_score,
                        "error_type": word.error_type # None, Omission, Insertion, Mispronunciation
                    }
                    word_details.append(word_info)

                logger.info(f"Grading successful. Score: {scores['accuracy']}")
                return {
                    "status": "success",
                    "scores": scores,
                    "word_details": word_details,
                    "recognized_text": result.text
                }
                
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("No speech recognized.")
                return {"status": "error", "message": "음성을 인식할 수 없습니다. (No Match)"}
                
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                logger.error(f"Recognition canceled: {cancellation_details.reason} - {cancellation_details.error_details}")
                return {
                    "status": "error", 
                    "message": f"인식 취소됨/오류: {cancellation_details.reason}"
                }
                
            else:
                return {"status": "error", "message": "알 수 없는 오류 발생"}
                
        except Exception as e:
            logger.exception("Exception during grading")
            return {"status": "error", "message": str(e)}
