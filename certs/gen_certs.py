"""
gen_certs.py -- Generate self-signed TLS certificates for mysql_server.py
Run from project root: python certs/gen_certs.py

Outputs: certs/server.crt and certs/server.key
"""
import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

CERTS_DIR = Path(__file__).resolve().parent   # certs/ folder

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"localhost")])
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.utcnow())
    .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
    .sign(key, hashes.SHA256())
)

with open(CERTS_DIR / "server.key", "wb") as f:
    f.write(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))

with open(CERTS_DIR / "server.crt", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print(f"Done: TLS certificates written to {CERTS_DIR}/")
print("  certs/server.crt")
print("  certs/server.key")
