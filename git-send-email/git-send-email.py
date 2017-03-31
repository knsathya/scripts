#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# git send email script
#
# Copyright (C) 2017 Sathya Kuppuswamy
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# @Author  : Sathya Kupppuswamy(sathyaosid@gmail.com)
# @History :
#          :  @v0.1 - Inital script
# @TODO    : Fix CC list issue
#          : Remove email hardcode
#
#
import os
import sys
import logging
import argparse
import subprocess
import fnmatch
import re
from email.utils import parseaddr

logger = logging.getLogger(__name__)
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger.setLevel(logging.DEBUG)

GSM_SMTP = os.getenv("GSM_SMTP_SERVER", "smtp.intel.com")
GSM_CC_LIST = os.getenv("GSM_CC_LIST", "sathyaosid@gmail.com")
GSM_FROM = os.getenv("GSM_FROM", "sathyanarayanan.kuppuswamy@linux.intel.com")
GIT_CMD = "/usr/bin/git"

def glob_recursive(root, pattern):
    file_list = []
    for subdir, dirs, files in os.walk(root):
        for file in fnmatch.filter(files, pattern):
            file_list.append(os.path.join(subdir, file))

    return file_list

def get_email_list(kernel, patch_dir):
    output = ""
    cc_list = [GSM_CC_LIST]
    to_list = []
    patch_list = []

    if kernel is None:
        raise Exception("Invalid kernel input")

    get_maintainer = os.path.join(kernel, "scripts", "get_maintainer.pl")

    if not os.path.exists(get_maintainer):
        raise Exception("Invalid maintainer script")

    if os.path.isdir(patch_dir):
        patch_list = glob_recursive(patch_dir, '*.patch')
    else:
        patch_list = [patch_dir]

    for patch in patch_list:
        logger.debug("finding maintainer list of %s\n", patch)
        if not os.path.exists(patch):
            raise Exception("%s patch does not exist", patch)
        try:
            output = subprocess.check_output([get_maintainer, patch])
        except subprocess.CalledProcessError, e:
            print("get maintainer cmd {} failed".format(e))
            raise

        for line in output.splitlines():
            if "maintainer" in line or "supporter" in line:
                name, email = parseaddr(line)
                to_list.append (email)
            elif "open list" in line or "subscriber list" in line or "moderated list" in line:
                name, email = parseaddr(line)
                cc_list.append(email)

    cc_list = list(set(cc_list))
    to_list = list(set(to_list))

    logger.debug("cc list: %s", cc_list)
    logger.debug("to list: %s", to_list)

    return (to_list, cc_list)

def send_email(to_list, cc_list, patch_dir):
    send_cmd = [GIT_CMD, "send-email", "--no-thread"]

    add_option = lambda x, y: send_cmd.append( x + "=" + y)

    add_option("--smtp-server", GSM_SMTP)
    add_option("--from", GSM_FROM)

    for to in to_list:
        add_option("--to", to)

    for cc in cc_list:
        add_option("--cc", cc)

    send_cmd.append(patch_dir)

    user_input = 'n'

    user_input = raw_input("do you want to send it ? y/n\n")

    if user_input == 'y':
        print ' '.join(send_cmd)
        return subprocess.check_call(send_cmd)

    return 0

def is_valid_patch(parser, arg):
    if os.path.isdir(arg):
        file_list = glob_recursive(arg, '*.patch')
        if len(file_list) > 0:
            return arg
        else:
            parser.error('The directory {} does not have valid patches!'.format(arg))
    elif os.path.exists(arg):
        file_name, extension = os.path.splitext(arg)
        if extension == ".patch":
            return arg
        else:
            parser.error('The patch file {} extension is incorrect!'.format(arg))
    else:
        parser.error('{} invalid input!'.format(arg))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='script used to send kernel patches upstream')

    parser.add_argument('-p', '--patch-dir', action='store', dest='patch_dir',
                        type=lambda x: is_valid_patch(parser, x),
                        help='patch directory or patch file')

    args = parser.parse_args()

    print args

    kernel_dir = os.getcwd()
    if not os.path.isdir(kernel_dir) or not os.path.exists(os.path.join(kernel_dir, 'Makefile')):
        raise Exception("Current directory is not a valid kernel source")

    to_list, cc_list = get_email_list(kernel_dir, args.patch_dir)

    send_email(to_list, cc_list, args.patch_dir)

