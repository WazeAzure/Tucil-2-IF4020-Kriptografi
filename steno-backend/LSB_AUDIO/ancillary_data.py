
"""
mp3_ancillary_lsb_stego.py

Embed/extract data using LSBs placed in MP3 frames' ancillary bytes (per-frame padding).
This script:
 - Parses MP3 frames (MPEG-1 Layer III focused, best-effort).
 - Parses side_info to read part2_3_length per granule -> compute estimated main_data bit usage.
 - Computes ancillary region per frame as bytes AFTER the estimated main_data usage up to the frame end.
 - Embeds payload bits into the LSBs of those ancillary bytes (1 bit per byte).
 - Extracts by reading those same LSBs.

Important notes / limitations:
 - This is a pragmatic, best-effort tool. MP3 bit-reservoir and encoder-specific layout can make
   exact mapping between “part2_3_length” and actual bytes tricky. This tool computes ancillaries
   by assuming the granule part2_3 bits are packed (per-frame) and that used bytes = ceil(sum_bits/8).
 - Many encoders may not leave ancillary bytes (ancillary_len == 0). The tool will skip frames with no ancillary.
 - If you plan to modify bytes and then re-encode the MP3 with another encoder, ancillary data may be lost.
 - Always work on copies, validate output with decoders (ffmpeg/mpg123), and test extraction on the edited file.

Usage:
  Inspect and show ancillary availability:
    python mp3_ancillary_lsb_stego.py inspect input.mp3

  Embed payload:
    python mp3_ancillary_lsb_stego.py embed input.mp3 out.mp3 payload.bin
    (or pass --text "secret message" to embed text instead of a file)

  Extract payload:
    python mp3_ancillary_lsb_stego.py extract input.mp3 out_payload.bin

Options:
  --step N        Use only every N-th frame for embedding (sparse embedding). Default 1 (every frame).
  --start-frame F Start embedding at frame index F (default 0).
  --bits-per-byte k Use k LSBs per ancillary byte (1 or 2). Default 1.
  --max-bytes M   Maximum total ancillary bytes to use (safety limit).

The script is self-contained and uses only Python stdlib.

Author: practical LSB-in-ancillary prototype
"""
from typing import List, Tuple, Dict, Optional
import sys
import os
import struct
import argparse
import math
import random

# ---------- MP3 parsing helpers (MPEG-1 Layer III focus) ----------
def is_frame_sync(header: bytes) -> bool:
    return len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0

def parse_header(header: bytes):
    if len(header) < 4:
        return None
    b0,b1,b2,b3 = header[0], header[1], header[2], header[3]
    ver_bits = (b1 >> 3) & 0x03
    if ver_bits == 3:
        mpeg_version = 1
    elif ver_bits == 2:
        mpeg_version = 2
    else:
        mpeg_version = 2

    layer_bits = (b1 >> 1) & 0x03
    if layer_bits == 1:
        layer = 3
    elif layer_bits == 2:
        layer = 2
    elif layer_bits == 3:
        layer = 1
    else:
        return None

    bitrate_idx = (b2 >> 4) & 0x0F
    samplerate_idx = (b2 >> 2) & 0x03
    padding = (b2 >> 1) & 0x01
    channel_mode = (b3 >> 6) & 0x03

    bitrate_table_v1_l3 = [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320,0]
    bitrate_table_v2_l3 = [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160,0]
    samplerate_table_v1 = [44100,48000,32000,0]
    samplerate_table_v2 = [22050,24000,16000,0]

    if mpeg_version == 1 and layer == 3:
        bitrate = bitrate_table_v1_l3[bitrate_idx]*1000
    else:
        bitrate = bitrate_table_v2_l3[bitrate_idx]*1000

    if mpeg_version == 1:
        samplerate = samplerate_table_v1[samplerate_idx]
    else:
        samplerate = samplerate_table_v2[samplerate_idx]

    if bitrate == 0 or samplerate == 0:
        return None

    if layer == 3:
        if mpeg_version == 1:
            frame_size = int(144 * bitrate / samplerate) + padding
        else:
            frame_size = int(72 * bitrate / samplerate) + padding
    else:
        frame_size = int(144 * bitrate / samplerate) + padding

    side_info_size = 17 if channel_mode == 3 else 32
    return {
        'frame_size': frame_size,
        'side_info_size': side_info_size,
        'mpeg_version': mpeg_version,
        'layer': layer,
        'channel_mode': channel_mode,
        'bitrate': bitrate,
        'samplerate': samplerate
    }

