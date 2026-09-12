"""Same-session Wyze talkback (camera speaker).

Audio is ingested as µ-law 8 kHz (or PCM16LE converted to µ-law) and sent
with avSendAudioData on the existing TUTK AV channel. See GitHub issue #533.
"""
from __future__ import annotations

import audioop
import logging
import os
import time

from wyzecam.tutk.tutk import FrameInfo3Struct

logger = logging.getLogger(__name__)

CODEC_ID_MULAW = 137
TALK_FRAME_BYTES = 320  # 40 ms at 8 kHz, 8-bit
ULAW_SILENCE = 0xFF


def talk_fifo_path(uri: str) -> str:
    return f"/tmp/{uri}_talk.pipe"


def chunk_mulaw(payload: bytes, frame_bytes: int = TALK_FRAME_BYTES) -> list[bytes]:
    if not payload:
        return []
    frames = []
    for i in range(0, len(payload), frame_bytes):
        chunk = payload[i : i + frame_bytes]
        if len(chunk) < frame_bytes:
            chunk = chunk + bytes([ULAW_SILENCE]) * (frame_bytes - len(chunk))
        frames.append(chunk)
    return frames


def pcm16le_to_mulaw(pcm: bytes) -> bytes:
    if len(pcm) % 2:
        pcm = pcm[:-1]
    if not pcm:
        return b""
    return audioop.lin2ulaw(pcm, 2)


def audio_frame_info(
    *,
    codec_id: int,
    frame_no: int,
    frame_len: int,
    timestamp: int | None = None,
) -> FrameInfo3Struct:
    now = time.time() if timestamp is None else float(timestamp)
    info = FrameInfo3Struct()
    info.codec_id = codec_id
    info.is_keyframe = 1
    info.cam_index = 0
    info.online_num = 1
    info.framerate = 25
    info.frame_size = 0
    info.bitrate = 0
    info.timestamp = int(now)
    info.timestamp_ms = int((now % 1) * 1000)
    info.frame_len = frame_len
    info.frame_no = frame_no
    return info


def ingest_talk_payload(uri: str, raw: bytes, content_type: str = "") -> int:
    """Write talk audio to the camera FIFO. Returns bytes written (µ-law)."""
    if not raw:
        return 0
    ctype = (content_type or "").lower()
    if "l16" in ctype or "pcm" in ctype or "s16" in ctype:
        raw = pcm16le_to_mulaw(raw)
    path = talk_fifo_path(uri)
    fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
    try:
        return os.write(fd, raw)
    finally:
        os.close(fd)
