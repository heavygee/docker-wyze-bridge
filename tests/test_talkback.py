"""Talkback helpers — protocol packing and frame chunking (no camera)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))

from wyzecam.tutk.tutk import FrameInfo3Struct
from wyzecam.tutk.tutk_protocol import K10010SetReturnAudio, decode


def test_return_audio_on_encodes_media_type_3():
    msg = K10010SetReturnAudio(1)
    header, payload = decode(msg.encode())
    assert header.code == 10010
    assert payload == bytes([3, 1])


def test_return_audio_off_encodes_disabled():
    msg = K10010SetReturnAudio(2)
    _, payload = decode(msg.encode())
    assert payload == bytes([3, 2])


def test_chunk_mulaw_splits_and_pads():
    from wyzebridge.talkback import TALK_FRAME_BYTES, chunk_mulaw

    payload = b"\x7f" * (TALK_FRAME_BYTES + 10)
    frames = chunk_mulaw(payload)
    assert len(frames) == 2
    assert len(frames[0]) == TALK_FRAME_BYTES
    assert len(frames[1]) == TALK_FRAME_BYTES
    assert frames[1][10:] == b"\xff" * (TALK_FRAME_BYTES - 10)


def test_audio_frame_info_mulaw():
    from wyzebridge.talkback import CODEC_ID_MULAW, audio_frame_info

    info = audio_frame_info(codec_id=CODEC_ID_MULAW, frame_no=7, frame_len=320)
    assert isinstance(info, FrameInfo3Struct)
    assert info.codec_id == 137
    assert info.frame_no == 7
    assert info.frame_len == 320
    assert info.is_keyframe == 1


def test_talk_fifo_path():
    from wyzebridge.talkback import talk_fifo_path

    assert talk_fifo_path("living-room-cam") == "/tmp/living-room-cam_talk.pipe"


def test_pcm16le_to_mulaw_length():
    from wyzebridge.talkback import pcm16le_to_mulaw

    pcm = b"\x00\x00" * 80
    ulaw = pcm16le_to_mulaw(pcm)
    assert len(ulaw) == 80
