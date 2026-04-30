"""
Cryptography Capability - NO RESTRICTIONS
Supports: AES, RSA, XOR, Base64, and custom schemes
"""
import base64
import hashlib
from typing import Dict, Optional

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


class CryptoCapability:
    """Complete cryptography toolkit - no restrictions"""

    def __init__(self):
        """Initialize crypto capability"""
        pass

    # ===== BASE64 =====

    def base64_encode(self, data: bytes) -> str:
        """Encode to base64"""
        return base64.b64encode(data).decode("utf-8")

    def base64_decode(self, data: str) -> bytes:
        """Decode from base64"""
        return base64.b64decode(data)

    # ===== XOR CIPHER =====

    def xor_cipher(self, data: bytes, key: bytes) -> bytes:
        """XOR cipher - encryption and decryption are the same"""
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

    # ===== AES =====

    def aes_encrypt(self, data: bytes, password: str) -> Dict:
        """AES-256 encryption"""
        try:
            # Derive key from password
            key = hashlib.sha256(password.encode()).digest()

            # Generate random IV
            cipher = AES.new(key, AES.MODE_CBC)
            iv = cipher.iv

            # Encrypt
            ciphertext = cipher.encrypt(pad(data, AES.block_size))

            return {
                "success": True,
                "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
                "iv": base64.b64encode(iv).decode("utf-8"),
                "algorithm": "AES-256-CBC",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def aes_decrypt(self, ciphertext_b64: str, iv_b64: str, password: str) -> Dict:
        """AES-256 decryption"""
        try:
            # Derive key
            key = hashlib.sha256(password.encode()).digest()

            # Decode
            ciphertext = base64.b64decode(ciphertext_b64)
            iv = base64.b64decode(iv_b64)

            # Decrypt
            cipher = AES.new(key, AES.MODE_CBC, iv)
            plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)

            return {"success": True, "plaintext": plaintext}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== RSA =====

    def rsa_generate_keypair(self, key_size: int = 2048) -> Dict:
        """Generate RSA keypair"""
        try:
            key = RSA.generate(key_size)
            private_key = key.export_key()
            public_key = key.publickey().export_key()

            return {
                "success": True,
                "private_key": private_key.decode("utf-8"),
                "public_key": public_key.decode("utf-8"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def rsa_encrypt(self, data: bytes, public_key_pem: str) -> Dict:
        """RSA encryption"""
        try:
            public_key = RSA.import_key(public_key_pem)
            cipher = PKCS1_OAEP.new(public_key)
            ciphertext = cipher.encrypt(data)

            return {
                "success": True,
                "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def rsa_decrypt(self, ciphertext_b64: str, private_key_pem: str) -> Dict:
        """RSA decryption"""
        try:
            private_key = RSA.import_key(private_key_pem)
            cipher = PKCS1_OAEP.new(private_key)
            ciphertext = base64.b64decode(ciphertext_b64)
            plaintext = cipher.decrypt(ciphertext)

            return {"success": True, "plaintext": plaintext}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== FILE OPERATIONS =====

    def encrypt_file(self, input_path: str, output_path: str, password: str) -> Dict:
        """Encrypt a file with AES"""
        try:
            with open(input_path, "rb") as f:
                data = f.read()

            result = self.aes_encrypt(data, password)
            if not result["success"]:
                return result

            # Save encrypted file
            with open(output_path, "wb") as f:
                f.write(f"AES-256-CBC\n".encode())
                f.write(f"{result['iv']}\n".encode())
                f.write(base64.b64decode(result["ciphertext"]))

            return {
                "success": True,
                "input": input_path,
                "output": output_path,
                "algorithm": "AES-256-CBC",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def decrypt_file(self, input_path: str, output_path: str, password: str) -> Dict:
        """Decrypt a file with AES"""
        try:
            with open(input_path, "rb") as f:
                algorithm = f.readline().decode().strip()
                iv_b64 = f.readline().decode().strip()
                ciphertext = f.read()

            ciphertext_b64 = base64.b64encode(ciphertext).decode("utf-8")

            result = self.aes_decrypt(ciphertext_b64, iv_b64, password)
            if not result["success"]:
                return result

            with open(output_path, "wb") as f:
                f.write(result["plaintext"])

            return {"success": True, "input": input_path, "output": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_crypto = None


def get_crypto() -> CryptoCapability:
    """Get crypto singleton"""
    global _crypto
    if _crypto is None:
        _crypto = CryptoCapability()
    return _crypto
