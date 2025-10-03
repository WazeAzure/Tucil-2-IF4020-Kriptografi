import struct

def text_to_bits(text: str) -> str:
    """Convert text to binary string."""
    return ''.join(f"{ord(c):08b}" for c in text)

def bits_to_text(bits: str) -> str:
    """Convert binary string to text."""
    chars = []
    for i in range(0, len(bits), 8):
        if i + 8 <= len(bits):
            byte_val = int(bits[i:i+8], 2)
            if byte_val == 0:  # Stop at null terminator
                break
            chars.append(chr(byte_val))
    return ''.join(chars)

def mute_side_info(mp3_bytes: bytearray, start: int, side_info_size: int):
    for k in range(start, start + side_info_size):
        mp3_bytes[k] = 0
        
def is_valid_frame_sync(header: bytes) -> bool:
    """Check if frame sync is valid (11 bits set)."""
    if len(header) < 4:
        return False
    return (header[0] == 0xFF) and ((header[1] & 0xE0) == 0xE0)

def get_frame_info(header: bytes) -> dict:
    """Extract frame information from MP3 header."""
    if len(header) < 4:
        return None
    
    # MPEG version
    mpeg_version = (header[1] >> 3) & 0x03
    if mpeg_version == 0 or mpeg_version == 1:  # Reserved or MPEG 2.5
        mpeg_version = 2  # MPEG 2
    elif mpeg_version == 2:
        mpeg_version = 2  # MPEG 2
    elif mpeg_version == 3:
        mpeg_version = 1  # MPEG 1
    
    # Layer
    layer = (header[1] >> 1) & 0x03
    if layer == 1:
        layer = 3  # Layer III
    elif layer == 2:
        layer = 2  # Layer II
    elif layer == 3:
        layer = 1  # Layer I
    else:
        return None
    
    # Bitrate index
    bitrate_idx = (header[2] >> 4) & 0x0F
    
    # Sample rate index
    samplerate_idx = (header[2] >> 2) & 0x03
    
    # Padding
    padding = (header[2] >> 1) & 0x01
    
    # Channel mode
    channel_mode = (header[3] >> 6) & 0x03
    
    # Bitrate table for MPEG1 Layer III
    bitrate_table_v1_l3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
    # Bitrate table for MPEG2 Layer III
    bitrate_table_v2_l3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
    
    # Sample rate table
    samplerate_table_v1 = [44100, 48000, 32000, 0]
    samplerate_table_v2 = [22050, 24000, 16000, 0]
    
    # Get bitrate
    if mpeg_version == 1 and layer == 3:
        bitrate = bitrate_table_v1_l3[bitrate_idx] * 1000
    else:
        bitrate = bitrate_table_v2_l3[bitrate_idx] * 1000
    
    # Get sample rate
    if mpeg_version == 1:
        samplerate = samplerate_table_v1[samplerate_idx]
    else:
        samplerate = samplerate_table_v2[samplerate_idx]
    
    if bitrate == 0 or samplerate == 0:
        return None
    
    # Calculate frame size
    if layer == 3:  # Layer III
        if mpeg_version == 1:
            frame_size = int(144 * bitrate / samplerate) + padding
        else:
            frame_size = int(72 * bitrate / samplerate) + padding
    else:
        frame_size = int(144 * bitrate / samplerate) + padding
    
    # Determine side info size
    if channel_mode == 3:  # Mono
        side_info_size = 17
    else:  # Stereo, Joint Stereo, Dual Channel
        side_info_size = 32
    
    return {
        'frame_size': frame_size,
        'side_info_size': side_info_size,
        'mpeg_version': mpeg_version,
        'layer': layer,
        'channel_mode': channel_mode
    }

def skip_id3v2_tag(mp3_bytes: bytes) -> int:
    """Skip ID3v2 tag if present and return offset."""
    if len(mp3_bytes) < 10:
        return 0
    
    if mp3_bytes[0:3] == b'ID3':
        # ID3v2 tag found
        size = ((mp3_bytes[6] & 0x7F) << 21) | \
               ((mp3_bytes[7] & 0x7F) << 14) | \
               ((mp3_bytes[8] & 0x7F) << 7) | \
               (mp3_bytes[9] & 0x7F)
        return 10 + size  # Header (10 bytes) + tag size
    
    return 0

