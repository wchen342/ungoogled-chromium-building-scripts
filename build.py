#!/usr/bin/env python3

import argparse
import logging
import os
import re
import shutil
import subprocess as sp

import distro

from config.versions import chromium_version

# User-defined Variables
ARCH = ('arm' 'arm64' 'x86' 'x64')
COMMAND = ('build', 'prepare', 'sync', 'clean')
OS = ('linux', 'android')
OUTPUT_DIR = os.path.join(os.getcwd(), "src", "out")


def clean(output_dir):
    """
    Clean output directory.
    :param output_dir: path to output dir.
    """
    sp.check_call(['rm', '-rf', output_dir])


def set_revision(shallow=False, hard_reset=False):
    """
    Update chromium source to needed revision.
    :param shallow: whether do a shallow clone. Ignored if src folder already exists.
    :param hard_reset: whether do a hard reset before update.
    """
    src_dir = 'src'
    clone_cmd = ['git', 'clone']
    if shallow:
        clone_cmd += ['--depth', '1', '--no-tags']
    print("Checking out chromium src...")

    # Check current checked out version
    # Do not catch git exception here because any error shall stop further steps
    if os.path.exists(src_dir) and os.path.isdir(src_dir):
        cwd = src_dir
        rev = sp.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd, encoding='utf8')
        tag = sp.run(['git', 'describe', '--tags', '--exact-match', rev], cwd=cwd, encoding='utf8')
        if tag.returncode != 0 or tag.stdout != chromium_version:
            msg = "Current chromium commit is at " + rev + "(\x1B[3mtag: "
            if tag.returncode == 0:
                msg += tag.stdout
            msg += "\x1B[0m)."
            logging.info(msg + ', updating to \x1B[3mtag: ' + chromium_version + '\x1B[0m.')
            if hard_reset:
                sp.check_call(['git', 'clean', '-fxd'], cwd=cwd)
                sp.check_call(['git', 'reset', '--hard'], cwd=cwd)
            sp.check_call(['git', 'pull'], cwd=cwd)
            sp.check_call(['git', 'checkout', chromium_version], cwd=cwd)
        else:
            logging.info("Current chromium commit is at " + chromium_version + ', no need to update.')
    else:
        print("Cloning chromium source..")
        shutil.rmtree('src')
        sp.check_call(clone_cmd + [
            'https://chromium.googlesource.com/chromium/src.git',
            '-b',
            chromium_version])


def list_submodules():
    """
    List submodule names in current repo
    """
    submodule_names = []
    stages = sp.check_output(['git', 'ls-files', '--stage'], encoding='utf8')
    submodules_list = re.findall(r"^160000", stages, flags=re.MULTILINE)
    logging.debug("Found submodules: " + '\n'.join(submodules_list))
    for submodule in submodules_list:
        # this assumes no spaces in submodule paths
        submodule_names.append(re.split(r"[ ]+", submodule.strip())[-1])
    return submodule_names


def update_dependencies(hard_reset=False):
    """
    Update submodules.
    """
    # update HEAD
    sp.check_call(['git', 'pull'])

    submodules = list_submodules()

    # probe git exists in submodules
    for submodule in submodules:
        logging.info(submodule + ' is at commit ',
                     sp.check_call(['git', 'rev-parse', 'HEAD'],
                                   cwd=submodule))

    # update all submodules
    print('Update submodules..')
    if hard_reset:
        for submodule in submodules:
            sp.check_call(['git', 'reset', '--hard'],
                          cwd=submodule)
    sp.check_call(['git', 'submodule', 'update', '--init', '--recursive'])


def sync(shallow=False, hard_reset=False, install_deps=False, config=None):
    """
    Sync chromium source and run hooks.
    """
    if config is None:
        raise RuntimeError("Config not exist for build!")

    # Setup depot tools
    cwd = 'depot_tools'
    print("Cloning depot_tools...")
    if os.path.exists(cwd):
        shutil.rmtree(cwd)
    sp.check_call(['git', 'clone', 'https://chromium.googlesource.com/chromium/tools/depot_tools.git'])
    sp.check_call(['git', 'clean', '-fxd'], cwd=cwd)
    sp.check_call(['git', 'reset', '--hard'], cwd=cwd)

    # Fetch & Sync Chromium
    # Copy PATH from current process and add depot_tools to it
    _env = os.environ.copy()
    _env["PATH"] = os.path.join(os.getcwd(), 'depot_tools') + ":" + _env["PATH"]

    # Get chromium ref
    chromium_ref = sp.check_output(['git', 'rev-parse', 'HEAD'], cwd='src', encoding='utf8')

    # Run sync without hooks
    extra_args = []
    if hard_reset:
        extra_args += ['--revision', 'src@' + chromium_ref, '--force', '--with_tags', '--with_branch_heads',
                       '--upstream']
    if shallow:
        extra_args += ['--no-history', '--shallow']
    sp.check_call(['gclient', 'sync', '--reset', '--nohooks'] + extra_args, env=_env)

    # If Debian/Ubuntu and install_deps, then run the script.
    # Note: requires sudo
    if config['target_os'] == 'android':
        script = 'install-build-deps-android.sh'
    else:
        script = 'install-build-deps.sh'
    distro_name = distro.linux_distribution(full_distribution_name=False)[0].lower()
    if (distro_name == 'debian' or distro_name == 'ubuntu') and install_deps:
        sp.check_call(['sudo', os.path.join('src', 'build', script)])

    # Run hooks
    sp.check_call(['gclient', 'runhooks'], env=_env)


