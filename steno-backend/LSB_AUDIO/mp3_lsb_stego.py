import argparse
import sys
import os
import math
import struct
import numpy as np

SCALE = 1_000_000  # per paper: multiply floats by 1e6

# Try to import librosa (preferred), soundfile, and pydub as fallbacks.
_have_librosa = False
_have_soundfile = False
_have_pydub = False
try:
    import librosa
    _have_librosa = True
except Exception:
    pass

try:
    import soundfile as sf
    _have_soundfile = True
except Exception:
    pass

try:
    from pydub import AudioSegment
    _have_pydub = True
except Exception:
    pass

def read_audio_float(path):
    ext = os.path.splitext(path)[1].lower()
    if _have_librosa:
        y, sr = librosa.load(path, sr=None, mono=False)  # y shape: (n,) or (channels, n)
        if y.ndim == 1:
            y = np.expand_dims(y, 0)
        return y, sr
    # fallback to pydub
    if _have_pydub:
        audio = AudioSegment.from_file(path)
        sr = audio.frame_rate
        samples = np.array(audio.get_array_of_samples())
        channels = audio.channels
        samples = samples.reshape((-1, channels)).T.astype(np.float32)
        # convert from PCM range to [-1,1] using sample_width
        max_val = float(1 << (8 * audio.sample_width - 1))
        samples = samples / max_val
        return samples, sr
    raise RuntimeError("Need librosa or pydub to decode audio. Install librosa (recommended) or pydub+ffmpeg.")


def write_wav_float(path, samples, sr):
    if _have_soundfile:
        # soundfile expects shape (n, channels)
        sf.write(path, samples.T, sr, subtype='PCM_16')
        return
    # fallback: use wave + struct, convert to int16
    import wave
    nch, n = samples.shape
    sampwidth = 2  # bytes (16-bit)
    with wave.open(path, 'wb') as w:
        w.setnchannels(nch)
        w.setsampwidth(sampwidth)
        w.setframerate(sr)
        # clip and convert
        int_data = np.clip(samples, -1.0, 1.0)
        int_data = (int_data * 32767.0).astype(np.int16)
        # interleave channels
        interleaved = int_data.T.flatten()
        w.writeframes(interleaved.tobytes())


def reencode_to_mp3(input_wav, output_mp3, bitrate='320k'):
    if not _have_pydub:
        raise RuntimeError('pydub not available; cannot re-encode to mp3. Install pydub and ffmpeg.')
    audio = AudioSegment.from_wav(input_wav)
    audio.export(output_mp3, format='mp3', bitrate=bitrate)


def _int_to_bitlist(x):
    # Return list of bits LSB-first for positive integers
    if x == 0:
        return [0]
    bits = []
    while x:
        bits.append(x & 1)
        x >>= 1
    return bits


def _bitlist_to_int(bits):
    # bits is LSB-first list
    val = 0
    for i, b in enumerate(bits):
        if b:
            val |= (1 << i)
    return val


def text_to_bits(s):
    b = []
    for ch in s.encode('utf-8'):
        for i in range(8):
            b.append((ch >> (7 - i)) & 1)
    return b


def bits_to_text(bits):
    # bits are MSB-first per byte; bits length must be multiple of 8
    byts = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        byts.append(byte)
    try:
        return byts.decode('utf-8')
    except Exception:
        return byts.decode('latin-1', errors='replace')


def embed_bits_into_integers(int_arr, bits, lsb_count=1, start_idx=0):
    total_capacity = int_arr.size * lsb_count
    if len(bits) > total_capacity - 32:
        raise ValueError(f"Not enough capacity: need {len(bits)} bits, capacity {total_capacity - 32} (reserve for header)")
    # We'll write a 32-bit length header first (big-endian) to indicate payload length
    header = len(bits)
    header_bits = [(header >> (31 - i)) & 1 for i in range(32)]  # MSB-first
    payload = header_bits + bits
    # embed payload sequentially
    flat = int_arr.ravel()
    bit_idx = 0
    for i in range(start_idx, flat.size):
        if bit_idx >= len(payload):
            break
        # take next lsb_count bits (MSB-first within chunk)
        chunk = 0
        for k in range(lsb_count):
            if bit_idx < len(payload):
                chunk = (chunk << 1) | payload[bit_idx]
                bit_idx += 1
            else:
                chunk = (chunk << 1)
        # mask out lowest lsb_count bits and set them to chunk
        mask = ~((1 << lsb_count) - 1)
        flat[i] = (flat[i] & mask) | chunk
    return flat.reshape(int_arr.shape), bit_idx


