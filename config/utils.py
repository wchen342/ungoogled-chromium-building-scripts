import logging
import multiprocessing as mp
import os
import sys
from dataclasses import dataclass

from config.constants import OUTPUT_DIR


@dataclass
class Config:
    """Class keeps configurations."""
    cc_wrapper: str
    debug: bool
    direct_download: bool
    gn_args: dict
    install_build_deps: bool
    num_jobs: int
    output_dir: str
    patches_dir: str
    reset: bool
    shallow: bool
    skip_failed_patches: bool
    target_os: str
    target_cpu: str

    def __init__(self, args):
        # Parse GN args, ignore errors
        gn_args = {}
        if args.gn_args:
            kvs = str(args.gn_args).strip().split(';')
            for s in kvs:
                kv = s.split('=')
                if len(kv) != 2:
                    continue
                gn_args[kv[0]] = kv[1]

        self.cc_wrapper = args.cc_wrapper
        self.debug = args.debug
        self.direct_download = args.direct_download
        self.gn_args = gn_args
        self.install_build_deps = args.install_build_deps
        self.num_jobs = mp.cpu_count()
        self.output_dir = OUTPUT_DIR if not args.output_dir else args.output_dir
        self.patches_dir = args.patches_dir
        self.reset = args.reset
        self.shallow = args.shallow
        self.skip_failed_patches = args.skip_failed_patches
        self.target_os = args.os
        self.target_cpu = args.arch


def create_logger(level=logging.INFO, stream=sys.stdout, filename=None):
    FORMAT = '%(asctime)s %(message)s'
    if filename:
        logging.basicConfig(format=FORMAT, level=level,
                            filename=filename, encoding='utf-8')
    else:
        logging.basicConfig(format=FORMAT, level=level, stream=stream)
    return logging.getLogger('build_root')


def shell_expand_abs_path(path):
    """
    Expand $HOME and environment variables in path.
    """
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
