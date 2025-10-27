#!/usr/bin/python3

import argparse
import os
from pathlib import Path
from lib import Logger, Settings, PACKAGE_VERSION

VERSION = 'py_fancontrol 1.0'

def main():
    parser = argparse.ArgumentParser()
    parser.description = 'Python fancontrol, spinning fans in the 21st century'
    parser.add_argument('-c', '--config-path', nargs=1, required=True, type=is_config, help='Specify configuration')
    parser.add_argument('-v', '--version', action='version', version=PACKAGE_VERSION, help="Show version information")
    args = parser.parse_args()

    log = Logger(Logger.INFO)
    settings = Settings(parser.config_path)

def is_config(config_path):
    if not os.path.isfile(config_path):
        raise argparse.ArgumentError("No suitable file specified: (" + config_path + ")")
    if not config_path.lower().endswith(('.yaml')):
        raise argparse.ArgumentError("Unknown extension specified: (" + config_path + ")")
    return config_path
    

if __name__ == "__main__":
    main()
