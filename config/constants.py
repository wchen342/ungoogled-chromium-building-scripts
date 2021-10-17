import os

ARCH = ('arm', 'arm64', 'x86', 'x64')
COMMAND = ('init', 'sync', 'prepare', 'build', 'clean')
OS = ('linux', 'android')

SRC_DIR = "src"
OUTPUT_BASE_DIR = "out"

GCLIENT_CONFIG = """solutions = [
  {
    "managed": False,
    "name": "src",
    "url": "https://chromium.googlesource.com/chromium/src.git",
    "custom_deps": {
      "src/third_party/WebKit/LayoutTests": None,
      "src/chrome_frame/tools/test/reference_build/chrome": None,
      "src/chrome_frame/tools/test/reference_build/chrome_win": None,
      "src/chrome/tools/test/reference_build/chrome": None,
      "src/chrome/tools/test/reference_build/chrome_linux": None,
      "src/chrome/tools/test/reference_build/chrome_mac": None,
      "src/chrome/tools/test/reference_build/chrome_win": None
    },
    "custom_vars": {
      "checkout_pgo_profiles": False
    }
  },
]
target_os = [ @@TARGET_OS@@ ]
"""
