
"""
mp3_main_data_bitops.py

Purpose:
- Parse MP3 frames (basic MPEG-1 Layer III support).
- Extract per-frame:
    - header (4 bytes)
    - side_info (raw bytes)
    - main_data (raw bytes after side_info up to frame boundary)
- Concatenate main_data from frames into a single bytearray `main_data_concat`.
- Build a mapping structure to convert a bit-offset within `main_data_concat`
  back to the original mp3 byte index (so edits can be written back).
- Provide functions to flip bits in the concatenated main_data and commit edits
  to a new MP3 file.

Limitations / Assumptions:
- Best-effort for MPEG-1 Layer III (most common files). Some other variants may work,
  but full support for MPEG-2/2.5 and every corner-case isn't guaranteed.
- This tool does NOT decode Huffman tables or find sign bits automatically.
  Use it as the safe low-level editing layer: once you have bit offsets for sign bits,
  you can flip them here and write out the modified MP3.
- Changing bits may break the bitstream if you change bits that are part of Huffman
  codewords in a way that corrupts frame parsing. Flipping sign bits (which are raw
  1-bit sign flags after Huffman magnitude codewords) is appropriate but be cautious.

Usage:
    python mp3_main_data_bitops.py inspect input.mp3
    python mp3_main_data_bitops.py flip input.mp3 out.mp3 offset1 offset2 ...

Example:
    python mp3_main_data_bitops.py flip song.mp3 song_edited.mp3 12345 67890
    (this flips bit at bit-offset 12345 and 67890 inside the concatenated main_data)

"""
from typing import List, Tuple, Dict
import sys
import struct
import os

# -------------------------
# Low level helpers
# -------------------------
def is_frame_sync(header: bytes) -> bool:
    return len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0

def parse_header(header: bytes):
    """
    Parse 4-byte header and return dict with basic fields.
    Not full validation.
    """
    if len(header) < 4:
        return None
    b0, b1, b2, b3 = header[0], header[1], header[2], header[3]

    # mpeg_version: 3 => MPEG1, 2 => MPEG2, 0 => MPEG2.5 (we simplify)
    ver_bits = (b1 >> 3) & 0x03
    if ver_bits == 3:
        mpeg_version = 1
    elif ver_bits == 2:
        mpeg_version = 2
    else:
        mpeg_version = 2  # treat 0/1 as MPEG2/2.5 in simplified way

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

    side_info_size = 17 if channel_mode == 3 else 32  # mono vs stereo
    return {
        'frame_size': frame_size,
        'side_info_size': side_info_size,
        'mpeg_version': mpeg_version,
        'layer': layer,
        'channel_mode': channel_mode,
        'bitrate': bitrate,
        'samplerate': samplerate
    }

