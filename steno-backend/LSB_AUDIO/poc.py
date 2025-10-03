from pydub import AudioSegment
import numpy as np

# --- Helper functions ---
def text_to_bits(text):
    return ''.join(f"{ord(c):08b}" for c in text)

def bits_to_text(bits):
    chars = [chr(int(bits[i:i+8], 2)) for i in range(0, len(bits), 8)]
    return ''.join(chars)

# --- Embed message ---
def embed_message(audio, message, segment_length_ms=1000):
    bits = text_to_bits(message)
    bit_idx = 0
    processed_segments = []

    segments = [
        audio[i:i + segment_length_ms]
        for i in range(0, len(audio), segment_length_ms)
    ]

    for seg in segments:
        samples = np.array(seg.get_array_of_samples())
        samples = samples.reshape((-1, seg.channels))
        processed = samples.copy()

        # Modify samples LSB
        for row in range(processed.shape[0]):
            for ch in range(processed.shape[1]):
                if bit_idx < len(bits):
                    sample = processed[row, ch]
                    sample = (sample & ~1) | int(bits[bit_idx])  # set LSB
                    processed[row, ch] = sample
                    bit_idx += 1

        # Flatten and rebuild
        raw_bytes = processed.astype(np.int16).flatten().tobytes()
        rebuilt_seg = AudioSegment(
            data=raw_bytes,
            sample_width=seg.sample_width,
            frame_rate=seg.frame_rate,
            channels=seg.channels
        )
        processed_segments.append(rebuilt_seg)

    final_audio = sum(processed_segments)
    return final_audio, len(bits)  # also return how many bits we embedded

# --- Extract message ---
def extract_message(audio, bit_length, segment_length_ms=1000):
    bits = ""
    segments = [
        audio[i:i + segment_length_ms]
        for i in range(0, len(audio), segment_length_ms)
    ]

    for seg in segments:
        samples = np.array(seg.get_array_of_samples())
        samples = samples.reshape((-1, seg.channels))

        for row in range(samples.shape[0]):
            for ch in range(samples.shape[1]):
                if len(bits) < bit_length:
                    bits += str(samples[row, ch] & 1)

    return bits_to_text(bits)


# ====================
# DEMO USAGE
# ====================
if __name__ == "__main__":
    audio = AudioSegment.from_mp3("stego.mp3")

    # Secret message
    secret = "A"*1000

    # Embed
    stego_audio, bit_length = embed_message(audio, secret)
    stego_audio.export("rebuilt.mp3", format="mp3")

    # Extract
    extracted = extract_message(stego_audio, bit_length)
    print("Extracted message:", extracted)