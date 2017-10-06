# -*- coding: utf-8 -*-
#
# querying tags from local rpm files
#

import rpm

class RPMVersion(object):

    """RPMVersion holds an rpm version-release string

    this is userd for rpm version arithmetics, like comparing
    if a specific rpm version is lower or higher than another one

    """

    _arch_suffixes = [
        'noarch',
        'x86_64',
        's390x',
        'ppc64le',
        'aarch64'
    ]
    """
    :param _arch_suffixes: arch suffixes we get in addition to version on sle12
    """

    def __init__(self, ver, *args):
        if not ver:
            raise ValueError
        for x in self._arch_suffixes:
            ver = ver.replace('.' + x, '')

        if '-' in ver:
            # split rpm version string into version and release string
            (self.ver, self.rel) = ver.rsplit('-')
        else:
            self.ver = ver
            self.rel = '0'

    def __lt__(self, other):
        return rpm.labelCompare(
            ('1', self.ver, self.rel), ('1', other.ver, other.rel)) < 0

    def __gt__(self, other):
        return rpm.labelCompare(
            ('1', self.ver, self.rel), ('1', other.ver, other.rel)) > 0

    def __eq__(self, other):
        return rpm.labelCompare(
            ('1', self.ver, self.rel), ('1', other.ver, other.rel)) == 0

    def __le__(self, other):
        return rpm.labelCompare(
            ('1', self.ver, self.rel), ('1', other.ver, other.rel)) <= 0

    def __ge__(self, other):
        return rpm.labelCompare(
            ('1', self.ver, self.rel), ('1', other.ver, other.rel)) >= 0

    def __ne__(self, other):
        return rpm.labelCompare(
            ('1', self.ver, self.rel), ('1', other.ver, other.rel)) != 0

    def __str__(self):
        s = str(self.ver)
        if self.rel != '0':
            s += "-" + str(self.rel)
        return s
