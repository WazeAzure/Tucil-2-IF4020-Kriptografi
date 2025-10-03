import re
import json
import struct

import LSB_AUDIO.cipher as ci
import LSB_AUDIO.ancillary_data as ad

def extractFileExtention(filename: str) -> str:
    match = re.search(r"\.([^.]+)$", filename)
    return match.group(1) if match else None

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

    if config['lsbBits'] not in [1, 2]:
        config['lsbBits'] = 1

    if (config['encryptionKey'] is not None):
        generated_key = ci.generateKey(config['encryptionKey'])
        generated_seed = ci.generateSeed(generated_key)
        print("Generated Key:", generated_key)
        print("Generated Seed:", generated_seed)
    
    embbedded_config_json = json.dumps(embbedded_config).encode("utf-8")
    config_length = len(embbedded_config_json)
    config_len_bytes = struct.pack(">I", config_length)

    payload_data = embbedded_config_json + embed_data
    
    seed = None

    if config['encryptionKey'] is not None:
        payload_data = ci.vignereCipher(payload_data, generated_key)
        seed = ci.generateSeed(generated_key)
    
    final_payload = config_len_bytes + payload_data

    result = ad.embed_binary(audio_data,
                    final_payload,
                    bits_per_byte=config['lsbBits'],
                    step=1,
                    start_frame=0,
                    seed=seed)
    print("embbedded_config_json:", embbedded_config_json)
    return result

def decrypt(audio_data, key=None, is_scrambled=False, is_encrypted=False):
    scramble_seed = None
    if is_scrambled and key is not None:
        generated_key = ci.generateKey(key)
        scramble_seed = ci.generateSeed(generated_key)
        print("Generated Key:", generated_key)
        print("Generated Scramble Seed:", scramble_seed)
    elif key is not None:
        generated_key = ci.generateKey(key)
        print("Generated Key:", generated_key)
    
    result = ad.extract_binary(audio_data, step=1, start_frame=0, seed=scramble_seed)
    if result is None:
        raise ValueError("No hidden data found in the audio file.")
    
    config_length = struct.unpack(">I", result[:4])[0]
    encrypted_payload = result[4:]
    
    if is_encrypted and key is not None:
        decrypted_payload = ci.vignereDecipher(encrypted_payload, generated_key)
    else:
        decrypted_payload = encrypted_payload
    
    config_json = decrypted_payload[:config_length]
    config = json.loads(config_json.decode("utf-8"))
    
    extracted_data = decrypted_payload[config_length:]

    print("Extracted Config:", config)
    return config, extracted_data