def skip_id3v2(mp3_bytes: bytes) -> int:
    if len(mp3_bytes) < 10:
        return 0
    if mp3_bytes[0:3] == b'ID3':
        size = ((mp3_bytes[6] & 0x7F) << 21) | ((mp3_bytes[7] & 0x7F) << 14) | ((mp3_bytes[8] & 0x7F) << 7) | (mp3_bytes[9] & 0x7F)
        return 10 + size
    return 0

# ---------- side_info minimal parser (extract part2_3_length per granule/channel) ----------
def bytes_to_bitlist(barr: bytes) -> List[int]:
    out = []
    for byte in barr:
        for bitpos in range(8):
            out.append((byte >> (7-bitpos)) & 1)
    return out

def parse_side_info_fields(side_info_bytes: bytes):
    """
    Minimal attempt to parse side_info to extract per-granule per-channel part2_3_length.
    Returns dict with:
      - main_data_begin
      - per-granule list of channels with 'part2_3_length'
    If parsing fails, returns None.
    """
    try:
        bits = bytes_to_bitlist(side_info_bytes)
        ptr = 0
        def read(n):
            nonlocal ptr
            if ptr + n > len(bits):
                raise ValueError("not enough side_info bits")
            val = 0
            for _ in range(n):
                val = (val << 1) | bits[ptr]
                ptr += 1
            return val
        main_data_begin = read(9)
        _private_bits = read(3)
        # determine channels by side_info length (MPEG-1: 17 -> mono, 32 -> stereo)
        ch = 1 if len(side_info_bytes) == 17 else 2
        granules = []
        for gr in range(2):
            channels = []
            for c in range(ch):
                part2_3_length = read(12)
                big_values = read(9)
                _global_gain = read(8)
                _scalefac_compress = read(4)
                window_switching_flag = read(1)
                if window_switching_flag:
                    _block_type = read(2)
                    _mixed_block_flag = read(1)
                    _table_select0 = read(5)
                    _table_select1 = read(5)
                    _table_select2 = read(5)
                    _sub0 = read(3); _sub1 = read(3); _sub2 = read(3)
                    _region0 = read(4); _region1 = read(3)
                else:
                    _table_select0 = read(5); _table_select1 = read(5); _table_select2 = read(5)
                    _region0 = read(4); _region1 = read(3)
                    _preflag = read(1); _scalefac_scale = read(1); _count1table_select = read(1)
                channels.append({'part2_3_length': part2_3_length, 'big_values': big_values})
            granules.append(channels)
        # scfsi per channel (4 bits each)
        scfsi = []
        for c in range(ch):
            scfsi.append(read(4))
        return {'main_data_begin': main_data_begin, 'granules': granules, 'channels': ch}
    except Exception:
        return None

