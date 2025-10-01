import numpy as np
import soundfile as sf
import subprocess

def mp3_to_wav(mp3_path, wav_path):
    subprocess.run(["ffmpeg", "-y", "-nostats", "-hide_banner", "-i", mp3_path, wav_path], check=True)

def wav_to_mp3(wav_path, mp3_path, bitrate="128k"):
    subprocess.run(["ffmpeg", "-y", "-nostats", "-hide_banner", "-i", wav_path, "-b:a", bitrate, mp3_path], check=True)

def float_lsb_embed(wav_in, wav_out, message_bits):
    data, samplerate = sf.read(wav_in, dtype="float32")
    if data.ndim > 1:
        data = data[:, 0]  # mono for simplicity
    
    # Scale to int16 to get a clear "LSB plane"
    int_samples = np.int16(data * 1000000)

    for i, bit in enumerate(message_bits):
        if i >= len(int_samples):
            break
        int_samples[i] = (int_samples[i] & ~1) | bit

    # Convert back to float
    float_samples = int_samples.astype(np.float32) / 1000000.0
    sf.write(wav_out, float_samples, samplerate, subtype="PCM_16")

def float_lsb_extract(wav_in, n_bits):
    data, _ = sf.read(wav_in, dtype="float32")
    if data.ndim > 1:
        data = data[:, 0]

    int_samples = np.int16(data * 32767)
    bits = [(s & 1) for s in int_samples[:n_bits]]
    return bits

# Example usage
mp3_to_wav("input.mp3", "decoded.wav")

msg = "HELLO"
bits = [int(b) for c in msg.encode() for b in f"{c:08b}"]

float_lsb_embed("decoded.wav", "stego.wav", bits)
wav_to_mp3("stego.wav", "stego.mp3", bitrate="320k")

mp3_to_wav("stego.mp3", "redecoded.wav")
recovered_bits = float_lsb_extract("redecoded.wav", len(bits))

# Convert bits back to text
chars = [int("".join(map(str, recovered_bits[i:i+8])), 2) for i in range(0, len(bits), 8)]
print("DDDDDDDDDDDONNNNNNNNNNNNNNEEEEEEEEEEE")
print(bytes(chars).decode())
