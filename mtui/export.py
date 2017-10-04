# -*- coding: utf-8 -*-
#
# exporting mtui's log (xml) to the maintenance template
#

import os
import codecs
import xml.dom.minidom

from mtui.rpmver import RPMVersion
from mtui.systemcheck import system_info


def _read_xmldata(logger, xmldata):
    try:
        if os.path.isfile(xmldata):
            x = xml.dom.minidom.parse(xmldata)
        else:
            x = xml.dom.minidom.parseString(xmldata.encode('utf-8'))
    except Exception as error:
        logger.error('failed to parse XML data: {!s}'.format(error))
        raise AttributeError('XML')

    return x


def xml_installog_to_template(logger, xmldata, config, target):
    x = _read_xmldata(logger, xmldata)
    t = []
    for host in x.getElementsByTagName('host'):
        if host.getAttribute('hostname') == target:
            template_log = host.getElementsByTagName('log')[0]

    # add hostname to indicate from which host the log was exported
    updatehost = template_log.parentNode.getAttribute('hostname')

    t.append("log from {!s}\n".format(updatehost))

    for child in template_log.childNodes:
        if not hasattr(child, 'getAttribute'):
            continue
        cmd = child.getAttribute('name')
        if not cmd.startswith('zypper '):
            continue
        t.append(
            '# {!s}\n{!s}\n'.format(cmd, child.childNodes[0].nodeValue))
    return t


