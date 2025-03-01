import binascii
import json
import random
import struct
import time
from typing import TypeVar

from beancount.core import data
from gmssl.sm2 import CryptSM2
from gmssl.sm3 import sm3_hash
from gmssl.sm4 import SM4_DECRYPT, SM4_ENCRYPT, CryptSM4

Transaction = TypeVar("Transaction", bound=data.Transaction)

OT = "6D7C4194F913953339B87FCF7D1B6E2358439912B54D822F0235B3BA3CA9E9FB"
ST = "ACA0676AF369D80DAD3C243ABBF885460D9E95D2CE6C538208814DE94D017413"


BLOCK_LENGTH = 64


def _xor_bytes(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def _hmac_sm3_key(key: str):
    k = _str_key_to_bytes(key)

    if len(k) > BLOCK_LENGTH:
        k = bytes.fromhex(sm3_hash([b for b in k]))

    if len(k) < BLOCK_LENGTH:
        k = k + b"\x00" * (BLOCK_LENGTH - len(k))

    return k


def _hmac_sm3(data: str, key: str):
    """
    计算HMAC-SM3
    使用SM3哈希函数实现标准HMAC算法

    Args:
        data: 要签名的数据字符串
        key: 用于签名的密钥字符串

    Returns:
        str: 十六进制表示的HMAC值
    """
    # 1. 处理密钥为标准长度
    k = _hmac_sm3_key(key)

    # 4. 准备内外填充
    o_key_pad = _xor_bytes(k, b"\x5c" * BLOCK_LENGTH)
    i_key_pad = _xor_bytes(k, b"\x36" * BLOCK_LENGTH)

    # 5. 计算内部哈希
    inner_data = i_key_pad + _encode_utf8(data)
    inner_hash = sm3_hash(list(inner_data))

    # 6. 计算外部哈希
    outer_data = o_key_pad + bytes.fromhex(inner_hash)
    outer_hash = sm3_hash(list(outer_data))

    return outer_hash.upper()


def generate_key(length=32):
    chars = "0123456789ABCDEF"
    return "".join(random.choice(chars) for _ in range(length))


def _encode_utf8(text: str) -> bytes:
    return text.encode("utf-8")


def _utf8_parse_like_crypto_js(text: str):
    bytes_data = text.encode("utf-8")

    # 计算需要多少个32位words
    word_count = (len(bytes_data) + 3) // 4

    # 创建words数组
    words = []
    for i in range(word_count):
        start = i * 4
        end = min(start + 4, len(bytes_data))

        # 填充不足4字节的部分
        chunk = bytes_data[start:end].ljust(4, b"\x00")

        # 转换为32位整数
        word = struct.unpack(">I", chunk)[0]
        words.append(word)

    return {"words": words, "sigBytes": len(bytes_data)}


def _word_array_to_hex(word_array) -> str:
    words = word_array["words"]
    sig_bytes = word_array["sigBytes"]

    result = ""
    for i in range((sig_bytes + 3) // 4):
        word = words[i]
        bytes_to_process = min(4, sig_bytes - i * 4)

        for j in range(bytes_to_process):
            byte_val = (word >> (24 - j * 8)) & 0xFF
            result += f"{byte_val:02x}"

    return result


def _get_words(hex_string) -> bytes:
    result = []
    for i in range(0, len(hex_string), 2):
        if i + 1 < len(hex_string):
            byte_val = int(hex_string[i : i + 2], 16)
            result.append(byte_val)

    return bytes(result)


def _generate_nonce(key: str) -> str:
    word_array = _utf8_parse_like_crypto_js(key)
    hex_string = _word_array_to_hex(word_array)
    byte_array = _get_words(hex_string)

    sm2 = CryptSM2(public_key=OT + ST, private_key="", mode=1)
    encrypted_bytes = sm2.encrypt(byte_array)
    return "04" + binascii.hexlify(encrypted_bytes).decode("utf-8")


def _str_key_to_bytes(key: str) -> bytes:
    if all(c in "0123456789ABCDEFabcdef" for c in key):
        key_bytes = binascii.unhexlify(key)
    else:
        key_bytes = _encode_utf8(key)

    if len(key_bytes) > 16:
        key_bytes = key_bytes[:16]
    elif len(key_bytes) < 16:
        key_bytes = key_bytes + b"\x00" * (16 - len(key_bytes))

    return key_bytes


def _encrypt_sm4(data: str, key: str):
    processed_key = _str_key_to_bytes(key)

    crypt_sm4 = CryptSM4()
    crypt_sm4.set_key(processed_key, SM4_ENCRYPT)

    encrypted_data = crypt_sm4.crypt_ecb(_encode_utf8(data))

    return binascii.b2a_base64(encrypted_data, newline=False).decode("utf-8")


def _decrypt_sm4(encrypted_data, key):
    processed_key = _str_key_to_bytes(key)

    crypt_sm4 = CryptSM4()
    crypt_sm4.set_key(processed_key, SM4_DECRYPT)

    # Base64解码
    data_bytes = binascii.a2b_base64(encrypted_data)

    # ECB模式解密
    decrypted_data = crypt_sm4.crypt_ecb(data_bytes)

    # 移除PKCS#7填充
    padding_length = decrypted_data[-1]
    if padding_length > 0 and padding_length <= 16:
        # 验证填充
        for i in range(1, padding_length + 1):
            if decrypted_data[-i] != padding_length:
                raise ValueError("Invalid PKCS#7 padding")
        decrypted_data = decrypted_data[:-padding_length]

    return decrypted_data.decode("utf-8")


def encrypt_request(request_data: dict, key: str):
    json_str = json.dumps(request_data, separators=(",", ":"))
    encrypted_data = _encrypt_sm4(json_str, key)
    timestamp = int(time.time() * 1000)
    sign_result = _hmac_sm3(str(timestamp) + json_str, key)
    nonce = _generate_nonce(key)

    return {"data": encrypted_data, "timestamp": timestamp, "nonce": nonce, "sign": sign_result}


def decrypt_response(encrypted_response: str, key: str):
    decrypted_data_str = _decrypt_sm4(encrypted_response, key)
    return json.loads(decrypted_data_str)
