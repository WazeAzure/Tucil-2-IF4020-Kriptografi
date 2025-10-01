#!/usr/bin/env python3
"""
mp3_consensus_harness.py

Embed with repetition+interleaving and extract with majority vote (consensus).
Depends on ffmpeg, soundfile, numpy.

Usage examples:
  python3 mp3_consensus_harness.py embed input.mp3 output_stego.mp3 "SECRET" --r 5 --bitplane 0 --bitrate 128k
  python3 mp3_consensus_harness.py extract output_stego.mp3 --r 5 --bitplane 0
"""

import argparse
import numpy as np
import soundfile as sf
import subprocess
import os
import math
import random
from typing import List

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
def text_to_bits(text: str) -> List[int]:
    b = []
    for byte in text.encode("utf-8"):
        for i in range(8):
            b.append((byte >> (7-i)) & 1)
    return b

def bits_to_text(bits: List[int]) -> str:
    # group into bytes MSB-first
    out = []
    for i in range(0, len(bits), 8):
        chunk = bits[i:i+8]
        if len(chunk) < 8: break
        val = 0
        for bit in chunk:
            val = (val << 1) | (bit & 1)
        out.append(val)
    try:
        return bytes(out).decode("utf-8", errors="replace")
    except:
        return bytes(out).decode("latin1", errors="replace")

# -----------------------
# embedding with repetition + interleaving
# -----------------------
def make_redundant_bit_positions(num_samples: int, payload_len_bits: int, r: int, rng_seed: int = None):
    """
    Create positions (sample indices) where each payload bit will be stored r times.
    Returns a list-of-lists positions[bit_index] = [pos1, pos2, ..., pos_r]
    Strategy:
      - Flatten the sample indices and choose positions by random sampling without replacement,
        but ensure spread: we shuffle blocks to interleave.
    """
    if rng_seed is not None:
        random.seed(rng_seed)

    total_slots = num_samples
    slots_needed = payload_len_bits * r
    if slots_needed > total_slots:
        raise ValueError(f"Not enough capacity: need {slots_needed} slots but have {total_slots}")

    # create list of all indices then shuffle
    indices = list(range(total_slots))
    random.shuffle(indices)

    # take first slots_needed indices and distribute them into payload_len_bits groups
    chosen = indices[:slots_needed]
    # we want to spread copies per bit: sample r indices for each bit
    positions = []
    for i in range(payload_len_bits):
        block = chosen[i*r:(i+1)*r]
        positions.append(block)
    return positions

def embed_with_repetition(wav_in: str, wav_out: str, payload_bits: List[int], r: int, bitplane:int=0, rng_seed: int = None):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        data = data[:,0]  # mono
    samples = data.copy()
    num_samples = len(samples)

    positions = make_redundant_bit_positions(num_samples, len(payload_bits), r, rng_seed=rng_seed)

    mask = ~(1 << bitplane)
    for bit_idx, bit in enumerate(payload_bits):
        for pos in positions[bit_idx]:
            samples[pos] = (samples[pos] & mask) | ((bit & 1) << bitplane)

    sf.write(wav_out, samples, sr, subtype="PCM_16")
    return positions  # for debugging/analysis

# -----------------------
# extraction with majority vote
# -----------------------
def extract_with_consensus(wav_in: str, payload_bits_len: int, r: int, bitplane:int=0, positions=None):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        data = data[:,0]
    samples = data.copy()

    num_samples = len(samples)
    # if positions known (embedding time), use them; otherwise, assume deterministic positions
    if positions is None:
        # fallback: use deterministic layout (simple contiguous layout) — unlikely to match embedding
        # so extraction without position map will generally fail unless both agree on RNG seed and method.
        positions = make_redundant_bit_positions(num_samples, payload_bits_len, r, rng_seed=0)

    recovered_bits = []
    for bit_idx in range(payload_bits_len):
        votes = []
        for pos in positions[bit_idx]:
            if pos >= num_samples:
                votes.append(0)
            else:
                votes.append((samples[pos] >> bitplane) & 1)
        # majority vote
        ones = sum(votes)
        zeroes = len(votes) - ones
        recovered_bits.append(1 if ones > zeroes else 0)
    return recovered_bits, positions

