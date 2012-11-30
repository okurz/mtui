# -*- coding: utf-8 -*-
#
# mtui config file parser and default values
#

import os
import getpass
import logging
import ConfigParser

out = logging.getLogger('mtui')


class Config(object):

    """Read and store the variables from mtui config files"""

    def __init__(self):
        # read config values from /etc/mtui.cfg for system-wide configuration
        # and ~/.mtuirc for user overrides
        self.configfiles = [os.path.join('/', 'etc', 'mtui.cfg'), os.path.expanduser('~/.mtuirc')]

        self.config = ConfigParser.SafeConfigParser()
        try:
            self.config.read(self.configfiles)
        except ConfigParser.Error:
            pass

        try:
            self.datadir = os.path.expanduser(self._get_option('mtui', 'datadir'))
        except Exception:
            # datadir is in parent directory
            self.datadir = os.path.dirname(os.path.dirname(__file__))
        out.debug('config.datadir set to "%s"' % self.datadir)

        try:
            self.template_dir = os.path.expanduser(self._get_option('mtui', 'templatedir'))
        except Exception:
            self.template_dir = os.path.expanduser(os.getenv('TEMPLATEDIR', '.'))
        out.debug('config.template_dir set to "%s"' % self.template_dir)

        try:
            self.local_tempdir = os.path.expanduser(self._get_option('mtui', 'tempdir'))
        except Exception:
            self.local_tempdir = '/tmp'
        out.debug('config.local_tempdir set to "%s"' % self.local_tempdir)

        try:
            self.session_user = self._get_option('mtui', 'user')
        except Exception:
            self.session_user = getpass.getuser()
        out.debug('config.session_user set to "%s"' % self.session_user)

        try:
            self.location = self._get_option('mtui', 'location')
        except Exception:
            self.location = 'default'
        out.debug('config.location set to "%s"' % self.location)

        try:
            self.refhosts_xml = os.path.expanduser(self._get_option('mtui', 'refhosts'))
            # always use an absolute path to refhosts.xml
            if not self.refhosts_xml.startswith('/'):
                # default location of refhosts.xml is in datadir if path isn't
                # absolute
                self.refhosts_xml = os.path.join(self.datadir, self.refhosts_xml)
        except Exception:
            self.refhosts_xml = os.path.join(self.datadir, 'refhosts.xml')
        out.debug('config.refhosts_xml set to "%s"' % self.refhosts_xml)

        try:
            self.connection_timeout = int(self._get_option('connection', 'timeout'))
        except Exception:
            self.connection_timeout = 300
        out.debug('config.connection_timeout set to "%s"' % self.connection_timeout)

        try:
            self.svn_path = self._get_option('svn', 'path')
        except Exception:
            self.svn_path = 'svn+ssh://svn@qam.suse.de/testreports'
        out.debug('config.svn_path set to "%s"' % self.svn_path)

        try:
            self.patchinfo_url = self._get_option('url', 'patchinfo')
        except Exception:
            self.patchinfo_url = 'http://hilbert.nue.suse.com/abuildstat/patchinfo'
        out.debug('config.patchinfo_url set to "%s"' % self.patchinfo_url)

        try:
            self.bugzilla_url = self._get_option('url', 'bugzilla')
        except Exception:
            self.bugzilla_url = 'https://bugzilla.novell.com'
        out.debug('config.bugzilla_url set to "%s"' % self.bugzilla_url)

        try:
            self.reports_url = self._get_option('url', 'testreports')
        except Exception:
            self.reports_url = 'http://qam.suse.de/testreports'
        out.debug('config.reports_url set to "%s"' % self.reports_url)

        try:
            self.repclean_path = self._get_option('target', 'repclean')
        except Exception:
            self.repclean_path = '/suse/rd-qa/bin/rep-clean.sh'
        out.debug('config.repclean_path set to "%s"' % self.repclean_path)

        try:
            self.target_tempdir = self._get_option('target', 'tempdir')
        except Exception:
            self.target_tempdir = '/tmp'
        out.debug('config.target_tempdir set to "%s"' % self.target_tempdir)

        try:
            self.target_testsuitedir = self._get_option('target', 'testsuitedir')
        except Exception:
            self.target_testsuitedir = '/usr/share/qa/tools'
        out.debug('config.target_testsuitedir set to "%s"' % self.target_testsuitedir)

    def _get_option(self, section, option):
        try:
            return self.config.get(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            out.debug('[%s]->%s not found. falling back to default.' % (section, option))
            raise
        except ConfigParser.Error:
            out.error('failed to parse config files %s. falling back to default.' % self.configfiles)
            raise

config = Config()

