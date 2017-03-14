# -*- coding: utf-8 -*-

import re

from paramiko import __version__ as paramiko_version
from mtui import __version__ as mtui_version


def detect_system():
    _distro = re.compile("NAME=[\"|](.*)[\"|]")
    _v_id = re.compile("VERSION_ID=[\"|](.*)[\"|]")
    try:
        with open('/etc/os-release', mode='r', encoding='utf-8') as f:
            for line in f:
                if _distro.match(line):
                    distro = _distro.match(line).group(1)
                    continue
                if _v_id.match(line):
                    verid = _v_id.match(line).group(1)
                    continue
    except:
        verid = "None"
        distro = "Unknown"

    return distro, verid


def system_info(distro, verid, user):
    string = "## export MTUI:{}, paramiko {} on {}-{} by {}".format(
        mtui_version, paramiko_version, distro, verid, user)
    return string