def xml_to_template(logger, template, xmldata, config):
    """ export mtui xml data to an existing maintenance template

    simple method to export package versions and
    update log from the log to the template file

    Keyword arguments:
    template  -- maintenance template path (needs to exist)
    xmldata   -- mtui xml log
    """

    with codecs.open(template, 'r', 'utf-8', errors='replace') as f:
        t = f.readlines()

    x = _read_xmldata(logger, xmldata)

    # since the maintenance template is more of a human readable file then
    # a pretty parsable log, we need to build on specific strings to know
    # where to add which information. if these strings change, we need to
    # adapt.

    # for each host/system of the mtui session, search for the correct location
    # in the template. disabled hosts are not excluded.
    # if the location was found, add the hostname.
    # if the location isn't found, it's considered that it doesn't exist.
    # in this case, a whole new host section including the systemname is added.
    for host in x.getElementsByTagName('host'):
        hostname = host.getAttribute('hostname')
        systemtype = host.getAttribute('system')

        # systemname/reference host string in the maintenance template
        # in case the hostname is already set
        line = '{!s} (reference host: {!s})\n'.format(systemtype, hostname)
        try:
            # position of the system line
            i = t.index(line)
        except ValueError:
            # system line not found
            logger.debug(
                'host section %s not found, searching system'.format(hostname))
            # systemname/reference host string in the maintenance template
            # in case the hostname is not yet set
            line = '{!s} (reference host: ?)\n'.format(systemtype)
            try:
                # trying again with a not yet set hostname
                i = t.index(line)
                t[i] = '{!s} (reference host: {!s})\n'.format(
                    systemtype, hostname)
            except ValueError:
                # system line still not found (not with already set hostname, nor
                # with not yet set hostname). create new one
                logger.debug(
                    'system section {!s} not found, creating new one'.format(
                        systemtype))
                # starting point, just above the hosts section
                line = 'Test results by product-arch:\n'

                try:
                    i = t.index(line) + 2
                except ValueError:
                    # starting point not found, try again with the deprecated one
                    # from older templates
                    try:
                        line = 'Test results by test platform:\n'
                        i = t.index(line) + 2
                    except ValueError:
                        # no hostsection found and no starting point for insertion,
                        # bail out and try the next host
                        logger.error('update results section not found')
                        break

                # insert new package version log at position i.
                # example:
                # sles11sp1-i386 (reference host: leo.suse.de)
                # --------------
                # before:
                # after:
                # scripts:
                #
                # => PASSED/FAILED
                #
                # comment: (none)
                #
                t.insert(i, '\n')
                i += 1
                t.insert(
                    i, '{!s} (reference host: {!s})\n'.format(
                        systemtype, hostname))
                i += 1
                t.insert(i, '--------------\n')
                i += 1
                t.insert(i, 'before:\n')
                i += 1
                t.insert(i, 'after:\n')
                i += 1
                t.insert(i, 'scripts:\n')
                i += 1
                t.insert(i, '\n')
                i += 1
                t.insert(i, '=> PASSED/FAILED\n')
                i += 1
                t.insert(i, '\n')
                i += 1
                t.insert(i, 'comment: (none)\n')
                i += 1
                t.insert(i, '\n')

    # add package version log and script results for each host to the template
    for host in x.getElementsByTagName('host'):
        versions = {}
        hostname = host.getAttribute('hostname')
        systemtype = host.getAttribute('system')

        # search for system position which is already existing in the template
        # or was created in the previous step.
        line = '{!s} (reference host: {!s})\n'.format(systemtype, hostname)
        try:
            i = t.index(line)
        except ValueError:
            # host section not found (this should really not happen)
            # proceed with the next one.
            logger.warning('host section {!s} not found'.format(hostname))
            continue
        for state in ['before', 'after']:
            versions[state] = {}
            try:
                i = t.index('      {!s}:\n'.format(state), i) + 1
            except ValueError:
                try:
                    i = t.index('{!s}:\n'.format(state), i) + 1
                except ValueError:
                    logger.error(
                        '{!s} packages section not found'.format(state))
                    continue

            for package in host.getElementsByTagName(state):
                for child in package.childNodes:
                    try:
                        name = child.getAttribute('name')
                        version = child.getAttribute('version')
                        versions[state].update({name: version})

                        # if package version is None, update was probably not
                        # yet run, skip
                        if 'None' in version:
                            break

                        # if the package version was already exported, overwrite it with
                        # the new version. if the package version was not yet exported,
                        # add a new line
                        if name in t[i]:
                            # if package version is 0, package isn't installed
                            if version != '0':
                                t[i] = '\t{!s}-{!s}\n'.format(name, version)
                            else:
                                t[i] = '\tpackage {!s} is not installed\n'.format(
                                    name)
                        else:
                            if version != '0':
                                t.insert(
                                    i, '\t{!s}-{!s}\n'.format(name, version))
                            else:
                                t.insert(
                                    i, '\tpackage {!s} is not installed\n'.format(name))
                        i += 1
                    except Exception:
                        pass
        try:
            # search for scripts starting point
            i = t.index('scripts:\n', i-1) + 1
        except ValueError:
            # if no scripts section is found, add a new one
            logger.debug('scripts section not found, adding one')
            t.insert(i, '      scripts:\n')
            i += 1

        template_log = host.getElementsByTagName('log')[0]

        # if the package versions were not updated or one of the testscripts
        # failed, set the result to FAILED, otherwise to PASSED
        failed = 0
        for package in list(versions['before'].keys()):
            # check if the packages have a higher version after the update
            try:
                if versions['after'][package] != '0':
                    assert(
                        RPMVersion(
                            versions['before'][package]) < RPMVersion(
                            versions['after'][package]))
            except Exception:
                failed = 1
        if failed == 1:
            logger.warning(
                'installation test result on {!s} set to FAILED as some packages were not updated. please override manually.'.format(hostname))

        for child in template_log.childNodes:
            # search for check scripts in the xml and inspect return code
            # return code values:   0 SUCCEEDED
            #                       1 FAILED
            #                       2 INTERNAL ERROR
            #                       3 NOT RUN
            try:
                # name == command, exitcode == exitcode
                name = child.getAttribute('name')
                exitcode = child.getAttribute('return')
                # move on if the script wasn't run
                if exitcode == '3':
                    continue

            except Exception:
                continue

                # check if command is a compare_* script
            if 'scripts/compare/compare_' in name:
                scriptname = os.path.basename(name.split(' ')[0])
                scriptname = scriptname.replace('compare_', '')
                scriptname = scriptname.replace('.pl', '')
                scriptname = scriptname.replace('.sh', '')

                if exitcode == '0':
                    result = 'SUCCEEDED'
                elif exitcode == '1':
                    failed = 1
                    result = 'FAILED'
                else:
                    failed = 1
                    result = 'INTERNAL ERROR'

                scriptline = '\t{0:25}: {1}\n'.format(scriptname, result)
                if scriptname in t[i]:
                    t[i] = scriptline
                else:
                    t.insert(i, scriptline)

                i += 1

        if 'PASSED/FAILED' in t[i + 1]:
            if failed == 0:
                t[i + 1] = '=> PASSED\n'
            elif failed == 1:
                t[i + 1] = '=> FAILED\n'

    try:
        # search starting point for update logs
        i = t.index('put here the output of the following commands:\n', 0) + 1
    except ValueError:
        logger.error('install log section not found in template. skipping.')
    else:
        t.append("zypper logs are exported to ./install_logs directory\n")

    t.append(
        system_info(
            config.distro,
            config.distro_ver,
            config.distro_kernel,
         config.session_user))

    return t
