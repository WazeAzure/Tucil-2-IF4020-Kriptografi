#!/usr/bin/env python3
"""
pcm_survival_diagnostics.py

Stronger diagnostics for PCM bit-plane survival through MP3 round-trip.

Usage:
  python3 pcm_survival_diagnostics.py input.mp3 --bitrate 128k --length 5000

Requires:
  - ffmpeg on PATH
  - pip install numpy soundfile
"""
import argparse, subprocess, os, math
import numpy as np
import soundfile as sf
from collections import defaultdict

# ffmpeg helpers
def mp3_to_wav(mp3_path, wav_path):
    subprocess.run(["ffmpeg","-y","-i",mp3_path,wav_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def wav_to_mp3(wav_path, mp3_path, bitrate="128k"):
    subprocess.run(["ffmpeg","-y","-i",wav_path,"-b:a",bitrate,mp3_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# embed/extract single plane
def embed_bits_plane_pattern(wav_in, wav_out, bitplane, pattern_bits):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        data = data[:,0]
    samples = data.copy()
    n = min(len(pattern_bits), len(samples))
    mask = ~(1 << bitplane) & 0xFFFF
    for i in range(n):
        samples[i] = (samples[i] & mask) | ((pattern_bits[i] & 1) << bitplane)
    sf.write(wav_out, samples, sr, subtype="PCM_16")
    return n, sr

def extract_bits_plane(wav_in, bitplane, nbits):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        data = data[:,0]
    n = min(nbits, len(data))
    return [ (int(data[i]) >> bitplane) & 1 for i in range(n) ]

# helpers to build patterns
def make_pattern(pattern_name, length, rng=None):
    if pattern_name == "zeros":
        return [0]*length
    if pattern_name == "ones":
        return [1]*length
    if pattern_name == "alt":
        return [ (i%2) for i in range(length) ]
    if pattern_name == "rand":
        rng = np.random.RandomState(rng)
        return list(rng.randint(0,2,size=length))
    raise ValueError("unknown pattern")

def confusion_counts(orig_bits, rec_bits):
    n00 = n01 = n10 = n11 = 0
    for o,r in zip(orig_bits, rec_bits):
        if o == 0 and r == 0: n00 += 1
        elif o == 0 and r == 1: n01 += 1
        elif o == 1 and r == 0: n10 += 1
        elif o == 1 and r == 1: n11 += 1
    return n00,n01,n10,n11

def baseline_sample_change_rate(orig_wav, bitrate):
    # round-trip without embedding
    wav_to_mp3(orig_wav, "baseline.mp3", bitrate=bitrate)
    mp3_to_wav("baseline.mp3", "baseline_decoded.wav")
    orig, _ = sf.read(orig_wav, dtype="int16")
    dec, _ = sf.read("baseline_decoded.wav", dtype="int16")
    if orig.ndim>1: orig = orig[:,0]
    if dec.ndim>1: dec = dec[:,0]
    n = min(len(orig), len(dec))
    changed = sum(1 for i in range(n) if int(orig[i]) != int(dec[i]))
    return changed, n

def amplitude_buckets(values, nbins=5):
    mags = np.abs(values)
    bins = np.linspace(0, mags.max()+1e-9, nbins+1)
    idx = np.digitize(mags, bins) - 1
    return idx, bins

def run_tests(input_mp3, bitrate="128k", length=5000, planes=(0,1,2,3), rngseed=0):
    # decode original
    mp3_to_wav(input_mp3, "orig.wav")
    # baseline sample change
    changed, total = baseline_sample_change_rate("orig.wav", bitrate)
    print(f"\nBaseline sample changes (no embed) after roundtrip @ {bitrate}: {changed}/{total} ({100*changed/total:.2f}%)")

    patterns = ["zeros","ones","alt","rand"]
    results = {}

    for plane in planes:
        print(f"\n=== Testing plane {plane} ===")
        results[plane] = {}
        for pat in patterns:
            print(f"  pattern: {pat} ...", end="", flush=True)
            bits = make_pattern(pat, length, rng=rngseed)
            embed_bits_plane_pattern("orig.wav", "embed.wav", plane, bits)
            wav_to_mp3("embed.wav", "embed_mp3.mp3", bitrate=bitrate)
            mp3_to_wav("embed_mp3.mp3", "embed_dec.wav")
            rec = extract_bits_plane("embed_dec.wav", plane, length)
            n00,n01,n10,n11 = confusion_counts(bits, rec)
            total = n00+n01+n10+n11
            p01 = n01 / (n00+n01) if (n00+n01)>0 else float('nan')
            p10 = n10 / (n10+n11) if (n10+n11)>0 else float('nan')
            survival = (n00 + n11) / total * 100 if total>0 else float('nan')
            print(f" done. surv={survival:.2f}%, 0->1={p01*100:.2f}%, 1->0={p10*100:.2f}%")
            results[plane][pat] = {
                "n00": n00,"n01": n01,"n10": n10,"n11": n11,
                "p01": p01, "p10": p10, "survival": survival,
                "total": total
            }

        # amplitude bucket analysis: embed alt pattern and then inspect flips by amplitude
        bits = make_pattern("alt", length, rng=rngseed)
        embed_bits_plane_pattern("orig.wav", "embed.wav", plane, bits)
        wav_to_mp3("embed.wav", "embed_mp3.mp3", bitrate=bitrate)
        mp3_to_wav("embed_mp3.mp3", "embed_dec.wav")
        orig_samps, _ = sf.read("orig.wav", dtype="int16")
        dec_samps, _ = sf.read("embed_dec.wav", dtype="int16")
        if orig_samps.ndim>1: orig_samps = orig_samps[:,0]
        if dec_samps.ndim>1: dec_samps = dec_samps[:,0]
        n = min(len(orig_samps), len(dec_samps), length)
        orig_vals = orig_samps[:n]
        # find which bits flipped at plane
        flips = []
        for i in range(n):
            ob = (int(orig_vals[i]) >> plane) & 1
            rb = (int(dec_samps[i]) >> plane) & 1
            flips.append(0 if ob==rb else 1)
        idx, bins = amplitude_buckets(orig_vals, nbins=6)
        by_bucket = {}
        for b in range(len(bins)-1):
            members = [flips[i] for i in range(n) if idx[i]==b]
            if not members:
                rate = float('nan')
            else:
                rate = 100.0 * sum(members) / len(members)
            by_bucket[f"{bins[b]:.0f}-{bins[b+1]:.0f}"] = {"count": len(members), "flip_rate": rate}
        results[plane]['amplitude_buckets'] = by_bucket
        print("  amplitude bucket flip rates:", by_bucket)

    # pretty print summary
    print("\n\nSUMMARY TABLE:")
    print("Plane | Pattern | Total | Survival% | P(0->1)% | P(1->0)%")
    print("-"*60)
    for plane in sorted(results.keys()):
        for pat in patterns:
            r = results[plane][pat]
            print(f"{plane:5} | {pat:7} | {r['total']:5} | {r['survival']:8.2f} | {r['p01']*100:8.2f} | {r['p10']*100:8.2f}")
    return results

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input_mp3")
    ap.add_argument("--bitrate", default="128k")
    ap.add_argument("--length", type=int, default=5000)
    ap.add_argument("--planes", nargs="+", type=int, default=[0,1,2,3])
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    run_tests(args.input_mp3, bitrate=args.bitrate, length=args.length, planes=args.planes, rngseed=args.seed)