def embed_lsb(mp3_in: str, mp3_out: str, message: str, step: int = 2):
    """Embed message into MP3 using sparse LSB in main data of each frame.
       step menentukan interval (misal 3 → tiap frame ke-3 saja)."""
    with open(mp3_in, "rb") as f:
        mp3_bytes = bytearray(f.read())
    
    # Add delimiter ke pesan
    message_with_delimiter = message + "\x00\x00"
    bits = text_to_bits(message_with_delimiter)
    
    print(f"Message length: {len(message)} chars")
    print(f"Bits to embed: {len(bits)} bits")
    
    bit_idx = 0
    frames_processed = 0
    frame_counter = 0  # hitung semua frame
    
    # Skip ID3v2 tag
    i = skip_id3v2_tag(mp3_bytes)
    print(f"Starting at offset: {i}")
    
    while i < len(mp3_bytes) and bit_idx < len(bits):
        if i + 4 > len(mp3_bytes):
            break
        
        header = mp3_bytes[i:i+4]
        print(header)
        if not is_valid_frame_sync(header):
            i += 1
            continue
        
        frame_info = get_frame_info(header)
        if frame_info is None or frame_info['frame_size'] <= 0:
            i += 1
            continue
        
        frame_size = frame_info['frame_size']
        print(frame_size)
        
        side_info_size = frame_info['side_info_size']
        print(side_info_size)
        
        if i + frame_size > len(mp3_bytes):
            break
        
        main_data_start = i + 4 + side_info_size
        if main_data_start >= i + frame_size:
            i += frame_size
            continue
        
        # hanya embed kalau sesuai step
        if frame_counter % step == 0:
            for j in range(main_data_start, i + frame_size):
                if bit_idx >= len(bits):
                    break
                mp3_bytes[j] = (mp3_bytes[j] & 0xFE) | int(bits[bit_idx])
                bit_idx += 1
            # mute side info (opsional, kalau mau tetap hilangkan noise)
            mute_side_info(mp3_bytes, i+4, side_info_size)
            frames_processed += 1
        
        frame_counter += 1
        i += frame_size
    
    print(f"Frames used: {frames_processed} (every {step} frames)")
    print(f"Bits embedded: {bit_idx}/{len(bits)}")
    
    if bit_idx < len(bits):
        print(f"WARNING: Not all bits embedded! Missing {len(bits) - bit_idx} bits")
    
    with open(mp3_out, "wb") as f:
        f.write(mp3_bytes)
    
    print(f"Output written to {mp3_out}")


def extract_lsb(mp3_file: str) -> str:
    """Extract message from MP3 embedded via LSB."""
    with open(mp3_file, "rb") as f:
        mp3_bytes = f.read()
    
    bits = ""
    frames_processed = 0
    
    # Skip ID3v2 tag
    i = skip_id3v2_tag(mp3_bytes)
    
    while i < len(mp3_bytes):
        if i + 4 > len(mp3_bytes):
            break
        
        header = mp3_bytes[i:i+4]
        
        if not is_valid_frame_sync(header):
            i += 1
            continue
        
        frame_info = get_frame_info(header)
        
        if frame_info is None or frame_info['frame_size'] <= 0:
            i += 1
            continue
        
        frame_size = frame_info['frame_size']
        side_info_size = frame_info['side_info_size']
        
        if i + frame_size > len(mp3_bytes):
            break
        
        main_data_start = i + 4 + side_info_size
        
        if main_data_start >= i + frame_size:
            i += frame_size
            continue
        
        # Extract LSBs from main data
        for j in range(main_data_start, i + frame_size):
            bits += str(mp3_bytes[j] & 1)
            
            # Check for double null terminator every 16 bits
            if len(bits) >= 16 and len(bits) % 8 == 0:
                if bits[-16:] == "0000000000000000":
                    message = bits_to_text(bits[:-16])
                    print(f"Frames processed: {frames_processed}")
                    print(f"Bits extracted: {len(bits)}")
                    return message
        
        frames_processed += 1
        i += frame_size
    
    print(f"Frames processed: {frames_processed}")
    print(f"Bits extracted: {len(bits)}")
    return bits_to_text(bits)

# ======================
# DEMO
# ======================
if __name__ == "__main__":
    # Test with embedding
    test_message = "HELLO WORLD! This is a secret message."*1000
    print(f"\n=== EMBEDDING ===")
    embed_lsb("stego.mp3", "rebuilt.mp3", test_message)
    
    print(f"\n=== EXTRACTING ===")
    extracted_msg = extract_lsb("rebuilt.mp3")
    print(f"\nOriginal:  '{test_message}'")
    print(f"Extracted: '{extracted_msg}'")
    print(f"Match: {test_message == extracted_msg}")