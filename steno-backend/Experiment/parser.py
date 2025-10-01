#!/usr/bin/env python3
"""
mp3_parser.py - Minimal MP3 frame parser in Python

Scans an MP3 file, detects frame headers, and extracts
frame metadata + raw bytes for inspection.
"""

import sys
import struct

# Bitrate lookup table (MPEG1 Layer III)
BITRATES = {
    0b0001: 32, 0b0010: 40, 0b0011: 48, 0b0100: 56,
    0b0101: 64, 0b0110: 80, 0b0111: 96, 0b1000: 112,
    0b1001: 128, 0b1010: 160, 0b1011: 192, 0b1100: 224,
    0b1101: 256, 0b1110: 320,
}

# Sampling rate lookup (MPEG1 only here)
SAMPLERATES = {
    0b00: 44100,
    0b01: 48000,
    0b10: 32000,
}

def parse_frame_header(header_bytes):
    """Parse a 4-byte MP3 frame header"""
    b1, b2, b3, b4 = struct.unpack(">BBBB", header_bytes)

    # Sync word check (11 bits)
    sync = (b1 << 3) | (b2 >> 5)
    if sync != 0x7FF:
        return None

    mpeg_version_id = (b2 >> 3) & 0b11   # 2 bits
    layer_index     = (b2 >> 1) & 0b11   # 2 bits
    protection_bit  = b2 & 0b1

    bitrate_index   = (b3 >> 4) & 0b1111 # 4 bits
    sampling_index  = (b3 >> 2) & 0b11   # 2 bits
    padding_bit     = (b3 >> 1) & 0b1
    private_bit     = b3 & 0b1

    channel_mode    = (b4 >> 6) & 0b11   # 2 bits

    # Lookup bitrate and samplerate (simplified: only MPEG1 Layer III)
    bitrate = BITRATES.get(bitrate_index, None)
    samplerate = SAMPLERATES.get(sampling_index, None)

    if not bitrate or not samplerate:
        return None

    # Frame length formula (MPEG1 Layer III)
    frame_length = int((144000 * bitrate * 1000) // samplerate + padding_bit)

    return {
        "mpeg_version_id": mpeg_version_id,
        "layer_index": layer_index,
        "protection_bit": protection_bit,
        "bitrate": bitrate * 1000,
        "samplerate": samplerate,
        "padding": padding_bit,
        "channel_mode": channel_mode,
        "frame_length": frame_length
    }


def parse_mp3(filename, max_frames=10):
    """Parse MP3 file frame by frame"""
    with open(filename, "rb") as f:
        data = f.read()

    frames = []
    i = 0
    while i < len(data) - 4 and len(frames) < max_frames:
        header = data[i:i+4]
        parsed = parse_frame_header(header)
        if parsed:
            frame_length = parsed["frame_length"]
            frame_bytes = data[i:i+frame_length]

            frames.append({
                "pos": i,
                "header": parsed,
                "raw": frame_bytes
            })

            # Move to next frame
            i += frame_length
        else:
            i += 1

    return frames


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mp3_parser.py input.mp3")
        sys.exit(1)

    filename = sys.argv[1]
    frames = parse_mp3(filename, max_frames=5)

    for idx, frame in enumerate(frames):
        h = frame["header"]
        print(f"\nFrame {idx} @ byte {frame['pos']}:")
        print(f"  Bitrate: {h['bitrate']} bps")
        print(f"  Samplerate: {h['samplerate']} Hz")
        print(f"  Channel Mode: {h['channel_mode']}")
        print(f"  Frame length: {h['frame_length']} bytes")
        print(f"  Raw bytes (first 16): {frame['raw'][:16].hex()}")