# ---------- core scanning and mapping ----------
def scan_frames_for_ancillary(mp3_bytes: bytes) -> List[Dict]:
    """
    Iterate frames and compute ancillary byte region (start, length) per frame.
    Returns list of dicts:
      {
        frame_index, header_idx, frame_size, side_info_idx, side_info_size,
        main_data_idx, estimated_main_data_bytes, ancillary_idx, ancillary_len, parsed_side_info
      }
    """
    results = []
    i = skip_id3v2(mp3_bytes)
    n = len(mp3_bytes)
    frame_idx = 0
    while i < n:
        if i + 4 > n:
            break
        header = bytes(mp3_bytes[i:i+4])
        if not is_frame_sync(header):
            i += 1
            continue
        info = parse_header(header)
        if info is None:
            i += 1
            continue
        frame_size = info['frame_size']
        side_info_size = info['side_info_size']
        if i + frame_size > n:
            # truncated frame finish
            break
        header_idx = i
        side_info_idx = i + 4
        main_data_idx = i + 4 + side_info_size
        side_info_bytes = bytes(mp3_bytes[side_info_idx:side_info_idx+side_info_size])
        parsed = parse_side_info_fields(side_info_bytes)
        # compute estimated used main_data bits for this frame as sum of part2_3_length across granules/channels
        estimated_bits = 0
        if parsed:
            for gr in parsed['granules']:
                for chinfo in gr:
                    # part2_3_length is bits for that channel/granule
                    estimated_bits += chinfo['part2_3_length']
        # convert bits to bytes (ceil)
        estimated_main_bytes = (estimated_bits + 7) // 8
        # bound estimated_main_bytes not to exceed available space
        max_possible_main = max(0, (i + frame_size) - main_data_idx)
        if estimated_main_bytes > max_possible_main:
            # best-effort clamp
            estimated_main_bytes = max_possible_main
        ancillary_idx = main_data_idx + estimated_main_bytes
        ancillary_len = (i + frame_size) - ancillary_idx
        results.append({
            'frame_index': frame_idx,
            'header_idx': header_idx,
            'frame_start': i,
            'frame_size': frame_size,
            'side_info_idx': side_info_idx,
            'side_info_size': side_info_size,
            'main_data_idx': main_data_idx,
            'estimated_main_bytes': estimated_main_bytes,
            'ancillary_idx': ancillary_idx,
            'ancillary_len': ancillary_len,
            'parsed_side_info': parsed
        })
        i += frame_size
        frame_idx += 1
    return results

# ---------- embedding/extraction helpers ----------
def scramble_frames_with_seed(frames_info: List[Dict], seed: int) -> List[Dict]:
    """
    Scramble the order of frames using a seed for reproducible randomization.
    
    Args:
        frames_info: Original frames list from scan_frames_for_ancillary
        seed: Integer seed for reproducible randomization
    
    Returns:
        New list with frames in scrambled order
    """
    # Create a copy to avoid modifying the original
    scrambled_frames = frames_info.copy()
    
    # Set seed for reproducible randomization
    random.seed(seed)
    
    # Shuffle the frames
    random.shuffle(scrambled_frames)
    
    return scrambled_frames
def embed_into_ancillary(mp3_bytes: bytearray, frames_info: List[Dict], payload_bits: str,
                         bits_per_byte: int = 1, step: int = 1, start_frame: int = 0):
    """
    Embed payload_bits (string of '0'/'1') into ancillary bytes' LSBs.
    - bits_per_byte: 1 or 2 (number of LSBs to use in each ancillary byte)
    - step: use every 'step' frames (sparser embedding)
    - start_frame: index to start embedding
    - returns number of bits embedded and list of positions used (frame_index, abs_byte_idx, bit_positions)
    """
    assert bits_per_byte in (1,2,3,4)
    total_capacity_bits = 0
    for f in frames_info:
        if f['ancillary_len'] > 0:
            total_capacity_bits += f['ancillary_len'] * bits_per_byte
    
    # Add 32-bit length prefix to mark payload size
    payload_length = len(payload_bits)
    length_bits = f"{payload_length:032b}"  # 32-bit length prefix
    full_payload = length_bits + payload_bits
    
    if len(full_payload) > total_capacity_bits:
        raise ValueError(f"Payload too large for ancillary capacity: need {len(full_payload)} bits (including 32-bit length), capacity {total_capacity_bits} bits")

    bit_idx = 0
    used = []
    frames_count = len(frames_info)
    for fi in range(start_frame, frames_count, 1):
        f = frames_info[fi]
        if (fi - start_frame) % step != 0:
            continue
        if f['ancillary_len'] <= 0:
            continue
        # iterate bytes in ancillary region
        for b in range(f['ancillary_len']):
            abs_idx = f['ancillary_idx'] + b
            if abs_idx >= len(mp3_bytes):
                break
            orig = mp3_bytes[abs_idx]
            # build new value by taking next bits_per_byte bits
            newval = orig
            bits_collected = []
            for k in range(bits_per_byte):
                if bit_idx >= len(full_payload):
                    bit = 0
                else:
                    bit = int(full_payload[bit_idx])
                bits_collected.append(bit)
                bit_idx += 1
            # assemble bits_collected into integer (MSB-first inside these LSB slots)
            val = 0
            for bit in bits_collected:
                val = (val << 1) | (bit & 1)
            # clear bottom bits_per_byte bits of orig and set val
            mask = (~((1 << bits_per_byte) - 1)) & 0xFF
            newval = (orig & mask) | val
            mp3_bytes[abs_idx] = newval
            used.append((f['frame_index'], abs_idx, bits_collected))
            if bit_idx >= len(full_payload):
                break
        if bit_idx >= len(full_payload):
            break
    return bit_idx, used

