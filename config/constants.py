import os

ARCH = ('arm', 'arm64', 'x86', 'x64')
COMMAND = ('init', 'sync', 'prepare', 'build', 'clean')
OS = ('linux', 'android')

SRC_DIR = "src"
OUTPUT_DIR = os.path.join(
    os.path.abspath(os.path.join(os.path.split(__file__)[0], '..')), SRC_DIR, "out")
