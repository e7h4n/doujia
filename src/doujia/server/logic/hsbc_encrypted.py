import binascii
import json
import random
import time

import requests

# 添加这个导入来禁用警告
import urllib3
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from gmssl import sm3
from gmssl.sm4 import SM4_DECRYPT, SM4_ENCRYPT, CryptSM4

# 禁用不安全请求的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 常量定义
OT = "6D7C4194F913953339B87FCF7D1B6E2358439912B54D822F0235B3BA3CA9E9FB"
ST = "ACA0676AF369D80DAD3C243ABBF885460D9E95D2CE6C538208814DE94D017413"


def generate_random_hex(length=32):
    """生成指定长度的随机十六进制字符串"""
    chars = "0123456789ABCDEF"
    return "".join(random.choice(chars) for _ in range(length))


def str_to_bytes(text):
    """将字符串转换为字节"""
    return text.encode("utf-8")


def sm3_hmac(data, key):
    """使用SM3实现HMAC功能"""
    key_bytes = str_to_bytes(key)
    data_bytes = str_to_bytes(data)

    # 如果密钥长度大于SM3分组大小, 先哈希
    block_size = 64  # SM3的分组大小为64字节
    if len(key_bytes) > block_size:
        key_bytes = binascii.unhexlify(sm3.sm3_hash(list(key_bytes)))

    # 密钥长度不足, 用0填充
    if len(key_bytes) < block_size:
        key_bytes = key_bytes + b"\x00" * (block_size - len(key_bytes))

    # 内部和外部填充
    o_key_pad = bytes((x ^ 0x5C) for x in key_bytes)
    i_key_pad = bytes((x ^ 0x36) for x in key_bytes)

    # HMAC计算 - 转换为list再传给sm3_hash
    inner_hash = sm3.sm3_hash(list(i_key_pad + data_bytes))
    hmac = sm3.sm3_hash(list(o_key_pad + binascii.unhexlify(inner_hash)))

    return hmac


def generate_nonce(key, salt, mode=1):
    """生成nonce - 修改版本以匹配原始JavaScript实现的长度"""
    # 原始JavaScript实现生成的nonce长约256字节 (512个十六进制字符)
    # 我们将使用多次SM3 HMAC迭代来生成足够长的nonce
    result = ""
    seed = key

    # 生成足够长的字符串
    for i in range(16):  # 16次迭代应该能生成足够长的字符串
        current_hash = sm3_hmac(seed + str(i), salt + str(i))
        result += current_hash
        seed = current_hash

    # 确保nonce长度与原始JavaScript实现一致 (约512个字符)
    return result[:512]


def encrypt_sm4(data, key):
    """SM4加密"""
    crypt_sm4 = CryptSM4()
    key_bytes = str_to_bytes(key)

    # 确保密钥长度为16字节
    if len(key_bytes) > 16:
        key_bytes = key_bytes[:16]
    elif len(key_bytes) < 16:
        key_bytes = key_bytes + b"\x00" * (16 - len(key_bytes))

    crypt_sm4.set_key(key_bytes, SM4_ENCRYPT)

    # 数据分组加密
    data_bytes = str_to_bytes(data)
    encrypted_data = crypt_sm4.crypt_ecb(data_bytes)

    return binascii.b2a_base64(encrypted_data).decode().strip()


def decrypt_sm4(encrypted_data, key):
    """SM4解密"""
    crypt_sm4 = CryptSM4()
    key_bytes = str_to_bytes(key)

    # 确保密钥长度为16字节
    if len(key_bytes) > 16:
        key_bytes = key_bytes[:16]
    elif len(key_bytes) < 16:
        key_bytes = key_bytes + b"\x00" * (16 - len(key_bytes))

    crypt_sm4.set_key(key_bytes, SM4_DECRYPT)

    # 解码并解密
    data_bytes = binascii.a2b_base64(encrypted_data)
    decrypted_data = crypt_sm4.crypt_ecb(data_bytes)

    return decrypted_data.decode("utf-8")


def sign(timestamp, data, key):
    """计算签名"""
    sign_data = str(timestamp) + json.dumps(data)
    return sm3_hmac(sign_data, key)


def create_encrypted_request(data, key):
    """创建加密请求"""
    json_str = json.dumps(data)
    encrypted_data = encrypt_sm4(json_str, key)
    timestamp = int(time.time() * 1000)
    sign_result = sign(timestamp, data, key)
    nonce = generate_nonce(key, OT + ST)

    return {"data": encrypted_data, "timestamp": timestamp, "nonce": nonce, "sign": sign_result}


def process_encrypted_response(response, key):
    """处理加密响应"""
    if response and "rspData" in response:
        decrypted_data_str = decrypt_sm4(response["rspData"], key)
        decrypted_data = json.loads(decrypted_data_str)
        response["decryptedData"] = decrypted_data
    return response


def fetch_rsa_public_key():
    """获取RSA公钥"""
    url = "https://creditcards.hsbc.com.cn/nwxhf/pub/applySysKey"
    # 添加 verify=False 参数来忽略SSL证书验证
    response = requests.get(url, verify=False)
    if response.status_code == 200:
        data = response.json()
        if data["code"] == "000000":
            return {"modulus": data["rspData"]["modulus"], "exponent": data["rspData"]["exponent"]}
    return None


def rsa_encrypt(data, public_key):
    """使用RSA公钥加密数据"""
    modulus = int(public_key["modulus"], 16)
    exponent = int(public_key["exponent"], 16)

    # 构造RSA公钥
    key = RSA.construct((modulus, exponent))

    # 创建加密器
    cipher = PKCS1_v1_5.new(key)

    # 加密数据
    data_bytes = str_to_bytes(data)
    encrypted_data = cipher.encrypt(data_bytes)

    # 返回十六进制字符串
    return binascii.hexlify(encrypted_data).decode()


def encrypt_with_public_key(data, public_key):
    """使用与JavaScript函数ht相同的方式加密"""
    data_length = str(len(data))
    if len(data_length) < 2:
        data_length = "0" + data_length

    return rsa_encrypt(data_length + data, public_key)


def query_unbilled_transactions():
    """获取未出账交易, 使用RSA+SM4加密流程"""
    sm4_key = generate_random_hex()

    request_data = {
        "billOption": "A",
    }

    encrypted_request_body = create_encrypted_request(request_data, sm4_key)

    # 5. 发送加密请求
    url = "https://creditcards.hsbc.com.cn/nwxhf/bill/getPendingBills"
    headers = {
        "authorization": "",
        "authorizationguest": "",
        "content-type": "application/json",
    }

    def parse_cookie_string(cookie_str):
        cookies = {}
        if cookie_str:
            cookie_pairs = cookie_str.split("; ")
            for pair in cookie_pairs:
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    cookies[key] = value
        return cookies

    cookie_string = ("",)
    cookies = parse_cookie_string(cookie_string)

    print("json", encrypted_request_body)

    response = requests.post(url, headers=headers, cookies=cookies, json=encrypted_request_body, verify=False)

    # 处理响应
    if response.status_code == 200:
        response_data = response.json()
        # 使用SM4密钥解密响应数据
        decrypted_response = process_encrypted_response(response_data, sm4_key)
        return decrypted_response
    else:
        return {"error": f"Request failed with status code {response.status_code}", "response": response.text}

    # 5. 使用RSA加密SM4密钥(可能需要根据实际流程调整)
    # encrypted_sm4_key = encrypt_with_public_key(sm4_key, public_key)

    # 6. 发送请求并处理响应
    # ...

    return encrypted_request_body