def extract_from_ancillary(mp3_bytes: bytes, frames_info: List[Dict], bits_per_byte: int = 1,
                           step: int = 1, start_frame: int = 0, max_bits: Optional[int]=None):
    """
    Read bits from ancillary LSBs in the same traversal order used for embed.
    First reads 32-bit length prefix, then extracts exact payload length.
    Returns concatenated bitstring of just the payload (without length prefix).
    """
    bits = []
    frames_count = len(frames_info)
    collected = 0
    payload_length = None
    target_bits = 32  # Start by reading 32-bit length prefix
    
    for fi in range(start_frame, frames_count, 1):
        f = frames_info[fi]
        if (fi - start_frame) % step != 0:
            continue
        if f['ancillary_len'] <= 0:
            continue
        for b in range(f['ancillary_len']):
            abs_idx = f['ancillary_idx'] + b
            if abs_idx >= len(mp3_bytes):
                break
            byte = mp3_bytes[abs_idx]
            # read bottom bits_per_byte bits
            val = byte & ((1 << bits_per_byte) - 1)
            # append bits in MSB-first order for consistency
            for k in reversed(range(bits_per_byte)):
                bits.append('1' if ((val >> k) & 1) else '0')
                collected += 1
                
                # After reading 32 bits, decode the length and update target
                if collected == 32 and payload_length is None:
                    length_bits = ''.join(bits[:32])
                    payload_length = int(length_bits, 2)
                    target_bits = 32 + payload_length  # Length prefix + actual payload
                    print(f"[*] Detected payload length: {payload_length} bits")
                
                # Stop when we've read the exact amount needed
                if collected >= target_bits:
                    # Return only the payload part (skip the 32-bit length prefix)
                    return ''.join(bits[32:32+payload_length]) if payload_length is not None else ''.join(bits)
                
                # Respect max_bits parameter if provided (for backward compatibility)
                if max_bits is not None and collected >= max_bits:
                    return ''.join(bits)
    
    # If we didn't get enough bits, return what we have (skip length prefix if we got it)
    if payload_length is not None and len(bits) > 32:
        actual_payload_bits = min(payload_length, len(bits) - 32)
        return ''.join(bits[32:32+actual_payload_bits])
    return ''.join(bits)

