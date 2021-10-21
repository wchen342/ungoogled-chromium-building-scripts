import subprocess
import sys

call = subprocess.call
check_call = subprocess.check_call
check_output = subprocess.check_output
run = subprocess.run


def hook():
    global call, check_call, check_output, run
    call = _call
    check_call = _check_call
    check_output = _check_output
    run = _run


def check_input(args):
    if args[0].endswith('.py'):
        args.insert(0, sys.executable)


def _call(*args, **kwargs):
    check_input(args[0])
    return subprocess.call(*args, **kwargs)


def _check_call(*args, **kwargs):
    check_input(args[0])
    return subprocess.check_call(*args, **kwargs)


def _check_output(*args, **kwargs):
    check_input(args[0])
    return subprocess.check_output(*args, **kwargs)


def _run(*args, **kwargs):
    check_input(args[0])
    return subprocess.run(*args, **kwargs)