def default_python_version():
    python_v = re.match(r"^Python ([2|3]{1})(?:\.[0-9]{1})+",
                        sp.check_output(['python', '--version'], encoding='utf8'))
    if python_v != '2' and python_v != '3':
        raise FileNotFoundError("Cannot get python version on this system")
    return python_v


def python2_executable():
    python2_path = sp.check_output(['command -v python2'], encoding='utf8')
    return python2_path


def prepare(config=None):
    """
    Run ungoogled-chromium scripts, apply patches.
    TODO: add a patch list filter
    """
    if config is None:
        raise RuntimeError("Config not exist for build!")

    domain_substitution_cache_file = "domsubcache.tar.gz"
    if os.path.exists(domain_substitution_cache_file) and os.path.isfile(domain_substitution_cache_file):
        os.remove(domain_substitution_cache_file)

    # Patch ungoogled-chromium for android
    if config['target_os'] == 'android':
        sp.check_call(['patch', '-p1', '--ignore-whitespace', '-i',
                       os.path.join(
                           'ungoogled-chromium-android', 'patches',
                           'Other', 'ungoogled-main-repo-fix.patch'),
                       '--no-backup-if-mismatch'],
                      cwd='platforms')

    # ungoogled-chromium scripts
    # Do not check here because prune script return non-zero for non-existing files
    sp.run([
        os.path.join('ungoogled-chromium', 'utils', 'prune_binaries.py'),
        'src',
        os.path.join('ungoogled-chromium', 'pruning.list')])
    sp.check_call([
        os.path.join('ungoogled-chromium', 'utils', 'patches.py'),
        'apply', 'src',
        os.path.join('ungoogled-chromium', 'patches')])
    sp.check_call([
        os.path.join('ungoogled-chromium', 'utils', 'domain_substitution.py'),
        'apply', '-r',
        os.path.join('ungoogled-chromium', 'domain_regex.list'),
        '-f',
        os.path.join('ungoogled-chromium', 'domain_substitution.list'),
        '-c', domain_substitution_cache_file, 'src'
    ])

    if config['target_os'] == 'android':
        if os.path.exists(domain_substitution_cache_file) and os.path.isfile(domain_substitution_cache_file):
            os.remove(domain_substitution_cache_file)

        sp.check_call([
            os.path.join('ungoogled-chromium', 'utils', 'patches.py'),
            'apply', 'src',
            os.path.join('platforms', 'ungoogled-chromium-android', 'patches')])
        sp.run([
            os.path.join('ungoogled-chromium', 'utils', 'prune_binaries.py'),
            'src',
            os.path.join('platforms', 'ungoogled-chromium-android', 'pruning_2.list')])
        sp.check_call([
            os.path.join('ungoogled-chromium', 'utils', 'domain_substitution.py'),
            'apply', '-r',
            os.path.join('ungoogled-chromium', 'domain_regex.list'),
            '-f',
            os.path.join('platforms', 'ungoogled-chromium-android', 'domain_sub_2.list'),
            '-c', domain_substitution_cache_file, 'src'
        ])

    # Change shebang in all relevant files in source directory and all subdirectories
    python_version = default_python_version()
    python2_path = python2_executable()
    if python_version == '3':
        sp.check_call([
            'find', '-type', 'f', '-exec', 'sed', '-iE',
            "'1s=^#! */usr/bin/\(python\|env python\)[23]\?=#!" + python2_path + "='",
            '{}',
            '+'])


