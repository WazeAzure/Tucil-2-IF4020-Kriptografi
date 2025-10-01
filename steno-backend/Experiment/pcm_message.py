#!/usr/bin/env python3
"""
pcm_message_test.py

Embed a real UTF-8 message into PCM LSB planes, round-trip via MP3, and measure recovery.

Usage:
  Embed:
    python3 pcm_message_test.py embed input.mp3 out.mp3 "SECRET MESSAGE" --bits-per-sample 1 --bitrate 128k --seed 42
  Extract & test:
    python3 pcm_message_test.py extract out.mp3 --bits-per-sample 1

This script:
 - converts message -> bits (MSB-first per byte)
 - embeds bits sequentially into the chosen bits_per_sample planes, LSB-first within each sample (k=0..bits_per_sample-1)
 - writes positions map to out.mp3.pos.json so extraction can be deterministic
 - extracts bits from round-tripped decoded WAV and reconstructs bytes
 - prints bitwise and bytewise statistics and shows recovered string (lossy)
"""
import argparse, subprocess, json, os, random
from typing import List
import soundfile as sf
import numpy as np
import math
import textwrap

# ---------- ffmpeg helpers ----------
def mp3_to_wav(mp3_path, wav_path):
    subprocess.run(["ffmpeg","-y","-i",mp3_path,wav_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def wav_to_mp3(wav_path, mp3_path, bitrate="128k"):
    subprocess.run(["ffmpeg","-y","-i",wav_path,"-b:a",bitrate,mp3_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# ---------- bit helpers ----------
def bytes_to_bits(data: bytes) -> List[int]:
    bits = []
    for b in data:
        for i in range(8):
            bits.append((b >> (7 - i)) & 1)  # MSB-first per byte
    return bits

def bits_to_bytes(bits: List[int]) -> bytes:
    out = []
    for i in range(0, len(bits), 8):
        chunk = bits[i:i+8]
        if len(chunk) < 8:
            break
        val = 0
        for bit in chunk:
            val = (val << 1) | (bit & 1)
        out.append(val)
    return bytes(out)

# ---------- position selection (deterministic by seed) ----------
def pick_positions(num_samples: int, total_bits: int, bits_per_sample: int, seed: int=None):
    if seed is not None:
        random.seed(seed)
    total_slots = num_samples * bits_per_sample
    if total_bits > total_slots:
        raise ValueError(f"Not enough capacity: need {total_bits} bits but only {total_slots} slots")
    # flat slots are sample indices repeated bits_per_sample times
    slots = []
    for s in range(num_samples):
        for _ in range(bits_per_sample):
            slots.append(s)
    random.shuffle(slots)
    return slots[:total_bits]  # positions for each bit, in order

# ---------- embed / extract ----------
def embed_bits_pcm(wav_in, wav_out, bits: List[int], bits_per_sample:int=1, seed:int=0):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        data = data[:,0]
    samples = data.copy()
    n_samples = len(samples)
    positions = pick_positions(n_samples, len(bits), bits_per_sample, seed=seed)
    # counters to place multiple bits into same sample across occurrences (k=0..bits_per_sample-1)
    counters = {}
    for i, bit in enumerate(bits):
        samp = positions[i]
        k = counters.get(samp, 0)
        if k >= bits_per_sample:
            # should not happen
            continue
        mask = ~(1 << k) & 0xFFFF
        samples[samp] = (int(samples[samp]) & mask) | ((bit & 1) << k)
        counters[samp] = k + 1
    sf.write(wav_out, samples, sr, subtype="PCM_16")
    return positions, n_samples, sr

def extract_bits_pcm(wav_in, total_bits:int, bits_per_sample:int, positions:List[int]):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        data = data[:,0]
    samples = data
    counters = {}
    bits = []
    for i in range(total_bits):
        samp = positions[i]
        k = counters.get(samp, 0)
        if k >= bits_per_sample:
            bits.append(0)
        else:
            bits.append( (int(samples[samp]) >> k) & 1 )
        counters[samp] = k + 1
    return bits

# ---------- stats / printing ----------
def bit_confusion(orig_bits, rec_bits):
    assert len(orig_bits) == len(rec_bits)
    n00 = n01 = n10 = n11 = 0
    for o,r in zip(orig_bits, rec_bits):
        if o==0 and r==0: n00+=1
        elif o==0 and r==1: n01+=1
        elif o==1 and r==0: n10+=1
        elif o==1 and r==1: n11+=1
    return {"n00":n00,"n01":n01,"n10":n10,"n11":n11}

def pretty_print_results(message, orig_bits, rec_bits):
    conf = bit_confusion(orig_bits, rec_bits)
    total = sum(conf.values())
    survival = (conf["n00"] + conf["n11"]) / total * 100 if total>0 else 0.0
    p01 = conf["n01"] / (conf["n00"] + conf["n01"]) * 100 if (conf["n00"]+conf["n01"])>0 else float('nan')
    p10 = conf["n10"] / (conf["n10"] + conf["n11"]) * 100 if (conf["n10"]+conf["n11"])>0 else float('nan')
    print("\n=== BIT-LEVEL STATS ===")
    print(f"bits embedded: {total}")
    print(f"survival (bit equal): {survival:.2f}%")
    print(f"P(0->1): {p01:.2f}%   P(1->0): {p10:.2f}%")
    print("confusion:", conf)
    # bytewise
    rec_bytes = bits_to_bytes(rec_bits)
    orig_bytes = bits_to_bytes(orig_bits)
    # compare bytes
    same_bytes = sum(1 for a,b in zip(orig_bytes, rec_bytes) if a==b)
    print("\n=== BYTE-LEVEL STATS ===")
    print(f"bytes embedded: {len(orig_bytes)}  bytes fully recovered: {same_bytes} ({100.0*same_bytes/len(orig_bytes):.2f}%)")
    print("\nRecovered text (lossy; nonprintable shown as hex):")
    try:
        # try to decode as utf-8
        txt = rec_bytes.decode("utf-8")
        # show a short preview (safely)
        print(textwrap.fill(txt[:512], width=80))
        if len(txt) > 512:
            print("... (truncated)")
    except Exception:
        # show hex
        print(rec_bytes.hex()[:512] + ("..." if len(rec_bytes.hex())>512 else ""))

# ---------- CLI handlers ----------
def cmd_embed(args):
    mp3_to_wav(args.input_mp3, "orig.wav")
    msg_bytes = args.message.encode("utf-8")
    orig_bits = bytes_to_bits(msg_bytes)
    print(f"[+] Message bytes: {len(msg_bytes)} -> bits: {len(orig_bits)}")
    positions, n_samples, sr = embed_bits_pcm("orig.wav", "embedded.wav", orig_bits,
                                             bits_per_sample=args.bits_per_sample, seed=args.seed)
    wav_to_mp3("embedded.wav", args.output_mp3, bitrate=args.bitrate)
    # save meta for extraction
    meta = {
        "positions": positions,
        "total_bits": len(orig_bits),
        "bits_per_sample": args.bits_per_sample,
        "msg_bytes": len(msg_bytes)
    }
    with open(args.output_mp3 + ".pos.json","w") as f:
        json.dump(meta, f)
    print(f"[+] Written {args.output_mp3} and positions map {args.output_mp3}.pos.json")

def cmd_extract(args):
    posfile = args.stego_mp3 + ".pos.json"
    if not os.path.exists(posfile):
        print("position file missing:", posfile); return
    meta = json.load(open(posfile,"r"))
    positions = meta["positions"]
    total_bits = meta["total_bits"]
    bits_per_sample = meta["bits_per_sample"]
    mp3_to_wav(args.stego_mp3, "recovered.wav")
    rec_bits = extract_bits_pcm("recovered.wav", total_bits, bits_per_sample, positions)
    orig_bytes_len = meta["msg_bytes"]
    # we can reconstruct original bits for reporting by reading saved positions? We didn't store original bits here.
    # For stats we assume user embedded recently and has orig message; we'll accept a --orig-message parameter optionally.
    if args.orig_message:
        orig_bits = bytes_to_bits(args.orig_message.encode("utf-8"))
    else:
        # attempt to reconstruct original bits from positions by re-extracting from the embedded.wav if present
        orig_bits = None
    # if orig_bits known, compute confusion; else show recovered bytes and stats
    if orig_bits is not None:
        pretty_print_results(args.orig_message, orig_bits, rec_bits)
    else:
        rec_bytes = bits_to_bytes(rec_bits)[:orig_bytes_len]
        print("\nRecovered bytes (len={}):".format(len(rec_bytes)))
        try:
            print(rec_bytes.decode("utf-8", errors="replace"))
        except:
            print(rec_bytes.hex())
        # also show bit-level match percentage if we can load embedded.wav (convenience)
        if os.path.exists("embedded.wav"):
            emb_bits = extract_bits_pcm("embedded.wav", total_bits, bits_per_sample, positions)
            conf = bit_confusion = None
            # compare emb_bits vs rec_bits
            eq = sum(1 for a,b in zip(emb_bits, rec_bits) if a==b)
            print(f"\n(Comparing embedded.wav -> recovered.wav) Bit equality: {eq}/{total_bits} = {100.0*eq/total_bits:.2f}%")
        else:
            print("Note: for full bitwise stats, re-run embed/extract in same folder or pass --orig-message to extract.")

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    p_e = sub.add_parser("embed")
    p_e.add_argument("input_mp3")
    p_e.add_argument("output_mp3")
    p_e.add_argument("message")
    p_e.add_argument("--bits-per-sample", type=int, default=1, choices=[1,2,3])
    p_e.add_argument("--bitrate", default="128k")
    p_e.add_argument("--seed", type=int, default=42)
    p_x = sub.add_parser("extract")
    p_x.add_argument("stego_mp3")
    p_x.add_argument("--orig-message", default=None, help="(optional) provide original message for precise stats")
    p_x.add_argument("--bits-per-sample", type=int, default=1)
    args = ap.parse_args()

    if args.cmd == "embed":
        cmd_embed(args)
    elif args.cmd == "extract":
        cmd_extract(args)
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
