import numpy as np
import soundfile as sf
import subprocess
import itertools
import os

# ------------------------------------
# Utilities
# ------------------------------------
def mp3_to_wav(mp3_path, wav_path):
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, wav_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

def wav_to_mp3(wav_path, mp3_path, bitrate="128k"):
    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-b:a", bitrate, mp3_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

# ------------------------------------
# LSB Embed/Extract with selectable bit-plane
# ------------------------------------
def embed_lsb(wav_in, wav_out, message_bits, bitplane=0):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        data = data[:, 0]  # mono only

    mask = ~(1 << bitplane)
    samples = data.copy()
    for i, bit in enumerate(message_bits):
        if i >= len(samples):
            break
        samples[i] = (samples[i] & mask) | (bit << bitplane)

    sf.write(wav_out, samples, sr, subtype="PCM_16")

def extract_lsb(wav_in, nbits, bitplane=0):
    data, sr = sf.read(wav_in, dtype="int16")
    if data.ndim > 1:
        data = data[:, 0]
    return ((data[:nbits] >> bitplane) & 1).tolist()

# ------------------------------------
# Experiment
# ------------------------------------
def run_experiment(input_mp3, secret_message, bitrate="128k", bitplane=0):
    # Step 1. Convert MP3 -> WAV
    mp3_to_wav(input_mp3, "original.wav")

    # Step 2. Message → bits
    bits = []
    for b in secret_message.encode("utf-8"):
        for i in range(8):
            bits.append((b >> (7 - i)) & 1)

    # Step 3. Embed
    embed_lsb("original.wav", "embedded.wav", bits, bitplane)

    # Step 4. Recompress cycle
    wav_to_mp3("embedded.wav", "compressed.mp3", bitrate)
    mp3_to_wav("compressed.mp3", "recovered.wav")

    # Step 5. Extract
    extracted = extract_lsb("recovered.wav", len(bits), bitplane)

    # Step 6. Compare
    survived = sum(1 for a, b in zip(bits, extracted) if a == b)
    return len(bits), survived


def test_harness(input_mp3):
    bitrates = ["64k", "128k", "192k", "320k"]
    bitplanes = [0, 1, 2]  # LSB, 2nd LSB, 3rd LSB
    payloads = [
        "HELLO WORLD",
        "A" * 100,      # ~800 bits
        "A" * 1000,     # ~8000 bits
    ]

    results = []

    for msg, br, bp in itertools.product(payloads, bitrates, bitplanes):
        total, survived = run_experiment(input_mp3, msg, br, bp)
        survival = survived / total * 100
        results.append((len(msg), br, bp, total, survived, survival))

    # Pretty print results
    print("\n=== SURVIVAL SUMMARY ===")
    print(f"{'Len':>6} | {'Bitrate':>6} | {'Plane':>5} | {'Bits':>6} | {'Survived':>9} | {'Rate':>7}")
    print("-" * 60)
    for r in results:
        print(f"{r[0]:6} | {r[1]:>6} | {r[2]:5} | {r[3]:6} | {r[4]:9} | {r[5]:6.2f}%")

    return results


if __name__ == "__main__":
    test_harness("input.mp3")
