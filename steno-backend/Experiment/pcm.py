#!/usr/bin/env python3
"""
mp3_pcm_rs_stego.py

PCM-intermediary + Reed–Solomon steganography for MP3.

Dependencies:
  - ffmpeg (system)
  - pip install numpy soundfile reedsolo

Main idea:
  1) mp3 -> wav (PCM int16)
  2) RS-encode message bytes -> encoded_bytes
  3) bits = bytes -> bitlist
  4) choose randomized positions across PCM samples and embed bits into the lowest `bits_per_sample` bits
     (we pack bits sequentially across samples; each sample contributes up to bits_per_sample bits)
  5) write modified wav -> encode back to mp3
  6) to extract: decode mp3->wav, use saved positions to read bits -> bytes -> RS decode

Notes:
  - For simplicity, we operate on the first channel only (mono). For stereo you can modify code to interleave across channels.
  - The script requires writing a positions map: output_mp3 + ".pos.json".
  - bits_per_sample controls how many LSBs of each sample are used (1..3 recommended).
  - nsym is Reed–Solomon parity bytes (higher => more correction, less capacity).
"""

import argparse
import subprocess
import json
import os
import math
import random
from typing import List
import numpy as np
import soundfile as sf
import reedsolo

# -------------------------
# ffmpeg helpers
# -------------------------
def mp3_to_wav(mp3_path: str, wav_path: str):
    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, wav_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def wav_to_mp3(wav_path: str, mp3_path: str, bitrate: str = "128k"):
    subprocess.run(["ffmpeg", "-y", "-i", wav_path, "-b:a", bitrate, mp3_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# -------------------------
# Bit utilities
# -------------------------
def bytes_to_bits(b: bytes) -> List[int]:
    bits = []
    for byte in b:
        for i in range(8):
            bits.append((byte >> (7 - i)) & 1)
    return bits

def bits_to_bytes(bits: List[int]) -> bytes:
    out = []
    for i in range(0, len(bits), 8):
        chunk = bits[i:i+8]
        if len(chunk) < 8:
            break
        v = 0
        for bit in chunk:
            v = (v << 1) | (bit & 1)
        out.append(v)
    return bytes(out)

# -------------------------
# Position selection (randomized & interleaved)
# -------------------------
def pick_positions(num_samples: int, total_bits: int, bits_per_sample: int, seed: int = None) -> List[int]:
    """
    Return a flattened list of sample indices length == total_bits.
    Each sample index appears at most bits_per_sample times (we treat each sample as bits_per_sample slots).
    Strategy:
      - Make a list of slots = [(sample_idx, slot_index_within_sample)] but only sample_idx is needed for mapping.
      - Shuffle and pick first total_bits slots.
      - We'll store only sample indices (positions) aligning with sequence of bits.
    """
    if seed is not None:
        random.seed(seed)

    total_slots = num_samples * bits_per_sample
    if total_bits > total_slots:
        raise ValueError(f"Not enough capacity: need {total_bits} bits but only have {total_slots} slots "
                         f"({num_samples} samples x {bits_per_sample} bits/sample).")

    # create list of sample indices repeated bits_per_sample times
    slots = []
    for s in range(num_samples):
        for _ in range(bits_per_sample):
            slots.append(s)
    random.shuffle(slots)
    chosen = slots[:total_bits]
    return chosen  # length == total_bits

# -------------------------
# Embed / Extract
# -------------------------
def embed_bits_into_wav(wav_in: str, wav_out: str, bits: List[int], bits_per_sample: int, seed: int = None):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        # use first channel only to simplify
        data = data[:, 0]
    samples = data.copy()
    num_samples = len(samples)

    positions = pick_positions(num_samples, len(bits), bits_per_sample, seed=seed)

    # embed sequentially: for i, pick sample idx = positions[i], and write into the next LSB slot available in that sample.
    # We'll write bits so that for each sample multiple bits occupy the lower bits: we fill LSBs cumulatively.
    # To ensure reproducibility we'll embed per-bit in the order of positions list; extraction uses same list.
    for i, bit in enumerate(bits):
        samp_idx = positions[i]
        # determine which of the bits_per_sample slot this is for that sample: count occurrences before i for same samp_idx
        # compute k = occurrence index in positions[:i+1] of samp_idx - 1 (0-based)
        # optimization: maintain a dict of counters
        # but simplest: we'll compute using a running counter map
        pass

    # To implement efficiently, compute counters:
    counters = {}
    for i, bit in enumerate(bits):
        samp_idx = positions[i]
        k = counters.get(samp_idx, 0)  # which bit slot in this sample
        if k >= bits_per_sample:
            # shouldn't happen as pick_positions ensured capacity
            continue
        # set bit at position k (we place first occurrence as LSB (k=0), next as bit1 (k=1), etc.)
        mask = ~(1 << k) & 0xFFFF
        samples[samp_idx] = (samples[samp_idx] & mask) | ((bit & 1) << k)
        counters[samp_idx] = k + 1

    # write wav_out
    sf.write(wav_out, samples, sr, subtype="PCM_16")
    return positions, num_samples, sr

def extract_bits_from_wav(wav_in: str, total_bits: int, bits_per_sample: int, positions: List[int]):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        data = data[:, 0]
    samples = data
    bits = []
    # extraction uses exact same positions list and the same ordering of per-sample occurrences (we use occurrence-order)
    # we must track counters to know which bit slot to read for each occurrence of a sample index
    counters = {}
    for i in range(total_bits):
        samp_idx = positions[i]
        k = counters.get(samp_idx, 0)
        if k >= bits_per_sample:
            bits.append(0)
        else:
            b = (int(samples[samp_idx]) >> k) & 1
            bits.append(b)
        counters[samp_idx] = k + 1
    return bits

# -------------------------
# High-level RS embed/extract
# -------------------------
def embed_message_pcm_rs(input_mp3: str, output_mp3: str, message: str,
                         nsym: int = 32, bits_per_sample: int = 1,
                         bitrate: str = "128k", seed: int = 42):
    # decode to wav
    tmp_wav = "tmp_original.wav"
    tmp_emb = "tmp_embedded.wav"
    mp3_to_wav(input_mp3, tmp_wav)

    rs = reedsolo.RSCodec(nsym)
    bmsg = message.encode("utf-8")
    encoded = rs.encode(bmsg)  # bytes
    encoded_len = len(encoded)

    bits = bytes_to_bits(encoded)
    total_bits = len(bits)

    # embed
    positions, num_samples, sr = embed_bits_into_wav(tmp_wav, tmp_emb, bits, bits_per_sample, seed=seed)

    # write mp3
    wav_to_mp3(tmp_emb, output_mp3, bitrate=bitrate)

    # save metadata: positions list and encoded length + nsym + bits_per_sample + sample_count
    posfile = output_mp3 + ".pos.json"
    meta = {
        "positions": positions,
        "encoded_len": encoded_len,
        "nsym": nsym,
        "bits_per_sample": bits_per_sample,
        "num_samples": num_samples,
        "seed": seed
    }
    with open(posfile, "w") as f:
        json.dump(meta, f)
    print(f"[+] Embedded message ({len(message)} bytes) -> RS-encoded {encoded_len} bytes, bits={total_bits}")
    print(f"[+] Wrote stego MP3: {output_mp3} and positions map {posfile}")

def extract_message_pcm_rs(stego_mp3: str, max_encoded_bytes: int = 65536):
    posfile = stego_mp3 + ".pos.json"
    if not os.path.exists(posfile):
        raise FileNotFoundError(f"Positions map not found: {posfile}")

    meta = json.load(open(posfile, "r"))
    positions = meta["positions"]
    encoded_len = meta["encoded_len"]
    nsym = meta["nsym"]
    bits_per_sample = meta["bits_per_sample"]
    total_bits = encoded_len * 8

    # decode stego mp3 -> wav
    tmp_recovered_wav = "tmp_recovered.wav"
    mp3_to_wav(stego_mp3, tmp_recovered_wav)

    # extract bits
    bits = extract_bits_from_wav(tmp_recovered_wav, total_bits, bits_per_sample, positions)
    raw_bytes = bits_to_bytes(bits)
    # ensure we only pass encoded_len bytes to RS decode
    raw_trim = raw_bytes[:encoded_len]
    rs = reedsolo.RSCodec(nsym)
    try:
        decoded = rs.decode(raw_trim)[0]
        msg = decoded.decode("utf-8", errors="replace")
        print("[+] RS decode successful.")
        print("Recovered message:")
        print(msg)
    except Exception as e:
        print("[-] RS decode failed:", e)
        # still show hexdump of raw_trim for debugging
        print("[*] Raw encoded bytes (hex):", raw_trim.hex()[:400])

# -------------------------
# CLI
# -------------------------
def main():
    ap = argparse.ArgumentParser(description="PCM intermediary + RS stego for MP3")
    sub = ap.add_subparsers(dest="cmd")

    p_emb = sub.add_parser("embed", help="Embed message into MP3 (produces stego MP3 and .pos.json)")
    p_emb.add_argument("input_mp3")
    p_emb.add_argument("output_mp3")
    p_emb.add_argument("message")
    p_emb.add_argument("--nsym", type=int, default=32, help="RS parity bytes")
    p_emb.add_argument("--bits-per-sample", type=int, default=1, choices=[1,2,3], help="how many LSB planes per sample")
    p_emb.add_argument("--bitrate", default="128k")
    p_emb.add_argument("--seed", type=int, default=42)

    p_ext = sub.add_parser("extract", help="Extract message using .pos.json map")
    p_ext.add_argument("stego_mp3")

    args = ap.parse_args()
    if args.cmd == "embed":
        embed_message_pcm_rs(args.input_mp3, args.output_mp3, args.message,
                             nsym=args.nsym, bits_per_sample=args.bits_per_sample,
                             bitrate=args.bitrate, seed=args.seed)
    elif args.cmd == "extract":
        extract_message_pcm_rs(args.stego_mp3)
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