def build(config=None):
    """
    Run build for given targets.
    :param config: A dict contains necessary configs. For example:

    config = {
        'debug': False,
        'output_base_path': os.path.join('src', 'out'),
        'cc_wrapper': None,
        'target_os': 'linux',
        'target_cpu': 'x86',
        'num_jobs': 16,
    }
    """
    if config is None:
        raise RuntimeError("Config not exist for build!")

    # Create output folder if not exist
    release_channel = 'Release' if not config['debug'] else 'Debug'
    output_folder = release_channel + '_' + config['target_os'] + '_' + config['target_cpu']
    output_path = os.path.join(config['output_base_path'], output_folder)
    if os.path.exists(output_path):
        if not os.path.isdir(output_path):
            os.remove(output_path)
    else:
        os.makedirs(output_path)

    # Build GN args
    gn_args = {}

    # ungoogled-chromium
    with open(os.path.join(
            'ungoogled-chromium', 'flags.gn'
    ), 'r') as file:
        for line in file:
            name, var = line.partition("=")[::2]
            gn_args[name.strip()] = var.strip()

    # Extra flags
    gn_args.update({
        'is_debug': 'false',
        'is_official_build': 'false',
        'is_unsafe_developer_build': 'false',
        'proprietary_codecs': 'true',
        'ffmpeg_branding': '"Chrome"',
        'branding_path_component': '"ungoogled-chromium"',
        'enable_widevine': 'false',
        'use_gnome_keyring': 'false',
        'is_component_build': 'false',
        'exclude_unwind_tables': 'false',
        'enable_feed_v2': 'false',
        'enable_feed_v2_modern': 'false',
        'target_os': config['target_os'],
    })

    if config['debug']:
        gn_args['is_debug'] = 'true'
        gn_args['is_unsafe_developer_build'] = 'true'
    else:
        gn_args['symbol_level'] = '0'
        gn_args['blink_symbol_level'] = '0'

    if config['cc_wrapper'] is not None:
        gn_args['cc_wrapper'] = config['cc_wrapper']

    if config['target_cpu'] is not None:
        gn_args['target_cpu'] = config['target_cpu']

    # Assemble args
    gn_args_str = ""
    for k, v in gn_args.items():
        gn_args_str += '='.join([k, v]) + ' '

    # Run GN
    cwd = 'src'
    sp.check_call([
        os.path.join('src', 'tools', 'gn', 'bootstrap', 'bootstrap.py'),
        '--gn-gen-args=\'' + gn_args_str + '\''], cwd=cwd)
    sp.check_call([
        os.path.join('depot_tools', 'gn'),
        '--script-executable=' + python2_executable(), 'gen',
        '--args=\'' + gn_args_str + '\'',
        output_path
    ], cwd=cwd)

    # Run ninja
    if config['target_os'] == 'linux':
        targets = ['chrome', 'chrome_sandbox', 'chromedriver']
    elif config['target_os'] == 'android':
        targets = ['chrome_modern_public_bundle']
    else:
        targets = []
    sp.check_call([
        os.path.join('depot_tools', 'autoninja'),
        '-j', config['num_jobs'], '-C', output_path,
        *targets
    ], cwd=cwd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='ungoogled-chromium build script',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        allow_abbrev=False)
    parser.add_argument('command',
                        type=str,
                        help='Command to run, can be one of '
                             + ' '.join(COMMAND))
    parser.add_argument('-a', '--arch', type=str, default=ARCH[0],
                        help='<arch> can be one of ' + ' '.join(ARCH))
    parser.add_argument('-g', '--gn-args', type=str, help='GN build arguments')
    parser.add_argument('-o', '--output-dir', type=str, default=OUTPUT_DIR,
                        help='path for build output. Defaults to src/out')
    parser.add_argument('-p', '--patches-dir', type=str,
                        help='path to a directory containing patches')
    parser.add_argument('-s', '--os', type=str, default=OS[0],
                        help='OS can be one of: ' + ' '.join(OS))
    parser.add_argument('--cc_wrapper', type=str,
                        help='Set cc_wrapper for build.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--shallow', action='store_true',
                       help='Do not clone git history for chromium source')
    group.add_argument('--reset', action='store_true',
                       help='Hard reset chromium source for sync')
    parser.add_argument('--debug', action='store_true',
                        help='Build debug builds')
    parser.add_argument('--no-skip-patches', action='store_true',
                        help='Exit on failed patch attempts')
    parser.add_argument('--install-build-deps', action='store_true',
                        help="Run chromium's install-build-deps(-android).sh during sync")
    args = parser.parse_args()
    print(args)

    # Build config
    config = {
        'debug': args.debug,
        'output_base_path': os.path.join('src', 'out'),
        'cc_wrapper': None,
        'target_os': 'linux',
        'target_cpu': 'x86',
        'num_jobs': 16,
    }
