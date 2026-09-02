import ssl
import socket

host = "ac-qhlp5xt-shard-00-00.gdfdofo.mongodb.net"

print("Python SSL:", ssl.OPENSSL_VERSION)

context = ssl.create_default_context()

# Force TLS 1.2 for testing
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.maximum_version = ssl.TLSVersion.TLSv1_2

try:
    with socket.create_connection((host, 27017), timeout=10) as sock:
        print("TCP connection: OK")

        with context.wrap_socket(sock, server_hostname=host) as ssock:
            print("TLS connection: OK")
            print("TLS version:", ssock.version())
            print("Cipher:", ssock.cipher())

except Exception as e:
    print("TLS FAILED:")
    print(repr(e))