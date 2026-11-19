"""Sync the offline copy of panyicheng40/originhgss-html.

This machine has no git, and the system-wide HTTP(S)_PROXY points at a
SOCKS5 listener (127.0.0.1:10808), which neither PowerShell 5.1 nor curl
(Schannel) can use here.  So this script speaks SOCKS5 directly and does a
plain HTTPS GET over the tunnel.

Usage (bundled Python, no third-party packages):
    python tools/update.py            # download + verify against tools/manifest.json
    python tools/update.py --write    # also rewrite manifest.json with current hashes

Exit code 0: everything matches (or manifest was refreshed).
Exit code 1: at least one file differs from the recorded manifest.
"""

import hashlib
import json
import os
import socket
import ssl
import sys

PROXY = ("127.0.0.1", 10808)
HOST = "raw.githubusercontent.com"
REPO_PATH = "/panyicheng40/originhgss-html/main/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "tools", "manifest.json")


def socks_connect(host, port):
    sock = socket.create_connection(PROXY, timeout=30)
    sock.sendall(b"\x05\x01\x00")
    if sock.recv(2) != b"\x05\x00":
        sock.close()
        raise RuntimeError("SOCKS5 greeting rejected by %s:%d" % PROXY)
    name = host.encode()
    sock.sendall(b"\x05\x01\x00\x03" + bytes([len(name)]) + name + port.to_bytes(2, "big"))
    head = sock.recv(4)
    if len(head) < 4 or head[1] != 0:
        raise RuntimeError("SOCKS5 CONNECT failed: %r" % head)
    atyp = head[3]
    if atyp == 1:
        sock.recv(4)
    elif atyp == 3:
        sock.recv(sock.recv(1)[0])
    elif atyp == 4:
        sock.recv(16)
    sock.recv(2)
    return sock


def https_get(path):
    raw = socks_connect(HOST, 443)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    tls = ctx.wrap_socket(raw, server_hostname=HOST)
    tls.sendall(
        (
            "GET %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: offline-sync/1.0\r\n"
            "Accept: */*\r\nConnection: close\r\n\r\n" % (path, HOST)
        ).encode()
    )
    buf = bytearray()
    while True:
        chunk = tls.recv(65536)
        if not chunk:
            break
        buf += chunk
    tls.close()

    head, _, body = bytes(buf).partition(b"\r\n\r\n")
    status = head.split(b"\r\n")[0].decode("latin-1")
    if b"Transfer-Encoding: chunked" in head:
        out, rest = bytearray(), body
        while rest:
            line, _, rest = rest.partition(b"\r\n")
            size = int(line.split(b";")[0], 16)
            if size == 0:
                break
            out += rest[:size]
            rest = rest[size + 2:]
        body = bytes(out)
    return status, body


def git_blob_sha1(payload):
    head = b"blob %d\0" % len(payload)
    return hashlib.sha1(head + payload).hexdigest()


def main():
    write_manifest = "--write" in sys.argv[1:]
    manifest = []
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)
    paths = [entry["path"] for entry in manifest]
    if not paths:
        print("manifest is empty; cannot tell which files to fetch")
        return 1

    failures = 0
    updated = []
    for path in paths:
        try:
            status, body = https_get(REPO_PATH + path)
            if "200" not in status:
                print("FAIL  %-28s %s" % (path, status))
                failures += 1
                continue
            sha = git_blob_sha1(body)
            record = {"path": path, "gitBlobSha1": sha, "bytes": len(body)}
            updated.append(record)
            before = next((x["gitBlobSha1"] for x in manifest if x["path"] == path), None)
            note = "MATCH" if sha == before else "UPDATED"
            with open(os.path.join(ROOT, path), "wb") as fh:
                fh.write(body)
            print("%-7s %-28s %8d bytes" % (note, path, len(body)))
            if sha != before:
                failures += 1
        except Exception as exc:  # noqa: BLE001 - report and continue per file
            print("ERR   %-28s %s: %s" % (path, type(exc).__name__, exc))
            failures += 1

    if write_manifest and updated:
        with open(MANIFEST, "w", encoding="utf-8") as fh:
            json.dump(updated, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("manifest refreshed: %d entries" % len(updated))
        return 0
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
