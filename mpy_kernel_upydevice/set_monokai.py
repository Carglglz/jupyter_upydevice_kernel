#!/usr/bin/env python3

import os
from mpy_kernel_upydevice import __path__
import shutil

jupyter_config_dir = '.jupyter'
jupyter_config_file = 'jupyter_console_config.py'


def main():

    if jupyter_config_dir not in os.listdir(os.environ['HOME']):
        os.mkdir("{}/{}".format(os.environ['HOME'], jupyter_config_dir))
    else:
        print('Found existing .jupyter config directory')

    print('Setting monokai as default jupyter console style')

    try:
        shutil.copyfile('{}/{}'.format(__path__[0], jupyter_config_file),
                        '{}/{}/{}'.format(os.environ['HOME'], jupyter_config_dir,
                                          jupyter_config_file))
        print('Monokai style setup successful!')
    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()
