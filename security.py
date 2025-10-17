from argon2 import PasswordHasher, exceptions

# initialize Argon2 hasher (modern and secure)
ph = PasswordHasher()

def hash_password(plain: str) -> str:
    # return a secure Argon2id hash of the plaintext password
    return ph.hash(plain)

def verify_password(hash_str: str, candidate: str) -> bool:
    # verify that the candidate matches the stored hash
    try:
        return ph.verify(hash_str, candidate)
    except exceptions.VerifyMismatchError:
        return False