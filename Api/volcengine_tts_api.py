#!/usr/bin/env python3
"""
火山引擎TTS API模块
基于WebSocket双向通信实现文本转语音功能
"""

import asyncio
import copy
import json
import logging
import uuid
import base64
from typing import Optional, Dict, Any
import os

import websockets

from .volcengine_tts_protocols import (
    EventType,
    MsgType,
    finish_connection,
    finish_session,
    receive_message,
    start_connection,
    start_session,
    task_request,
    wait_for_event,
)

logger = logging.getLogger(__name__)


class VolcengineTTSAPI:
    """火山引擎TTS API类"""
    
    def __init__(self, appid: str, access_token: str, endpoint: str = None):
        """
        初始化TTS API
        
        Args:
            appid: 应用ID
            access_token: 访问令牌
            endpoint: WebSocket端点URL
        """
        self.appid = appid
        self.access_token = access_token
        self.endpoint = endpoint or "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
        
    def get_resource_id(self, voice: str) -> str:
        """根据声音类型获取资源ID"""
        if voice.startswith("S_"):
            return "volc.megatts.default"
        return "volc.service_type.10029"
    
    async def convert_text_to_speech(
        self, 
        text: str, 
        voice_type: str = "zh_female_cancan_mars_bigtts",
        encoding: str = "mp3",
        sample_rate: int = 24000
    ) -> Optional[bytes]:
        """
        将文本转换为语音
        
        Args:
            text: 要转换的文本
            voice_type: 声音类型
            encoding: 音频编码格式
            sample_rate: 采样率
            
        Returns:
            音频数据的字节流，如果失败返回None
        """
        try:
            # 连接WebSocket服务器
            headers = {
                "X-Api-App-Key": self.appid,
                "X-Api-Access-Key": self.access_token,
                "X-Api-Resource-Id": self.get_resource_id(voice_type),
                "X-Api-Connect-Id": str(uuid.uuid4()),
            }
            
            logger.info(f"Connecting to {self.endpoint}")
            websocket = await websockets.connect(
                self.endpoint, 
                additional_headers=headers, 
                max_size=10 * 1024 * 1024
            )
            
            try:
                # 开始连接
                await start_connection(websocket)
                await wait_for_event(
                    websocket, MsgType.FullServerResponse, EventType.ConnectionStarted
                )
                
                # 准备请求参数
                base_request = {
                    "user": {
                        "uid": str(uuid.uuid4()),
                    },
                    "namespace": "BidirectionalTTS",
                    "req_params": {
                        "speaker": voice_type,
                        "audio_params": {
                            "format": encoding,
                            "sample_rate": sample_rate,
                            "enable_timestamp": True,
                        },
                        "additions": json.dumps({
                            "disable_markdown_filter": False,
                        }),
                    },
                }
                
                # 开始会话
                start_session_request = copy.deepcopy(base_request)
                start_session_request["event"] = EventType.StartSession
                session_id = str(uuid.uuid4())
                
                await start_session(
                    websocket, 
                    json.dumps(start_session_request).encode(), 
                    session_id
                )
                await wait_for_event(
                    websocket, MsgType.FullServerResponse, EventType.SessionStarted
                )
                
                # 发送文本进行合成
                synthesis_request = copy.deepcopy(base_request)
                synthesis_request["event"] = EventType.TaskRequest
                synthesis_request["req_params"]["text"] = text
                
                await task_request(
                    websocket, 
                    json.dumps(synthesis_request).encode(), 
                    session_id
                )
                
                # 结束会话
                await finish_session(websocket, session_id)
                
                # 接收音频数据
                audio_data = bytearray()
                while True:
                    msg = await receive_message(websocket)
                    
                    if msg.type == MsgType.FullServerResponse:
                        if msg.event == EventType.SessionFinished:
                            break
                    elif msg.type == MsgType.AudioOnlyServer:
                        audio_data.extend(msg.payload)
                    else:
                        logger.warning(f"Unexpected message: {msg}")
                
                return bytes(audio_data) if audio_data else None
                
            finally:
                # 结束连接
                await finish_connection(websocket)
                await wait_for_event(
                    websocket, MsgType.FullServerResponse, EventType.ConnectionFinished
                )
                await websocket.close()
                
        except Exception as e:
            logger.error(f"TTS conversion failed: {e}")
            return None


# 全局TTS实例
_tts_instance: Optional[VolcengineTTSAPI] = None


def get_tts_instance() -> Optional[VolcengineTTSAPI]:
    """获取TTS实例"""
    global _tts_instance
    
    if _tts_instance is None:
        # 从环境变量读取配置
        appid = os.getenv("VOLCENGINE_APPID")
        access_token = os.getenv("VOLCENGINE_ACCESS_TOKEN")
        
        if appid and access_token:
            _tts_instance = VolcengineTTSAPI(appid, access_token)
        else:
            logger.warning("Volcengine TTS credentials not found in environment variables")
            
    return _tts_instance


async def convert_text_to_speech(
    text: str, 
    voice_type: str = "zh_female_cancan_mars_bigtts"
) -> Optional[str]:
    """
    将文本转换为语音并返回base64编码的音频数据
    
    Args:
        text: 要转换的文本
        voice_type: 声音类型
        
    Returns:
        base64编码的音频数据，如果失败返回None
    """
    tts = get_tts_instance()
    if not tts:
        logger.error("TTS instance not available")
        return None
        
    try:
        audio_bytes = await tts.convert_text_to_speech(text, voice_type)
        if audio_bytes:
            return base64.b64encode(audio_bytes).decode('utf-8')
        return None
    except Exception as e:
        logger.error(f"Failed to convert text to speech: {e}")
        return None