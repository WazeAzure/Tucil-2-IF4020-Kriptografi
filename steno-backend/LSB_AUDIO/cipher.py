key=b"ilovedota2"

def vignereCipher(input: bytes, key: bytes)-> bytes:
    output = bytearray()
    key_length = len(key)
    for i in range(len(input)):
        key_c = key[i % key_length]
        output.append((input[i] + key_c) % 256)
    return bytes(output)

def vignereDecipher(input: bytes, key: bytes)-> bytes:
    output = bytearray()
    key_length = len(key)
    for i in range(len(input)):
        key_c = key[i % key_length]
        output.append((input[i] - key_c) % 256)
    return bytes(output)

def generateKey(text : str) -> str:
    encoded_text = text.encode()
    key_result = vignereCipher(encoded_text, key=key)
    return key_result

def generateSeed(text : bytes) -> int:
    seed = 0
    for char in text:
        seed += int(char)
    return seed*seed