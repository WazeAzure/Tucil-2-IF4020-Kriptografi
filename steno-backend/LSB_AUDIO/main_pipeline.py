import re
import json
import struct
import math

import LSB_AUDIO.cipher as ci
import LSB_AUDIO.ancillary_data as ad

def extractFileExtention(filename: str) -> str:
    match = re.search(r"\.([^.]+)$", filename)
    return match.group(1) if match else None

def calculate_psnr(original_data: bytes, embedded_data: bytes) -> float:
    if len(original_data) != len(embedded_data):
        raise ValueError("Audio data lengths must be equal for PSNR calculation")
    
    if len(original_data) == 0:
        raise ValueError("Audio data cannot be empty")
    
    mse = 0.0
    for i in range(len(original_data)):
        diff = int(original_data[i]) - int(embedded_data[i])
        mse += diff * diff
    
    mse = mse / len(original_data)
    
    if mse == 0:
        return float('inf')  # Perfect quality
    
    max_pixel_value = 255.0
    psnr = 20 * math.log10(max_pixel_value / math.sqrt(mse))
    
    return round(psnr, 2)

def encrypt(config : dict, audio_data, embed_data):
    # config['originalFileName'] = mp3_filename
    # config['embeddedFileName'] = embed_filename
    # config['useEncryption'] = use_encryption
    # config['randomEmbedding'] = random_embedding
    # config['lsbBits'] = lsb_bits
    # config['encryptionKey'] = key if key else None
    for key, value in config.items():
        print(f"{key}: {value}")

    extension = extractFileExtention(config["embeddedFileName"])

    embbedded_config = {
        "fn" : config['embeddedFileName'],
        "en" : config['useEncryption'],
        "re" : config['randomEmbedding'],
        "ls" : config['lsbBits'],
    }

    if (config['encryptionKey'] is not None):
        generated_key = ci.generateKey(config['encryptionKey'])
        generated_seed = ci.generateSeed(generated_key)
        print("Generated Key:", generated_key)
        print("Generated Seed:", generated_seed)
    
    embbedded_config_json = json.dumps(embbedded_config).encode("utf-8")
    config_length = len(embbedded_config_json)
    config_len_bytes = struct.pack(">I", config_length)

    payload_data = config_len_bytes + embbedded_config_json + embed_data
    
    seed = None

    if config['encryptionKey'] is not None:
        payload_data = ci.vignereCipher(payload_data, generated_key)
    
    if config["randomEmbedding"]:
        seed = ci.generateSeed(generated_key)

    final_payload = payload_data

    result = ad.embed_binary(audio_data,
                    final_payload,
                    bits_per_byte=config['lsbBits'],
                    step=1,
                    start_frame=0,
                    seed=seed)
    
    psnr_value = calculate_psnr(audio_data, result)
    print(f"PSNR between original and embedded audio: {psnr_value} dB")
    print("embbedded_config_json:", embbedded_config_json)
    
    return result, psnr_value

def decrypt(audio_data, key=None, is_scrambled=False, is_encrypted=False, bits_per_byte = 1):
    scramble_seed = None
    if is_scrambled and key is not None:
        generated_key = ci.generateKey(key)
        scramble_seed = ci.generateSeed(generated_key)
        print("Generated Key:", generated_key)
        print("Generated Scramble Seed:", scramble_seed)
    elif key is not None:
        generated_key = ci.generateKey(key)
        print("Generated Key:", generated_key)
    
    result = ad.extract_binary(audio_data, step=1, start_frame=0, seed=scramble_seed, bits_per_byte=bits_per_byte)
    if result is None:
        raise ValueError("No hidden data found in the audio file.")
    
    if is_encrypted and key is not None:
        decrypted_payload = ci.vignereDecipher(result, generated_key)
    else:
        decrypted_payload = result

    config_length = struct.unpack(">I", decrypted_payload[:4])[0]
    
    config_json = decrypted_payload[4:4+config_length]
    config = json.loads(config_json.decode("utf-8"))
    
    extracted_data = decrypted_payload[4+config_length:]

    print("Extracted Config:", config)
    return config, extracted_data