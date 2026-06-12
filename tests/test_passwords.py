from app.security.passwords import hash_pswd, verify_pswd


def test_hash_verify_roundtrip():
    h = hash_pswd("correct horse battery staple")
    assert verify_pswd("correct horse battery staple", h)


def test_verify_rejects_wrong_password():
    h = hash_pswd("right")
    assert not verify_pswd("wrong", h)


def test_same_input_produces_different_hashes():
    # The salt must make every hash unique even for identical plaintexts.
    assert hash_pswd("hello") != hash_pswd("hello")


def test_handles_long_passwords():
    # argon2 has no 72-byte limit (unlike bcrypt). 200-char passphrase must work.
    long_passphrase = "x" * 200
    h = hash_pswd(long_passphrase)
    assert verify_pswd(long_passphrase, h)


def test_hash_starts_with_argon2_id_prefix():
    # argon2-cffi's PasswordHasher defaults to Argon2id (the OWASP-recommended variant).
    h = hash_pswd("anything")
    assert h.startswith("$argon2id$")