# -------------------------
# Core: extract mapping
# -------------------------
class MP3MainDataMap:
    def __init__(self, mp3_bytes: bytes):
        self.mp3_bytes = bytearray(mp3_bytes)  # editable copy
        self.frames = []  # list of frame metadata dicts
        self.main_data_concat = bytearray()
        # mapping: for each byte of main_data_concat store (frame_index, byte_offset_in_frame, absolute_mp3_index)
        self.byte_map: List[Tuple[int,int,int]] = []

    def build(self):
        i = self._skip_id3v2()
        n = len(self.mp3_bytes)
        frame_idx = 0
        while i < n:
            if i + 4 > n:
                break
            header = bytes(self.mp3_bytes[i:i+4])
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
                # truncated frame => stop
                break

            header_idx = i
            side_info_idx = i + 4
            main_data_idx = i + 4 + side_info_size
            if main_data_idx >= i + frame_size:
                main_len = 0
            else:
                main_len = (i + frame_size) - main_data_idx

            # store frame meta
            frame_meta = {
                'frame_index': frame_idx,
                'header_idx': header_idx,
                'header_bytes': bytes(self.mp3_bytes[header_idx:header_idx+4]),
                'side_info_idx': side_info_idx,
                'side_info_bytes': bytes(self.mp3_bytes[side_info_idx: side_info_idx + side_info_size]),
                'main_data_idx': main_data_idx,
                'main_len': main_len,
                'frame_size': frame_size,
            }
            self.frames.append(frame_meta)

            # append main data bytes and create mapping
            if main_len > 0:
                for off in range(main_len):
                    abs_idx = main_data_idx + off
                    self.main_data_concat.append(self.mp3_bytes[abs_idx])
                    self.byte_map.append((frame_idx, off, abs_idx))

            i += frame_size
            frame_idx += 1

    def _skip_id3v2(self) -> int:
        if len(self.mp3_bytes) < 10:
            return 0
        if self.mp3_bytes[0:3] == b'ID3':
            size = ((self.mp3_bytes[6] & 0x7F) << 21) | ((self.mp3_bytes[7] & 0x7F) << 14) | ((self.mp3_bytes[8] & 0x7F) << 7) | (self.mp3_bytes[9] & 0x7F)
            return 10 + size
        return 0

    def summary(self, max_print=10):
        print(f"Total frames parsed: {len(self.frames)}")
        print(f"Total main_data bytes concatenated: {len(self.main_data_concat)}")
        print("First frames summary:")
        for m in self.frames[:max_print]:
            print(f"frame {m['frame_index']}: header@{m['header_idx']} side@{m['side_info_idx']} main@{m['main_data_idx']} main_len={m['main_len']} frame_size={m['frame_size']}")

    # bit-level helpers
    def bit_get(self, bit_offset:int) -> int:
        """Return single bit value from main_data_concat at bit_offset (0-based)."""
        byte_idx = bit_offset // 8
        bit_in_byte = 7 - (bit_offset % 8)  # big-endian bit order in MP3 bitstream
        if byte_idx < 0 or byte_idx >= len(self.main_data_concat):
            raise IndexError("bit offset out of range")
        return (self.main_data_concat[byte_idx] >> bit_in_byte) & 1

    def bit_flip(self, bit_offset:int):
        """Flip a single bit in main_data_concat and track mapping back to original mp3 bytes."""
        byte_idx = bit_offset // 8
        bit_in_byte = 7 - (bit_offset % 8)
        if byte_idx < 0 or byte_idx >= len(self.main_data_concat):
            raise IndexError("bit offset out of range")
        mask = 1 << bit_in_byte
        # flip in the concatenated buffer
        old = self.main_data_concat[byte_idx]
        new = old ^ mask
        self.main_data_concat[byte_idx] = new
        # find original absolute index and update original mp3 bytes array
        frame_idx, off_in_frame, abs_idx = self.byte_map[byte_idx]
        # update original mp3 byte
        self.mp3_bytes[abs_idx] = new
        return (frame_idx, off_in_frame, abs_idx, old, new)

    def commit_to_file(self, out_path:str):
        with open(out_path, "wb") as f:
            f.write(self.mp3_bytes)
        print(f"Wrote modified mp3 to {out_path}")

# -------------------------
# CLI
# -------------------------
def inspect_file(path:str):
    with open(path, "rb") as f:
        data = f.read()
    m = MP3MainDataMap(data)
    m.build()
    m.summary()
    # save main_data concatenated (optional)
    base = os.path.splitext(path)[0]
    out_main = base + "_main_data.bin"
    with open(out_main, "wb") as w:
        w.write(m.main_data_concat)
    print(f"Wrote concatenated main_data bytes to {out_main}")
    print("You can now inspect main_data and determine sign-bit bit-offsets (in bits).")

def flip_bits_in_file(path:str, out_path:str, bit_offsets:List[int]):
    with open(path, "rb") as f:
        data = f.read()
    m = MP3MainDataMap(data)
    m.build()
    print(f"Main_data total bytes: {len(m.main_data_concat)}, bits: {len(m.main_data_concat)*8}")
    results = []
    for b in bit_offsets:
        try:
            res = m.bit_flip(b)
            results.append(res)
            print(f"Flipped bit {b}: frame {res[0]} off_in_frame {res[1]} abs_idx {res[2]} byte_old=0x{res[3]:02x} byte_new=0x{res[4]:02x}")
        except IndexError as e:
            print(f"Error flipping bit {b}: {e}")
    m.commit_to_file(out_path)

def usage():
    print("Usage:")
    print("  inspect: python mp3_main_data_bitops.py inspect input.mp3")
    print("  flip:    python mp3_main_data_bitops.py flip input.mp3 out.mp3 bit_offset1 [bit_offset2 ...]")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage()
        sys.exit(1)
    cmd = sys.argv[1].lower()
    if cmd == "inspect":
        inspect_file(sys.argv[2])
    elif cmd == "flip":
        if len(sys.argv) < 5:
            usage()
            sys.exit(1)
        infile = sys.argv[2]
        outfile = sys.argv[3]
        bit_offsets = [int(x) for x in sys.argv[4:]]
        flip_bits_in_file(infile, outfile, bit_offsets)
    else:
        usage()