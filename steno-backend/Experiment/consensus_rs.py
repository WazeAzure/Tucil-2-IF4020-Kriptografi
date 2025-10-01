#!/usr/bin/env python3
"""
mp3_rs_harness.py
Reed–Solomon protected steganography in MP3 LSB plane.
Depends on: ffmpeg, numpy, soundfile, reedsolo
"""

import argparse
import numpy as np
import soundfile as sf
import subprocess
import os
import reedsolo

# -----------------------
# ffmpeg helpers
# -----------------------
def mp3_to_wav(mp3_path, wav_path):
    subprocess.run(["ffmpeg","-y","-i",mp3_path,wav_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def wav_to_mp3(wav_path, mp3_path, bitrate="128k"):
    subprocess.run(["ffmpeg","-y","-i",wav_path,"-b:a",bitrate,mp3_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# -----------------------
# bit utilities
# -----------------------
def bytes_to_bits(b: bytes):
    bits = []
    for byte in b:
        for i in range(8):
            bits.append((byte >> (7-i)) & 1)
    return bits

def bits_to_bytes(bits):
    out = []
    for i in range(0, len(bits), 8):
        chunk = bits[i:i+8]
        if len(chunk) < 8: break
        val = 0
        for bit in chunk:
            val = (val << 1) | bit
        out.append(val)
    return bytes(out)

# -----------------------
# LSB embed/extract
# -----------------------
def embed_bits(wav_in, wav_out, bits, bitplane=0):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        data = data[:,0]
    samples = data.copy()

    mask = ~(1 << bitplane)
    for i, bit in enumerate(bits):
        if i >= len(samples):
            break
        samples[i] = (samples[i] & mask) | ((bit & 1) << bitplane)

    sf.write(wav_out, samples, sr, subtype="PCM_16")

def extract_bits(wav_in, n_bits, bitplane=0):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        data = data[:,0]
    samples = data.copy()

    bits = []
    for i in range(min(n_bits, len(samples))):
        bits.append((samples[i] >> bitplane) & 1)
    return bits

# -----------------------
# RS protected embed/extract
# -----------------------
def embed_message_rs(input_mp3, output_mp3, message, nsym=32, bitrate="128k", bitplane=0):
    mp3_to_wav(input_mp3, "tmp_original.wav")

    rs = reedsolo.RSCodec(nsym)
    encoded = rs.encode(message.encode("utf-8"))

    bits = bytes_to_bits(encoded)
    embed_bits("tmp_original.wav", "tmp_embedded.wav", bits, bitplane=bitplane)

    wav_to_mp3("tmp_embedded.wav", output_mp3, bitrate=bitrate)
    print(f"[+] Embedded message of {len(message)} chars with RS({len(encoded)},{len(encoded)-nsym})")

def extract_message_rs(stego_mp3, nsym=32, bitplane=0, max_bytes=2048):
    mp3_to_wav(stego_mp3, "tmp_recovered.wav")

    # Extract enough bits to cover max_bytes
    bits = extract_bits("tmp_recovered.wav", max_bytes*8, bitplane=bitplane)
    raw_bytes = bits_to_bytes(bits)

    rs = reedsolo.RSCodec(nsym)
    try:
        decoded = rs.decode(raw_bytes)[0]
        print("[+] Decoded message:", decoded.decode("utf-8", errors="replace"))
    except reedsolo.ReedSolomonError as e:
        print("[-] RS decode failed:", e)

# -----------------------
# CLI
# -----------------------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    p_embed = sub.add_parser("embed")
    p_embed.add_argument("input_mp3")
    p_embed.add_argument("output_mp3")
    p_embed.add_argument("message")
    p_embed.add_argument("--nsym", type=int, default=32)
    p_embed.add_argument("--bitrate", default="128k")
    p_embed.add_argument("--bitplane", type=int, default=0)

    p_extract = sub.add_parser("extract")
    p_extract.add_argument("stego_mp3")
    p_extract.add_argument("--nsym", type=int, default=32)
    p_extract.add_argument("--bitplane", type=int, default=0)
    p_extract.add_argument("--max_bytes", type=int, default=2048)

    args = ap.parse_args()

    if args.cmd == "embed":
        embed_message_rs(args.input_mp3, args.output_mp3, args.message,
                         nsym=args.nsym, bitrate=args.bitrate, bitplane=args.bitplane)
    elif args.cmd == "extract":
        extract_message_rs(args.stego_mp3, nsym=args.nsym,
                           bitplane=args.bitplane, max_bytes=args.max_bytes)
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
