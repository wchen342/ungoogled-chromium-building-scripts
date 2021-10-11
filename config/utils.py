import multiprocessing as mp
import os

OUTPUT_DIR = os.path.join(
    os.path.abspath(os.path.join(os.path.split(__file__)[0], '..')), "src", "out")


def build_config(args):
    # Parse GN args, ignore errors
    gn_args = {}
    if args.gn_args:
        kvs = str(args.gn_args).strip().split(';')
        for s in kvs:
            kv = s.split('=')
            if len(kv) != 2:
                continue
            gn_args[kv[0]] = kv[1]

    # Build config
    config = {
        'cc_wrapper': args.cc_wrapper,
        'debug': args.debug,
        'direct_download': args.direct_download,
        'gn_args': gn_args,
        'install_build_deps': args.install_build_deps,
        'num_jobs': mp.cpu_count(),
        'output_dir': OUTPUT_DIR if not args.output_dir else args.output_dir,
        'patches_dir': args.patches_dir,
        'reset': args.reset,
        'shallow': args.shallow,
        'skip_failed_patches': args.skip_failed_patches,
        'target_os': args.os,
        'target_cpu': args.arch,
    }

    return config
