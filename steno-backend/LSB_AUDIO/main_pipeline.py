import re
import json

import LSB_AUDIO.cipher as ci

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

    embbedded_config_json = json.dumps(embbedded_config)
    if (config['encryptionKey'] is not None):
        generated_key = ci.generateKey(config['encryptionKey'])
        generated_seed = ci.generateSeed(generated_key)
        print("Generated Key:", generated_key)
        print("Generated Seed:", generated_seed)
        ciphered_data = ci.vignereCipher(embed_data, generated_key)

        print("Ciphered Data:", ciphered_data)
    

    print("embbedded_config_json:", embbedded_config_json)