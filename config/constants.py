import os

ARCH = ('arm', 'arm64', 'x86', 'x64')
COMMAND = ('init', 'sync', 'prepare', 'build', 'clean')
OS = ('linux', 'android')

SRC_DIR = "src"
OUTPUT_DIR = os.path.join(SRC_DIR, "out")