def extract_bits_from_integers(int_arr, lsb_count=1, start_idx=0):
    flat = int_arr.ravel()
    bits = []
    for i in range(start_idx, flat.size):
        val = flat[i] & ((1 << lsb_count) - 1)
        # val is an integer representing lsb_count bits (MSB-first per chunk?)
        # We need to expand into lsb_count bits MSB-first
        chunk_bits = [(val >> (lsb_count - 1 - j)) & 1 for j in range(lsb_count)]
        bits.extend(chunk_bits)
    # first 32 bits are header (MSB-first)
    if len(bits) < 32:
        return None
    header = 0
    for i in range(32):
        header = (header << 1) | bits[i]
    payload_len = header
    payload_bits = bits[32:32 + payload_len]
    if len(payload_bits) < payload_len:
        # incomplete
        return None
    return payload_bits


def embed_message(input_path, message, lsb=1, out_wav='stego.wav', out_mp3=None, bitrate='320k'):
    samples, sr = read_audio_float(input_path)  # shape: (channels, n)
    nch, n = samples.shape[0], samples.shape[1]
    print(f"Decoded: channels={nch}, samples_per_channel={n}, sr={sr}")
    # we'll operate per-sample preserving channel order: interleaved when flattening
    # Convert floats to scaled integers per paper
    signs = np.sign(samples)
    abs_samples = np.abs(samples)
    scaled = np.floor(abs_samples * SCALE + 0.5).astype(np.int64)  # integer-like
    # flatten in C-order (channel major -> we'll interleave manually)
    # For embedding convenience, create interleaved view: shape (n * nch,)
    interleaved = np.empty(n * nch, dtype=np.int64)
    for ch in range(nch):
        interleaved[ch::nch] = scaled[ch]
    # Now embed
    bits = text_to_bits(message)
    print(f"Message length: {len(message)} bytes => {len(bits)} bits; lsb={lsb}")
    modified, bits_embedded = embed_bits_into_integers(interleaved, bits, lsb_count=lsb, start_idx=0)
    print(f"Bits embedded (including header): {bits_embedded}")
    # reconstruct channels from interleaved
    reconstructed = np.empty_like(scaled)
    for ch in range(nch):
        reconstructed[ch] = modified[ch::nch]
    # restore sign and rescale back to float in [-1,1]
    recon_float = (reconstructed.astype(np.float64) / SCALE) * signs
    # clip
    recon_float = np.clip(recon_float, -1.0, 1.0)
    # write WAV
    write_wav_float(out_wav, recon_float, sr)
    print(f"WAV written to {out_wav}")
    if out_mp3:
        try:
            reencode_to_mp3(out_wav, out_mp3, bitrate=bitrate)
            print(f"MP3 re-encoded to {out_mp3} (bitrate {bitrate})")
        except Exception as e:
            print("Warning: failed to re-encode to mp3:", e)
            print("You can re-encode manually with ffmpeg: ffmpeg -i stego.wav -b:a 320k stego.mp3")


def extract_message(input_path, lsb=1):
    samples, sr = read_audio_float(input_path)
    nch, n = samples.shape[0], samples.shape[1]
    signs = np.sign(samples)
    abs_samples = np.abs(samples)
    scaled = np.floor(abs_samples * SCALE + 0.5).astype(np.int64)
    interleaved = np.empty(n * nch, dtype=np.int64)
    for ch in range(nch):
        interleaved[ch::nch] = scaled[ch]
    bits = extract_bits_from_integers(interleaved, lsb_count=lsb, start_idx=0)
    if bits is None:
        print("Failed to extract payload or incomplete payload.")
        return None
    text = bits_to_text(bits)
    return text


def main():
    p = argparse.ArgumentParser(description='MP3 LSB stego (paper method).')
    sub = p.add_subparsers(dest='cmd')
    e = sub.add_parser('embed', help='Embed message into an audio file (MP3 input recommended)')
    e.add_argument('input', help='Input MP3/WAV')
    e.add_argument('message', help='Message to embed (UTF-8)')
    e.add_argument('--lsb', type=int, default=1, choices=[1,2,3,4], help='Number of LSBs to use per sample integer')
    e.add_argument('--out-wav', default='stego.wav', help='Output WAV path (lossless)')
    e.add_argument('--out-mp3', default=None, help='Optional output MP3 path (requires ffmpeg)')
    e.add_argument('--bitrate', default='320k', help='Bitrate for re-encoding to mp3 (if used)')
    x = sub.add_parser('extract', help='Extract message from WAV/decoded MP3')
    x.add_argument('input', help='Input WAV/MP3 (if MP3, it will be decoded first)')
    x.add_argument('--lsb', type=int, default=1, choices=[1,2,3,4], help='LSBs used when embedding')
    args = p.parse_args()
    if args.cmd == 'embed':
        embed_message(args.input, args.message, lsb=args.lsb, out_wav=args.out_wav, out_mp3=args.out_mp3, bitrate=args.bitrate)
    elif args.cmd == 'extract':
        text = extract_message(args.input, lsb=args.lsb)
        if text is not None:
            print('Extracted message:\\n', text)
    else:
        p.print_help()


if __name__ == '__main__':
    main()