# ---------- utilities ----------
def bits_from_file(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    bits = ''.join(f"{b:08b}" for b in data)
    return bits

def bits_from_text(s: str) -> str:
    b = s.encode('utf-8')
    bits = ''.join(f"{byte:08b}" for byte in b)
    # optional null terminator to mark end
    bits += "00000000"
    return bits

def bits_to_bytestring_with_terminator(bits: str) -> bytes:
    # pad to byte boundary
    pad = (-len(bits)) % 8
    bits_padded = bits + ('0'*pad)
    out = bytearray()
    for i in range(0, len(bits_padded), 8):
        out.append(int(bits_padded[i:i+8], 2))
    return bytes(out)

def bits_to_text(bits: str) -> str:
    chars = []
    for i in range(0, len(bits), 8):
        if i+8 > len(bits):
            break
        byte = bits[i:i+8]
        if byte == '00000000':
            break
        chars.append(chr(int(byte,2)))
    return ''.join(chars)

# ---------- CLI operations ----------
def cmd_inspect(path: str):
    with open(path, "rb") as f:
        mp3 = f.read()
    frames = scan_frames_for_ancillary(mp3)
    total_anc_bytes = sum(f['ancillary_len'] for f in frames)
    print(f"Frames found: {len(frames)}")
    print(f"Total ancillary bytes available (est): {total_anc_bytes}")
    print("First 20 frame ancillary summaries:")
    for f in frames[:20]:
        print(f" frame {f['frame_index']:4d} at {f['frame_start']:8d} size={f['frame_size']:6d} anc_idx={f['ancillary_idx']:8d} anc_len={f['ancillary_len']:4d}")
    # optional detailed per-frame print for frames with anc
    print("\nNote: these are estimates based on part2_3_length sums. Actual encoder behavior and bit-reservoir may alter real ancillary layout.")

def cmd_embed(input_mp3: str, output_mp3: str, payload_path: Optional[str], text_payload: Optional[str],
              bits_per_byte: int, step: int, start_frame: int):
    with open(input_mp3, "rb") as f:
        mp3 = bytearray(f.read())
    frames = scan_frames_for_ancillary(mp3)
    # build payload bits
    if payload_path:
        payload_bits = bits_from_file(payload_path)
    else:
        assert text_payload is not None
        payload_bits = bits_from_text(text_payload)
    print(f"[*] Payload bits length: {len(payload_bits)}")
    capacity_bits = sum(f['ancillary_len'] * bits_per_byte for f in frames[start_frame::step])
    print(f"[*] Estimated ancillary capacity (bits, using step={step} from frame {start_frame}): {capacity_bits}")
    embedded_bits, used_info = embed_into_ancillary(mp3, frames, payload_bits, bits_per_byte=bits_per_byte, step=step, start_frame=start_frame)
    print(f"[*] Embedded bits: {embedded_bits}")
    print(f"[*] Frames/bytes used (sample): {used_info[:10]}")
    with open(output_mp3, "wb") as f:
        f.write(mp3)
    print(f"[*] Wrote output to {output_mp3}")
    print("[*] Extraction can be done with same step/start_frame and bits_per_byte parameters.")

def embed_binary(input_mp3_data: bytes, payload_data: bytes,
                 bits_per_byte: int = 1, step: int = 1, start_frame: int = 0, seed: int = None) -> bytes:
    """
    Embed payload into MP3 binary data and return the modified MP3 data.
    
    Args:
        input_mp3_data: MP3 file data as bytes
        payload_data: Binary payload data to embed
        bits_per_byte: Number of LSBs to use per ancillary byte (1 or 2)
        step: Use every N-th frame for embedding
        start_frame: Frame index to start embedding at
        scramble_seed: Optional seed for scrambling frame order (None = no scrambling)
    
    Returns:
        Modified MP3 data as bytes
    """
    mp3 = bytearray(input_mp3_data)
    frames = scan_frames_for_ancillary(mp3)
    
    # Scramble frames if seed is provided
    if seed is not None:
        frames = scramble_frames_with_seed(frames, seed)
        print(f"[*] Scrambled frame order using seed: {seed}")
    
    # convert payload binary data to bits
    payload_bits = ''.join(f"{b:08b}" for b in payload_data)
    
    print(f"[*] Payload bits length: {len(payload_bits)}")
    capacity_bits = sum(f['ancillary_len'] * bits_per_byte for f in frames[start_frame::step])
    print(f"[*] Estimated ancillary capacity (bits, using step={step} from frame {start_frame}): {capacity_bits}")
    
    embedded_bits, used_info = embed_into_ancillary(mp3, frames, payload_bits, bits_per_byte=bits_per_byte, step=step, start_frame=start_frame)
    print(f"[*] Embedded bits: {embedded_bits}")
    print(f"[*] Frames/bytes used (sample): {used_info[:10]}")
    
    return bytes(mp3)

def extract_binary(input_mp3_data: bytes, bits_per_byte: int = 1, step: int = 1, start_frame: int = 0, seed: int = None) -> bytes:
    """
    Extract payload from MP3 binary data and return the extracted binary data.
    
    Args:
        input_mp3_data: MP3 file data as bytes
        bits_per_byte: Number of LSBs used per ancillary byte (1 or 2)
        step: Frame step used during embedding
        start_frame: Frame index where embedding started
        scramble_seed: Seed used for scrambling during embedding (None = no scrambling)
    
    Returns:
        Extracted binary data as bytes
    """
    frames = scan_frames_for_ancillary(input_mp3_data)
    
    # Use same scrambling as during embedding
    if seed is not None:
        frames = scramble_frames_with_seed(frames, seed)
        print(f"[*] Using scrambled frame order with seed: {seed}")
    
    bitstr = extract_from_ancillary(input_mp3_data, frames, bits_per_byte=bits_per_byte, step=step, start_frame=start_frame)
    
    print(f"[*] Extracted bits length: {len(bitstr)} (first 200 chars): {bitstr[:200]}")
    
    # Convert bits back to bytes
    data = bits_to_bytestring_with_terminator(bitstr)
    return data

def cmd_extract(input_mp3: str, output_path: Optional[str], bits_per_byte: int, step: int, start_frame: int, max_bits: Optional[int], to_text: bool):
    with open(input_mp3, "rb") as f:
        mp3 = f.read()
    frames = scan_frames_for_ancillary(mp3)
    bitstr = extract_from_ancillary(mp3, frames, bits_per_byte=bits_per_byte, step=step, start_frame=start_frame, max_bits=max_bits)
    print(f"[*] Extracted bits length: {len(bitstr)} (first 200 chars): {bitstr[:200]}")
    if to_text:
        txt = bits_to_text(bitstr)
        print("[*] Recovered text (best-effort):")
        print(txt)
        if output_path:
            with open(output_path, "wb") as fo:
                fo.write(txt.encode('utf-8'))
            print(f"[*] Wrote text to {output_path}")
    else:
        # write raw bytes
        if output_path:
            data = bits_to_bytestring_with_terminator(bitstr)
            with open(output_path, "wb") as fo:
                fo.write(data)
            print(f"[*] Wrote extracted bytes to {output_path}")
        else:
            print("No output path provided; skipping write.")

def parse_args():
    p = argparse.ArgumentParser(description="Embed/extract LSBs into MP3 frame ancillary bytes (best-effort).")
    sub = p.add_subparsers(dest='cmd', required=True)
    pi = sub.add_parser('inspect', help='Inspect MP3 and report ancillary availability')
    pi.add_argument('input', help='input mp3 path')

    pe = sub.add_parser('embed', help='Embed payload into ancillary LSBs')
    pe.add_argument('input', help='input mp3 path')
    pe.add_argument('output', help='output mp3 path')
    group = pe.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='file to embed as payload (binary)')
    group.add_argument('--text', help='text message to embed (UTF-8)')
    pe.add_argument('--bits-per-byte', type=int, default=1, choices=[1,2], help='LSBs per ancillary byte to use')
    pe.add_argument('--step', type=int, default=1, help='use every N-th frame (sparse embedding)')
    pe.add_argument('--start-frame', type=int, default=0, help='frame index to start embedding at')
    pe.add_argument('--max-bytes', type=int, default=None, help='max ancillary bytes to use overall (safety limit)')

    px = sub.add_parser('extract', help='Extract payload from ancillary LSBs')
    px.add_argument('input', help='input mp3 path')
    px.add_argument('--output', help='output path for extracted payload (raw bytes or text)')
    px.add_argument('--text', action='store_true', help='interpret extracted bytes as text and print')
    px.add_argument('--bits-per-byte', type=int, default=1, choices=[1,2], help='LSBs per ancillary byte used')
    px.add_argument('--step', type=int, default=1, help='use same step as embedding')
    px.add_argument('--start-frame', type=int, default=0, help='frame index used as start during embed')
    px.add_argument('--max-bits', type=int, default=None, help='max bits to extract')
    return p.parse_args()

def main():
    args = parse_args()
    if args.cmd == 'inspect':
        cmd_inspect(args.input)
    elif args.cmd == 'embed':
        cmd_embed(args.input, args.output, args.file, args.text, bits_per_byte=args.bits_per_byte, step=args.step, start_frame=args.start_frame)
    elif args.cmd == 'extract':
        cmd_extract(args.input, args.output, bits_per_byte=args.bits_per_byte, step=args.step, start_frame=args.start_frame, max_bits=args.max_bits, to_text=args.text)
    else:
        print("unknown command")

if __name__ == "__main__":
    main()
