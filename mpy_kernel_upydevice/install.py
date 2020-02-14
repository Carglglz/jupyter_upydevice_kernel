import json
import os
import sys
import argparse

from jupyter_client.kernelspec import KernelSpecManager
from IPython.utils.tempdir import TemporaryDirectory

# copied out from https://github.com/takluyver/bash_kernel/blob/master/bash_kernel/install.py

# sys.executable should be "python3"
kernel_json = { "argv": [sys.executable, "-m", "mpy_kernel_upydevice", "-f", "{connection_file}"],
 "display_name": "MicroPython upydevice kernel",
 "language": "python"
}


def install_my_kernel_spec(user=True, prefix=None):
    if "python2" in sys.executable:
        print("I think this needs python3")
    with TemporaryDirectory() as td:
        os.chmod(td, 0o755) # Starts off as 700, not user readable
        with open(os.path.join(td, 'kernel.json'), 'w') as f:
            json.dump(kernel_json, f, sort_keys=True)
        # TODO: Copy resources once they're specified

        print('Installing IPython kernel spec of micropython')
        k = KernelSpecManager()
        k.install_kernel_spec(td, 'Micropython-upydevice', user=user, replace=True, prefix=prefix)

        h = k.get_kernel_spec("micropython-upydevice")
        print("...into", h.resource_dir)


def _is_root():
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False # assume not an admin on non-Unix platforms

def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Install KernelSpec for MicroPython Kernel'
    )
    prefix_locations = parser.add_mutually_exclusive_group()

    prefix_locations.add_argument(
        '--user',
        help='Install KernelSpec in user homedirectory',
        action='store_true'
    )
    prefix_locations.add_argument(
        '--sys-prefix',
        help='Install KernelSpec in sys.prefix. Useful in conda / virtualenv',
        action='store_true',
        dest='sys_prefix'
    )
    prefix_locations.add_argument(
        '--prefix',
        help='Install KernelSpec in this prefix',
        default=None
    )

    args = parser.parse_args(argv)

    user = False
    prefix = None
    if args.sys_prefix:
        prefix = sys.prefix
    elif args.prefix:
        prefix = args.prefix
    elif args.user or not _is_root():
        user = True

    install_my_kernel_spec(user=user, prefix=prefix)

if __name__ == '__main__':
    main()
