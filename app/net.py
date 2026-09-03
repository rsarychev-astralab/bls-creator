import socket

_orig = socket.getaddrinfo


def force_ipv4() -> None:
    def getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        return _orig(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = getaddrinfo
