def vignereCipher(input: bytes, key: str)-> bytes:
    output = bytearray()
    key_bytes = key.encode()
    key_length = len(key_bytes)
    for i in range(len(input)):
        key_c = key_bytes[i % key_length]
        print("key :", key_c)
        output.append((input[i] + key_c) % 256)
        print((input[i] + key_c) % 256)
    return bytes(output)

def vignereDecipher(input: bytes, key: str)-> bytes:
    output = bytearray()
    key_bytes = key.encode()
    key_length = len(key_bytes)
    for i in range(len(input)):
        key_c = key_bytes[i % key_length]
        output.append((input[i] - key_c) % 256)
    return bytes(output)

print(vignereCipher(b"hello", "key"))