# -----------------------
# wrapper: embed->compress->extract and report
# -----------------------
def run_consensus_test(input_mp3: str, message: str, r: int = 3, bitrate: str = "128k", bitplane: int = 0, rng_seed: int = 42):
    # 1. decode
    mp3_to_wav(input_mp3, "original.wav")
    # 2. build payload bits
    bits = text_to_bits(message)
    payload_len = len(bits)
    # 3. produce redundant embed in WAV
    positions = embed_with_repetition("original.wav", "embedded.wav", bits, r, bitplane=bitplane, rng_seed=rng_seed)
    # 4. compress cycle
    wav_to_mp3("embedded.wav", "stego.mp3", bitrate=bitrate)
    mp3_to_wav("stego.mp3", "recovered.wav")
    # 5. extract with consensus (need same positions) 
    recovered_bits, _ = extract_with_consensus("recovered.wav", payload_len, r, bitplane=bitplane, positions=positions)
    # 6. compare and stats
    survived_bits = sum(1 for a,b in zip(bits,recovered_bits) if a==b)
    survival_rate = survived_bits / payload_len * 100
    recovered_text = bits_to_text(recovered_bits)
    print("Payload bits:", payload_len, "r:", r, "bitplane:", bitplane, "bitrate:", bitrate)
    print("Recovered bits equal:", survived_bits, "(", f"{survival_rate:.2f}%", ")")
    print("Recovered text (lossy):")
    print(recovered_text)
    return {
        "payload_bits": payload_len,
        "r": r,
        "bitplane": bitplane,
        "bitrate": bitrate,
        "survived_bits": survived_bits,
        "survival_rate": survival_rate,
        "recovered_text": recovered_text
    }

# -----------------------
# CLI
# -----------------------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    p_embed = sub.add_parser("embed", help="embed and write stego MP3")
    p_embed.add_argument("input_mp3")
    p_embed.add_argument("output_mp3")
    p_embed.add_argument("message")
    p_embed.add_argument("--r", type=int, default=3)
    p_embed.add_argument("--bitrate", default="128k")
    p_embed.add_argument("--bitplane", type=int, default=0)
    p_embed.add_argument("--seed", type=int, default=42)

    p_extract = sub.add_parser("extract", help="extract from stego mp3 (requires positions map)")
    p_extract.add_argument("stego_mp3")
    p_extract.add_argument("--r", type=int, default=3)
    p_extract.add_argument("--bitplane", type=int, default=0)
    p_extract.add_argument("--seed", type=int, default=42)
    # NOTE: For simplicity this tool returns positions in memory when embedding; in real use persist positions to file.

    args = ap.parse_args()
    if args.cmd == "embed":
        # run full pipeline and write out mp3
        mp3_to_wav(args.input_mp3, "original.wav")
        bits = text_to_bits(args.message)
        positions = embed_with_repetition("original.wav", "embedded.wav", bits, args.r, bitplane=args.bitplane, rng_seed=args.seed)
        wav_to_mp3("embedded.wav", args.output_mp3, bitrate=args.bitrate)
        # save positions map for later extraction (simple approach)
        import json
        open(args.output_mp3 + ".pos.json","w").write(json.dumps(positions))
        print("Embedded; positions map written to", args.output_mp3 + ".pos.json")
    elif args.cmd == "extract":
        # load positions map
        import json
        posfile = args.stego_mp3 + ".pos.json"
        if not os.path.exists(posfile):
            print("Position map not found:", posfile)
            print("Cannot reliably extract without the embedding positions.")
            return
        mp3_to_wav(args.stego_mp3, "recovered.wav")
        positions = json.load(open(posfile,"r"))
        # convert list of lists to ints
        positions = [[int(x) for x in lst] for lst in positions]
        # payload length is len(positions)
        recovered_bits, _ = extract_with_consensus("recovered.wav", len(positions), args.r, bitplane=args.bitplane, positions=positions)
        print("Recovered text:")
        print(bits_to_text(recovered_bits))
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
