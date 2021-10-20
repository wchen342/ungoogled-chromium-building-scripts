import logging
import multiprocessing as mp
import shutil
import subprocess as sp
import os
import re
import sys
import warnings
from dataclasses import dataclass

from config.constants import OUTPUT_BASE_DIR


@dataclass
class Config:
    """Class keeps configurations."""
    cc_wrapper: str
    debug: bool
    direct_download: bool
    gn_args: dict
    install_build_deps: bool
    num_jobs: int
    output_base_dir: str
    reset: bool
    shallow: bool
    target_os: str
    target_cpu: str

    def __init__(self, args):
        # Parse GN args from cmdline, ignore errors
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
        self.output_base_dir = OUTPUT_BASE_DIR if not args.output_dir else args.output_dir
        self.reset = args.reset
        self.shallow = args.shallow
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


def parse_gn_flags(gn_lines):
    """
    Parse lines of GN flags into dictionary
    """
    gn_args = {}

    for line in gn_lines:
        name, var = line.strip().partition("=")[::2]
        gn_args[name.strip()] = var.strip()

    return gn_args


def filter_list_file(base_dir, list_file, excludes=(), excludes_pattern=None):
    """
    Filter list files (pruning.list, domain_substitution.list, series).
    """
    output_lines = []
    excludes = [e.strip() for e in excludes]
    with open(os.path.join(base_dir, list_file), 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for l in lines:
        if l.strip() in excludes or (
                excludes_pattern is not None and re.match(excludes_pattern, l)):
            continue

        output_lines.append(l.strip() + '\n')

    new_list_file = os.path.join(base_dir, list_file + '.filtered')
    with open(new_list_file, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    return new_list_file


def git_get_default_branch(repo_folder, remote_name='origin'):
    """
    Get the default branch name.
    """
    if not git_is_valid_repo(repo_folder):
        return

    remote_info = sp.check_output(['git', 'remote', 'show', remote_name], cwd=repo_folder,
                                  encoding='utf8').strip()
    branch_name = re.search(r'HEAD branch:\s*(.*)', remote_info).group(1)

    return branch_name


def git_maybe_checkout(remote, repo_folder, branch=None, reset=False):
    """
    Check if dir is a git working directory. If it exists and is a valid git repository,
    pull and update HEAD. Otherwise do a clean clone.
    branch can be tag.
    TODO: check origin matches
    """
    remote_name = 'origin'
    valid = git_is_valid_repo(repo_folder)
    default_branch = git_get_default_branch(repo_folder, remote_name)

    if not valid:
        shutil.rmtree(repo_folder, ignore_errors=True)
        clone_cmd = ['git', 'clone', remote]
        if branch is not None:
            clone_cmd += ['-b', branch]
        clone_cmd += [repo_folder]
        sp.check_call(clone_cmd)
    else:
        sp.check_call(['git', 'pull', remote_name, default_branch], cwd=repo_folder)
        sp.check_call(['git', 'checkout', branch], cwd=repo_folder)

    if reset:
        sp.check_call(['git', 'clean', '-fxd'], cwd=repo_folder)
        sp.check_call(['git', 'reset', '--hard'], cwd=repo_folder)


def git_is_valid_repo(repo_folder):
    """
    Test whether a folder is a valid git repository.
    """
    valid = True
    if not os.path.exists(repo_folder) or not os.path.isdir(repo_folder):
        valid = False
    else:
        try:
            sp.check_call(['git', 'rev-parse', '--is-inside-work-tree'], cwd=repo_folder)
            valid = not git_is_shallow(repo_folder)
        except sp.CalledProcessError as e:
            warnings.warn("{}\n{} is not a valid git repository".format(e, repo_folder))
            valid = False
    return valid


def git_is_shallow(repo_folder):
    """
    Check whether a git folder is a shallow copy
    """
    shallow = sp.check_output(['git', 'rev-parse', '--is-shallow-repository'], cwd=repo_folder, encoding='utf8').strip()
    return shallow == 'true'


def git_pull_submodules(repo_folder):
    sp.check_call(['git', 'submodule', 'update', '--init', '--recursive'], cwd=repo_folder)
