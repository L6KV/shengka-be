import json
import base64
import io
import tempfile
import os
from io import BytesIO
from pydub import AudioSegment
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from funasr import AutoModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from LLM_utils.LLM_Connection import get_my_deepseek
from OLogger.MyLogger import myLogger
from pydantic import BaseModel
from typing import List
from .volcengine_tts_api import convert_text_to_speech

# Initialize FunASR model for STT
stt_model = AutoModel(model="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                  vad_model="fsmn-vad",
                  punc_model="ct-punc-c")

dpRouter = APIRouter(
    prefix="/dp",
    tags=["dp"],
    responses={404: {"description": "Not found"}},
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: float = 1.0

@dpRouter.post("/voice_chat")
async def dp_voice_chat(
    audio_file: UploadFile = File(...),
    history: str = Form("[]"),  # Receive history as a JSON string
    voice: str = Form("zh_female_graceful")
):
    # 1. Parse history from Form data
    try:
        messages = json.loads(history)
        if not isinstance(messages, list):
            raise ValueError("History must be a list of objects.")
        for msg in messages:
            if not all(k in msg for k in ("role", "content")):
                raise ValueError("Each message in history must have 'role' and 'content' keys.")
    except (json.JSONDecodeError, ValueError) as e:
        myLogger.error(f"Invalid history format: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid history format: {e}")

    # 1. Speech-to-Text
    try:
        audio_bytes = await audio_file.read()

        # Use pydub to process audio
        audio = AudioSegment.from_file(BytesIO(audio_bytes))

        # Convert to 16kHz, mono
        audio = audio.set_frame_rate(16000)
        audio = audio.set_channels(1)

        # Export as a temporary WAV file for FunASR
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
            audio.export(tmp_wav.name, format="wav")
            tmp_wav_path = tmp_wav.name

        try:
            rec_result = stt_model.generate(tmp_wav_path, batch_size_s=15)
        finally:
            # Clean up the temporary file
            if os.path.exists(tmp_wav_path):
                os.remove(tmp_wav_path)
        myLogger.info(f"FunASR recognition result: {rec_result}")
        user_text = rec_result[0].get("text", "") if rec_result and isinstance(rec_result, list) and len(rec_result) > 0 and isinstance(rec_result[0], dict) else ""
        if not user_text:
            raise ValueError("STT failed, returned empty text.")
        messages.append({"role": "user", "content": user_text})
    except FileNotFoundError as e:
        myLogger.error(f"STT Error - File Not Found: {e}. This is likely due to a missing ffmpeg dependency for pydub. Please ensure ffmpeg is installed and in your system's PATH.", exc_info=True)
        raise HTTPException(status_code=500, detail="Speech-to-Text failed: A required file was not found. This may be caused by a missing ffmpeg installation. Please check server logs for details.")
    except ValueError as e:
        if "STT failed" in str(e):
            myLogger.warning(f"STT returned empty text: {e}")
            raise HTTPException(status_code=400, detail="Could not transcribe audio. The audio may be silent or invalid.")
        else:
            myLogger.error(f"STT Error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Speech-to-Text failed: {e}")
    except Exception as e:
        myLogger.error(f"STT Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Speech-to-Text failed: {e}")

    # 3. Get LLM response (non-streaming)
    try:
        my_deepseek = get_my_deepseek()
        response = my_deepseek.client.chat.completions.create(
            model=my_deepseek.dp_chat_model,
            messages=messages,
            stream=False,
        )
        assistant_text = response.choices[0].message.content
        if not assistant_text:
            raise ValueError("LLM returned empty content.")
    except Exception as e:
        myLogger.error(f"LLM Error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM call failed: {str(e)}")

    # 4. Generate TTS audio using Volcengine TTS
    assistant_audio = None
    try:
        voice_type = os.getenv("VOLCENGINE_VOICE_TYPE", "zh_female_cancan_mars_bigtts")
        assistant_audio = await convert_text_to_speech(assistant_text, voice_type)
        if assistant_audio:
            myLogger.info("TTS conversion successful")
        else:
            myLogger.warning("TTS conversion failed, returning text only")
    except Exception as e:
        myLogger.error(f"TTS Error: {e}")
        assistant_audio = None

    return JSONResponse(content={
        "user_text": user_text,
        "assistant_text": assistant_text,
        "assistant_audio": assistant_audio,
    })


@dpRouter.post("/stream_chat")
async def dp_stream_chat(request: ChatRequest):
    def generate():
        try:
            my_deepseek = get_my_deepseek()
            response = my_deepseek.client.chat.completions.create(
                model=my_deepseek.dp_chat_model,
                messages=[{"role": msg.role, "content": msg.content} for msg in request.messages],
                stream=True,
                temperature=request.temperature
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield json.dumps({"content": chunk.choices[0].delta.content}) + "\n"
        except Exception as e:
            myLogger.error(f"Stream Chat Error: {e}")
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(generate(), media_type="application/json")
