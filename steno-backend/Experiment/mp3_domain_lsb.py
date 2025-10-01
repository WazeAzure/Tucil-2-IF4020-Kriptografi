#!/usr/bin/env python3
"""
mp3_domain_lsb.py
Embed/extract simple text into MP3 main_data bytes (LSB) and
recalculate CRC if present.

NOTES:
- Uses paper's signatures and random-start Espace/Irand idea. (See uploaded paper.)
- Changing main_data WILL change audio quality; prefer bits_per_byte=1 for imperceptibility.
"""

import sys
import struct
import random
from typing import List, Tuple

# --- Signatures from the paper (14-bit pattern strings) ---
SIGNATURES = {
    1: ("10101010101010", "10101010101010"),  # single bit insertion
    2: ("01010101010101", "01010101010101"),  # two-bit insertion
    3: ("10101010101010", "01010101010101"),  # three-bit insertion
    4: ("01010101010101", "10101010101010"),  # four-bit insertion
}

# CRC16-IBM (poly=0x8005) implementation for MP3 CRC
def crc16_ibm(data: bytes, poly: int = 0x8005, init: int = 0xFFFF) -> int:
    crc = init
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF

# --- MP3 header parsing (simplified; supports MPEG1 Layer III common cases) ---
BITRATE_TABLE = {
    # index: bitrate in bps (MPEG1, Layer III)
    0b0001: 32000, 0b0010: 40000, 0b0011: 48000, 0b0100: 56000,
    0b0101: 64000, 0b0110: 80000, 0b0111: 96000, 0b1000: 112000,
    0b1001: 128000, 0b1010: 160000, 0b1011: 192000, 0b1100: 224000,
    0b1101: 256000, 0b1110: 320000
}
SAMPLERATE_TABLE = {0b00: 44100, 0b01: 48000, 0b10: 32000}

