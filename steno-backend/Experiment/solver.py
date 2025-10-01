import sys
import struct

# CRC16-IBM for MP3
def crc16_ibm(data: bytes, poly=0x8005, init=0xFFFF) -> int:
    crc = init
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def parse_header(header_bytes):
    """Parse MP3 4-byte header into fields"""
    b1, b2, b3, b4 = struct.unpack(">BBBB", header_bytes)

    sync = (b1 << 3) | (b2 >> 5)
    if (sync & 0x7FF) != 0x7FF:  # not a frame header
        return None

    version_id = (b2 >> 3) & 0b11
    layer = (b2 >> 1) & 0b11
    protection_bit = b2 & 0b1
    bitrate_index = (b3 >> 4) & 0xF
    samplerate_index = (b3 >> 2) & 0b11
    padding_bit = (b3 >> 1) & 0b1
    channel_mode = (b4 >> 6) & 0b11

    return {
        "version_id": version_id,
        "layer": layer,
        "protection_bit": protection_bit,
        "bitrate_index": bitrate_index,
        "samplerate_index": samplerate_index,
        "padding_bit": padding_bit,
        "channel_mode": channel_mode,
    }

def modify_lsb(byte: int, bit: int) -> int:
    """Flip the LSB of a byte to given bit (0 or 1)."""
    return (byte & 0xFE) | (bit & 1)

def process_mp3(filename, outfile):
    with open(filename, "rb") as f:
        data = f.read()

    pos = 0
    frame_idx = 0
    out_data = bytearray()

    while pos < len(data) - 4:
        if frame_idx % 4 == 0:
            frame_idx += 1
            continue
        
        header = data[pos:pos+4]
        fields = parse_header(header)
        if not fields:
            pos += 1
            out_data.append(data[pos])
            continue

        # MPEG1, Layer III only (simplified)
        version = fields["version_id"]
        layer = fields["layer"]
        bitrate_index = fields["bitrate_index"]
        samplerate_index = fields["samplerate_index"]
        padding = fields["padding_bit"]
        protection_bit = fields["protection_bit"]

        # Use bitrate/samplerate tables (simplified for demo)
        bitrate_table = [None, 32000, 40000, 48000, 56000, 64000, 80000,
                         96000, 112000, 128000, 160000, 192000, 224000,
                         256000, 320000, None]
        samplerate_table = [44100, 48000, 32000, None]

        bitrate = bitrate_table[bitrate_index]
        samplerate = samplerate_table[samplerate_index]

        if bitrate is None or samplerate is None:
            pos += 1
            out_data.append(data[pos])
            continue

        frame_len = int(144 * bitrate / samplerate) + padding
        frame = bytearray(data[pos:pos+frame_len])

        # Skip header
        crc_offset = 4
        if protection_bit == 0:
            crc_offset += 2  # CRC present

        main_data = frame[crc_offset:]

        # === Stego: Modify first byte's LSB to 1 ===
        if len(main_data) > 0:
            main_data[0] = modify_lsb(main_data[0], 1)
            frame[crc_offset:] = main_data

        # === Recalculate CRC if needed ===
        if protection_bit == 0:
            crc_data = frame[4:]  # after header
            crc_val = crc16_ibm(crc_data)
            frame[4:6] = struct.pack(">H", crc_val)

        out_data.extend(frame)

        print(f"Frame {frame_idx} @ {pos}: len={frame_len}, bitrate={bitrate}, samplerate={samplerate}, crc={'yes' if protection_bit==0 else 'no'}")
        pos += frame_len
        frame_idx += 1

    with open(outfile, "wb") as f:
        f.write(out_data)

    print(f"Modified MP3 written to {outfile}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python parser.py input.mp3 output.mp3")
    else:
        process_mp3(sys.argv[1], sys.argv[2])