def parse_frame_header(header_bytes: bytes):
    if len(header_bytes) < 4: return None
    b1,b2,b3,b4 = struct.unpack(">BBBB", header_bytes)
    sync = ((b1 << 4) | (b2 >> 4)) & 0xFFF
    if sync != 0xFFF:
        return None
    version_id = (b2 >> 3) & 0b11
    layer = (b2 >> 1) & 0b11
    protection_bit = b2 & 0b1
    bitrate_index = (b3 >> 4) & 0xF
    samplerate_index = (b3 >> 2) & 0b11
    padding_bit = (b3 >> 1) & 0x1
    channel_mode = (b4 >> 6) & 0b11

    bitrate = BITRATE_TABLE.get(bitrate_index, None)
    samplerate = SAMPLERATE_TABLE.get(samplerate_index, None)
    if bitrate is None or samplerate is None:
        return None

    # frame length formula for MPEG1 Layer III: floor(144000 * bitrate / samplerate) + padding
    frame_length = int((144000 * bitrate) // samplerate + padding_bit)
    return {
        "protection_bit": protection_bit,
        "bitrate": bitrate,
        "samplerate": samplerate,
        "padding": padding_bit,
        "channel_mode": channel_mode,
        "frame_length": frame_length
    }

# read all frames and their positions
def read_frames(mp3_path: str) -> List[Tuple[int, bytes, dict]]:
    data = open(mp3_path, "rb").read()
    frames = []
    i = 0
    while i < len(data) - 4:
        header = data[i:i+4]
        parsed = parse_frame_header(header)
        if parsed:
            fl = parsed["frame_length"]
            if i + fl > len(data):
                break
            frame_bytes = data[i:i+fl]
            frames.append((i, frame_bytes, parsed))
            i += fl
        else:
            i += 1
    return frames

# convert text to bit list with signatures (paper approach)
def text_to_bitlist(text: str, bits_per_byte: int) -> List[int]:
    start_sig, end_sig = SIGNATURES[bits_per_byte]
    bits = []
    # start signature (as bits)
    bits.extend(int(b) for b in start_sig)
    # message ascii -> bits
    for ch in text.encode("utf-8"):
        bstr = f"{ch:08b}"
        bits.extend(int(b) for b in bstr)
    # end signature
    bits.extend(int(b) for b in end_sig)
    return bits

# embed bitlist across main_data bytes starting at a chosen global offset
def embed_bits_into_frames(frames: List[Tuple[int, bytes, dict]], bitlist: List[int],
                           bits_per_byte: int, start_offset: int = 0, rng_seed: int = None):
    if rng_seed is not None:
        random.seed(rng_seed)

    # gather main_data byte arrays (frames already include header+maybe CRC)
    main_data_blocks = []
    for pos, frame_bytes, hdr in frames:
        header_len = 4
        if hdr["protection_bit"] == 0:
            header_len += 2  # CRC present
        main_data = bytearray(frame_bytes[header_len:])  # main_data + ancillary
        main_data_blocks.append((pos, header_len, main_data, hdr))

    # compute total available bytes R (paper used samples; here we use bytes)
    total_bytes = sum(len(b[2]) for b in main_data_blocks)
    needed = len(bitlist)
    deg = bits_per_byte
    # Espace rule adapted: Espace = R - rb*cb/deg - 200  (paper used samples & text size)
    # We'll adapt: Espace = total_bytes - ceil(bits_needed/deg) - 200
    slots_needed = (needed + deg - 1) // deg
    Espace = max(0, total_bytes - slots_needed - 200)
    # compute Irand per paper: ceil(rand * fix(Espace/2)) + 200
    irand = 200
    if Espace > 0:
        irand = 200 + random.randint(0, max(0, Espace//2))
    start = start_offset + irand
    # ensure start < total_bytes
    start = min(start, max(0, total_bytes - slots_needed))

    # now embed sequentially across bytes starting at 'start' index in flattened main_data space
    flat_index = 0
    bit_index = 0
    # advance flat_index to start
    flat_index = start

    for idx, (pos, header_len, main_data, hdr) in enumerate(main_data_blocks):
        n = len(main_data)
        for j in range(n):
            if flat_index > 0:
                flat_index -= 1
                continue
            # we are now at a byte we can use
            if bit_index >= needed:
                break
            # embed up to bits_per_byte bits into main_data[j] LSBs
            new_byte = main_data[j]
            value = 0
            for k in range(bits_per_byte):
                if bit_index < needed:
                    bit = bitlist[bit_index]
                    value |= (bit << k)
                    bit_index += 1
                else:
                    # no more bits, keep remaining LSBs as-is (or zero)
                    # we'll preserve existing upper bits and any leftover lower bits zeroed
                    pass
            # mask out lowest bits_per_byte bits, then OR with value
            mask = (~((1 << bits_per_byte) - 1)) & 0xFF
            new_byte = (new_byte & mask) | (value & ((1 << bits_per_byte) - 1))
            main_data[j] = new_byte
        # write back modified main_data into the frame bytes
        frames[idx] = (pos, bytearray(frames[idx][1][:header_len]) + main_data, hdr)

    if bit_index < needed:
        raise ValueError(f"Not enough capacity: embedded {bit_index}/{needed} bits")

    # recalc CRC per frame when needed and rebuild frame bytes
    out_frames_bytes = []
    for pos, frame_bytes, hdr in frames:
        header_len = 4
        crc_present = (hdr["protection_bit"] == 0)
        if crc_present:
            header_len += 2
        # frame_bytes currently header+main
        header = bytes(frame_bytes[:4])
        body = bytes(frame_bytes[4:])  # includes CRC slot if present; we'll recalc
        if crc_present:
            # compute crc over body (according to earlier understanding: CRC covers bits after header)
            crc_val = crc16_ibm(body)
            crc_bytes = struct.pack(">H", crc_val)
            # body currently starts with CRC field (we must overwrite first two bytes of body)
            body = crc_bytes + body[2:]
        out_frames_bytes.append(header + body)
    return out_frames_bytes

# Rebuild whole MP3: take original data and replace frame ranges with modified frames
def write_modified_mp3(original_path: str, out_path: str, frames_positions: List[Tuple[int, int]], modified_frames: List[bytes]):
    with open(original_path, "rb") as f:
        data = bytearray(f.read())
    # replace frames in order; frames_positions list contains (startpos, framelen)
    for (start, length), new_frame in zip(frames_positions, modified_frames):
        if len(new_frame) != length:
            # if new frame length differs, we must shift; for simplicity we'll error out
            raise ValueError("Modified frame length mismatch (this simple tool requires same length frames).")
        data[start:start+length] = new_frame
    with open(out_path, "wb") as f:
        f.write(data)

# extractor: read main_data LSBs and search signatures; returns first found ascii message
def extract_text_from_frames(frames: List[Tuple[int, bytes, dict]], bits_per_byte: int) -> str:
    # flatten LSB bits from main_data bytes
    bits = []
    for pos, frame_bytes, hdr in frames:
        header_len = 4 + (0 if hdr["protection_bit"] else 2)
        main_data = frame_bytes[header_len:]
        for b in main_data:
            for k in range(bits_per_byte):
                bits.append((b >> k) & 1)
    # convert bits to string searching for signature window
    start_sig, end_sig = SIGNATURES[bits_per_byte]
    start_sig_list = [int(x) for x in start_sig]
    end_sig_list = [int(x) for x in end_sig]
    # find start
    def find_subsequence(big, sub):
        L = len(sub)
        for i in range(len(big) - L + 1):
            if big[i:i+L] == sub:
                return i
        return -1
    si = find_subsequence(bits, start_sig_list)
    if si == -1:
        return ""
    ei = find_subsequence(bits[si+len(start_sig_list):], end_sig_list)
    if ei == -1:
        return ""
    payload_bits = bits[si+len(start_sig_list): si+len(start_sig_list)+ei]
    # group into 8 bits and decode
    chars = []
    for i in range(0, len(payload_bits), 8):
        byte_bits = payload_bits[i:i+8]
        if len(byte_bits) < 8: break
        val = 0
        for k,bit in enumerate(byte_bits):
            val = (val << 1) | bit
        chars.append(val)
    try:
        return bytes(chars).decode("utf-8", errors="replace")
    except:
        return bytes(chars).decode("latin1", errors="replace")

# --- High-level API: embed_text_in_mp3 and extract_text_from_mp3 ---
def embed_text_in_mp3(input_mp3: str, output_mp3: str, text: str, bits_per_byte: int = 1, rng_seed: int = None):
    if bits_per_byte not in (1,2,3,4):
        raise ValueError("bits_per_byte must be 1..4")
    frames = read_frames(input_mp3)
    if not frames:
        raise RuntimeError("No frames parsed - file may be unsupported format for this simple parser.")
    # remember original frame positions/lengths
    frames_positions = [(pos, len(frame_bytes)) for (pos, frame_bytes, hdr) in frames]
    # build bitlist from text + signatures
    bitlist = text_to_bitlist(text, bits_per_byte)
    # embed (this returns modified bytes for each frame)
    modified_bytes = embed_bits_into_frames(frames, bitlist, bits_per_byte, start_offset=0, rng_seed=rng_seed)
    # write back (this simple implementation requires frame sizes preserved)
    write_modified_mp3(input_mp3, output_mp3, frames_positions, modified_bytes)
    print("Embedding complete.")

def extract_text_from_mp3_file(input_mp3: str, bits_per_byte: int = 1) -> str:
    frames = read_frames(input_mp3)
    return extract_text_from_frames(frames, bits_per_byte)


# --- CLI ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  embed: python mp3_domain_lsb.py embed input.mp3 output.mp3 'your message' [bits_per_byte]")
        print("  extract: python mp3_domain_lsb.py extract input.mp3 [bits_per_byte]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "embed":
        _,_,inp,out,msg,*rest = sys.argv
        bits = int(rest[0]) if rest else 1
        embed_text_in_mp3(inp, out, msg, bits_per_byte=bits, rng_seed=12345)
    elif cmd == "extract":
        _,_,inp,*rest = sys.argv
        bits = int(rest[0]) if rest else 1
        print("Extracted:", extract_text_from_mp3_file(inp, bits_per_byte=bits))
    else:
        print("Unknown command")
