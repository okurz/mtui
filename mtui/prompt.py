# -*- coding: utf-8 -*-
#
# mtui command line prompt
#

import os
import cmd
import readline
import subprocess
import glob

from traceback import format_exc

from mtui import messages
from mtui.target import *
from mtui.utils import *
from mtui.refhost import *
import mtui.notification as notification
from mtui import commands
from .argparse import ArgsParseFailure
from mtui.refhost import Attributes
from mtui.template import NullTestReport
from mtui.template import OBSUpdateID
from mtui.utils import requires_update

try:
    unicode
except NameError:
    unicode = str


class QuitLoop(RuntimeError):
    pass


class CmdQueue(list):

    """
    Prerun support.

    Echos prompt with the command that's being popped (and about to be
    executed
    """

    def __init__(self, iterable, prompt, term):
        self.prompt = prompt
        self.term = term
        list.__init__(self, iterable)

    def pop(self, i):
        val = list.pop(self, i)
        self.echo_prompt(val)
        return val

    def echo_prompt(self, val):
        self.term.stdout.write("{0}{1}\n".format(self.prompt, val))


class CommandAlreadyBoundError(RuntimeError):
    pass


class CommandPrompt(cmd.Cmd):
    # TODO: It's worth considering to remove the inherit of cmd.Cmd and
    # just copy some of it's needed functionality, because
    #
    # 1. cmd.Cmd is not written in unit test friendly way.
    #
    # 2. cmd.Cmd.cmdloop() has to be wrapped or "clever" hacks
    #    (CmdQueue) devised in order to implement some features and
    #    tests (KeyboardInterrupt, prerun, stepping the loop one input
    #    by one) and the whole logic appears more complicated than
    #    it needs to be.
    #
    # 3. using methods as commands is quite simple but wrong way to do
    #    that and handling classes is hacked into the function system.
    #
    # 4. L{cmd.Cmd} does not inherit L{object}, therefore we can't use
    #    property accessor decorators and super
    #
    # Note: it might be possible to choose from several existing CLI
    # frameworks. Eg. cement. Maybe there's something in twisted, which
    # would be great if it could replace the ssh layer as well.

    def __init__(self, config, log, sys, display_factory):
        self.set_prompt()
        self.sys = sys

        cmd.Cmd.__init__(self, stdout=self.sys.stdout, stdin=self.sys.stdin)
        self.interactive = True
        self.display = display_factory(self.sys.stdout)
        self.metadata = NullTestReport(config, log)
        self.targets = self.metadata.targets
        """
        alias to ease refactoring
        """

        self.homedir = os.path.expanduser('~')
        self.config = config
        self.log = log
        self.datadir = self.config.datadir

        self.testopia = None

        readline.set_completer_delims('`!@#$%^&*()=+[{]}\|;:",<>? ')

        self._read_history()

        self.commands = {}
        self._add_subcommand(commands.HostsUnlock)
        self._add_subcommand(commands.HostLock)
        self._add_subcommand(commands.Whoami)
        self._add_subcommand(commands.Config)
        self._add_subcommand(commands.ListPackages)
        self._add_subcommand(commands.ReportBug)
        self._add_subcommand(commands.Commit)
        self._add_subcommand(commands.ListBugs)
        self._add_subcommand(commands.ListHosts)
        self._add_subcommand(commands.ListLocks)
        self._add_subcommand(commands.SessionName)
        self._add_subcommand(commands.SetLocation)
        self._add_subcommand(commands.SetLogLevel)
        self._add_subcommand(commands.SetTimeout)
        self._add_subcommand(commands.ListTimeout)
        self._add_subcommand(commands.ListUpdateCommands)
        self._add_subcommand(commands.SetRepo)
        self._add_subcommand(commands.Update)
        self._add_subcommand(commands.RemoveHost)
        self._add_subcommand(commands.ListSessions)
        self._add_subcommand(commands.ListMetadata)
        self._add_subcommand(commands.Downgrade)
        self._add_subcommand(commands.AddHost)
        self._add_subcommand(commands.Install)
        self._add_subcommand(commands.Uninstall)
        self._add_subcommand(commands.Shell)
        self._add_subcommand(commands.Run)
        self._add_subcommand(commands.Prepare)
        self._add_subcommand(commands.OSCAssign)
        self._add_subcommand(commands.OSCApprove)
        self._add_subcommand(commands.OSCReject)
        self._add_subcommand(commands.TestSuiteList)
        self._add_subcommand(commands.TestSuiteRun)
        self._add_subcommand(commands.TestSuiteSubmit)
        self._add_subcommand(commands.ListLog)
        self._add_subcommand(commands.Terms)
        self._add_subcommand(commands.Quit)
        self._add_subcommand(commands.DEOF)
        self._add_subcommand(commands.QExit)
        self._add_subcommand(commands.ListVersions)
        self._add_subcommand(commands.ListHistory)
        self._add_subcommand(commands.DoSave)
        self._add_subcommand(commands.LoadTemplate)
        self._add_subcommand(commands.HostState)
        self._add_subcommand(commands.Export)


        self.stdout = self.sys.stdout
        # self.stdout is used by cmd.Cmd
        self.identchars += '-'
        # support commands with dashes in them

    def notify_user(self, msg, class_=None):
        notification.display(self.log, 'MTUI', msg, class_)

    def println(self, msg='', eol='\n'):
        return self.stdout.write(msg + eol)

    def _read_history(self):
        try:
            readline.read_history_file('%s/.mtui_history' % self.homedir)
        except IOError as e:
            self.log.debug('failed to open history file: %s' % str(e))

    def _add_subcommand(self, cmd):
        if cmd.command in self.commands:
            raise CommandAlreadyBoundError(cmd.command)

        self.commands[cmd.command] = cmd

    def set_cmdqueue(self, queue):
        q = queue[:]
        if not self.interactive:
            q.append("quit")

        self.cmdqueue = CmdQueue(q, self.prompt, self.sys)

    def cmdloop(self):
        """
        Customized cmd.Cmd.cmdloop so it handles Ctrl-C and prerun
        """
        while True:
            try:
                cmd.Cmd.cmdloop(self)
            except KeyboardInterrupt:
                # Drop to interactive mode.
                # This takes effect only if we are in prerun
                self.interactive = True
                self.cmdqueue = []
                # make the new prompt to be printed on new line
                self.println()
            except QuitLoop:
                return
            except (messages.UserMessage, subprocess.CalledProcessError) as e:
                self.log.error(e)
                self.log.debug(format_exc())
            except Exception as e:
                self.log.error(format_exc())

    def get_names(self):
        names = cmd.Cmd.get_names(self)
        names += ["do_" + x for x in self.commands.keys()]
        names += ["help_" + x for x in self.commands.keys()]
        return names

    def __getattr__(self, x):
        if x.startswith('help_'):
            y = x.replace('help_', '', 1)
            if y in self.commands:
                c = self.commands[y]

                def help():
                    c.argparser(self.sys).print_help()
                return help

        if x.startswith('do_'):
            y = x.replace('do_', '', 1)
            if y in self.commands:
                c = self.commands[y]

                def do(arg):
                    try:
                        args = c.parse_args(arg, self.sys)
                    except ArgsParseFailure:
                        return
                    c(
                        args, self.targets.select(),
                        self.config, self.sys, self.log, self
                    ).run()
                return do

        if x.startswith('complete_'):
            y = x.replace("complete_", "", 1)
            if y in self.commands:
                c = self.commands[y]

                def complete(*args, **kw):
                    try:
                        return c.complete({
                            'hosts': self.targets.select(),
                            'metadata': self.metadata,
                            'config': self.config,
                            'log': self.log},
                            *args,
                            **kw)
                    except Exception as e:
                        self.log.error(e)
                        self.log.debug(format_exc(e))
                        raise e
                return complete

        raise AttributeError(str(x))

    def emptyline(self):
        return

    def _refhosts(self):
        try:
            return RefhostsFactory(self.config, self.log)
        except Exception:
            self.log.error('failed to load reference hosts data')
            raise

    def _parse_args(self, cmdline, params_type):
        tavailable = set(self.targets.keys()) | set(['all'])
        tselected = set()
        params = None

        while True:
            arg, _, rest = cmdline.strip().partition(',')
            if arg.strip() in tavailable:
                tselected.add(arg.strip())
                cmdline = rest
            else:
                break

        if params_type == str:
            params = cmdline.strip()
        elif params_type == set:
            params = set([arg.strip()
                         for arg in cmdline.split(',') if arg.strip()])

        if 'all' in tselected or tselected == set():
            targets = self.targets.select(enabled=True)
        else:
            targets = self.targets.select(tselected, enabled=True)

        return (targets, params)

    def ensure_testopia_loaded(self, *packages):
        self.testopia = self.metadata.load_testopia(*packages)

    @requires_update
    def do_testopia_list(self, args):
        """
        List all Testopia package testcases for the current product.
        If now packages are set, testcases are displayed for the
        current update.

        testopia_list [package,package,...]
        Keyword arguments:
        package  -- packag to display testcases for
        """

        self.ensure_testopia_loaded(*filter(None, args.split(',')))

        url = self.config.bugzilla_url

        if not self.testopia.testcases:
            self.log.info('no testcases found')

        for tcid, tc in self.testopia.testcases.items():
            self.display.testopia_list(
                url,
                tcid,
                tc['summary'],
                tc['status'],
                tc['automated'])

    @requires_update
    def do_testopia_show(self, args):
        """
        Show Testopia testcase

        testopia_show <testcase>[,testcase,...,testcase]
        Keyword arguments:
        testcase -- testcase ID
        """

        if args:
            cases = []
            url = self.config.bugzilla_url

            self.ensure_testopia_loaded()

            for case in args.split(','):
                case = case.replace('_', ' ')
                try:
                    cases.append(str(int(case)))
                except ValueError:
                    cases = [
                        k for k,
                        v in self.testopia.testcases.items() if v['summary'].replace(
                            '_',
                            ' ') in case]

            for case_id in cases:
                testcase = self.testopia.get_testcase(case_id)

                if not testcase:
                    continue

                if testcase:
                    self.display.testopia_show(
                        url, case_id,
                        testcase['summary'],
                        testcase['status'],
                        testcase['automated'],
                        testcase['requirement'],
                        testcase['setup'],
                        testcase['action'],
                        testcase['breakdown'],
                        testcase['effect'],
                    )
        else:
            self.parse_error(self.do_testopia_show, args)

    def complete_testopia_show(self, text, line, begidx, endidx):
        if not line.count(','):
            return self.complete_testopia_testcaselist(
                text,
                line,
                begidx,
                endidx)

    @requires_update
    def do_testopia_create(self, args):
        """
        Create new Testopia package testcase.
        An editor is spawned to process a testcase template file.

        testopia_create <package>,<summary>
        Keyword arguments:
        package  -- package to create testcase for
        summary  -- testcase summary
        """

        if args:
            url = self.config.bugzilla_url
            testcase = {}
            fields = [
                'requirement:',
                'setup:',
                'breakdown:',
                'action:',
                'effect:']
            (package, _, summary) = args.partition(',')

            self.ensure_testopia_loaded()

            fields.insert(0, 'status: proposed')
            fields.insert(0, 'automated: no')
            fields.insert(0, 'package: %s' % package)
            fields.insert(0, 'summary: %s' % summary)

            try:
                edited = edit_text('\n'.join(fields))
            except subprocess.CalledProcessError as e:
                self.log.error("editor failed: %s" % e)
                self.log.debug(format_exc())
                return

            if edited == '\n'.join(fields):
                self.log.warning('testcase was not modified. not uploading.')
                return

            template = edited.replace('\n', '|br|')

            for field in fields:
                template = template.replace(
                    '|br|%s:' %
                    field.partition(':')[0],
                    '\n%s:' %
                    field.partition(':')[0])

            lines = template.split('\n')
            for line in lines:
                key, _, value = line.partition(':')
                if key == 'package':
                    key = 'tags'
                    value = 'packagename_{name},testcase_{name}'.format(
                        name=value.strip())

                testcase[key] = value.strip()

            try:
                case_id = self.testopia.create_testcase(testcase)
            except Exception:
                self.log.error('failed to create testcase')
            else:
                self.log.info(
                    'created testcase %s/tr_show_case.cgi?case_id=%s' %
                    (url, case_id))

        else:
            self.parse_error(self.do_testopia_create, args)

    def complete_testopia_create(self, text, line, begidx, endidx):
        if not line.count(','):
            return self.complete_packagelist(text, line, begidx, endidx)

    @requires_update
    def do_testopia_edit(self, args):
        """
        Edit already existing Testopia package testcase.
        An editor is spawned to process a testcase template file.

        testopia_edit <testcase>
        Keyword arguments:
        testcase -- testcase ID
        """

        if args:
            template = []
            url = self.config.bugzilla_url
            fields = [
                'summary',
                'automated',
                'status',
                'requirement',
                'setup',
                'breakdown',
                'action',
                'effect']

            self.ensure_testopia_loaded()

            case = args.replace('_', ' ')
            try:
                case_id = str(int(case))
            except ValueError:
                try:
                    case_id = [
                        k for k,
                        v in self.testopia.testcases.items() if v['summary'].replace(
                            '_',
                            ' ') in case][0]
                except IndexError:
                    self.log.critical(
                        'case_id for testcase %s not found' %
                        case)
                    return

            testcase = self.testopia.get_testcase(case_id)

            if not testcase:
                return

            for field in fields:
                template.append('%s: %s' % (field, testcase[field]))

            try:
                edited = edit_text('\n'.join(template))
            except subprocess.CalledProcessError as e:
                self.log.error("editor failed: %s" % e)
                self.log.debug(format_exc())
                return

            if edited == '\n'.join(template):
                self.log.warning('testcase was not modified. not uploading.')
                return

            template = edited.replace('\n', '|br|')

            for field in fields:
                template = template.replace('|br|%s' % field, '\n%s' % field)

            lines = template.split('\n')
            for line in lines:
                key, _, value = line.partition(':')
                testcase[key] = value.strip()

            try:
                self.testopia.modify_testcase(case_id, testcase)
            except Exception:
                self.log.error('failed to modify testcase %s' % case_id)
            else:
                self.log.info(
                    'testcase saved: %s/tr_show_case.cgi?case_id=%s' %
                    (url, case_id))
        else:
            self.parse_error(self.do_testopia_edit, args)

    def complete_testopia_edit(self, text, line, begidx, endidx):
        if not line.count(','):
            return self.complete_testopia_testcaselist(
                text,
                line,
                begidx,
                endidx)

    def set_prompt(self, session=None):
        self.session = session
        session = ":"+str(session) if session else ''
        self.prompt = 'mtui{0}> '.format(session)

    def load_update(self, update, autoconnect):
        tr = update.make_testreport(
            self.config,
            self.log,
            autoconnect=autoconnect)

        if self.metadata and self.metadata.id is self.session:
            self.set_prompt(None)
        self.metadata = tr
        self.targets = tr.targets

    @requires_update
    def do_checkout(self, args):
        """
        Update template files from the SVN.

        checkout
        Keyword arguments:
        none
        """

        try:
            subprocess.check_call(
                'svn up'.split(),
                cwd=self.metadata.report_wd())
        except Exception:
            self.log.error('updating template failed')
            self.log.debug(format_exc())

    def do_put(self, args):
        """
        Uploads files to all enabled hosts. Multiple files can be selected
        with special patterns according to the rules used by the Unix shell
        (i.e. *, ?, []). The complete filepath on the remote hosts is shown
        after the upload. put has also directory completion.

        put <local filename>
        Keyword arguments:
        filename -- file to upload to the target hosts
        """

        if not args:
            self.parse_error(self.do_put, args)
            return

        for filename in glob.glob(args):
            if not os.path.isfile(filename):
                continue

            remote = self.metadata.target_wd(os.path.basename(filename))

            self.targets.put(filename, remote)
            self.log.info('uploaded {0} to {1}'.format(filename, remote))

    def complete_put(self, text, line, begidx, endidx):
        return self.complete_filelist(text, line, begidx, endidx)

    def do_get(self, args):
        """
        Downloads a file from all enabled hosts. Multiple files cannot be
        selected. Files are saved in the $TEMPLATE_DIR/downloads/ subdirectory
        with the hostname as file extension. If the argument ends with a
        slash '/', it will be treated as a folder and all its contents will
        be downloaded.

        get <remote filename>
        Keyword arguments:
        filename -- file to download from the target hosts
        """

        if not args:
            self.parse_error(self.do_get, args)
            return

        self.metadata.perform_get(self.targets, args)

        self.log.info('downloaded {0}'.format(args))

    def do_edit(self, args):
        """
        Edit a local file, the testing template, the specfile or a patch.
        The evironment variable EDITOR is processed to find the prefered
        editor. If EDITOR is empty, "vi" is set as default.

        edit file,<filename>
        edit template
        Keyword arguments:
        filename -- edit filename
        template -- edit template
        """

        (command, _, filename) = args.partition(',')

        editor = os.environ.get('EDITOR', 'vi')

        # all but the file command needs template data. skip if template
        # isn't loaded
        if not self.metadata and command != 'file':
            self.log.error('no testing template loaded')
            return

        if command == 'file':
            path = filename
        elif command == 'template':
            path = self.metadata.path
        else:
            self.parse_error(self.do_edit, args)
            return

        try:
            subprocess.check_call([editor, path])
        except Exception:
            self.log.error("failed to run %s" % editor)
            self.log.debug(format_exc())

    def complete_edit(self, text, line, begidx, endidx):
        if 'file,' in line:
            return self.complete_filelist(
                text.replace(
                    'file,',
                    '',
                    1),
                line,
                begidx,
                endidx)
        else:
            return [
                i for i in [
                    'file,',
                    'template'] if i.startswith(text)]

    def _do_save_impl(self, path='log.xml'):
        if not path.startswith('/'):
            dir_ = self.metadata.report_wd()
            path = os.path.join(dir_, 'output', path)

        ensure_dir_exists(os.path.dirname(path))

        if os.path.exists(path):
            self.log.warning('file {0} exists.'.format(path))
            m = 'should i overwrite {0}? (y/N) '.format(path)
            if not prompt_user(m, ['y', 'yes'], self.interactive):
                path += '.' + timestamp()

        self.log.info('saving output to {0}'.format(path))

        with open(path, 'w') as f:
            f.write(self.metadata.generate_xmllog())

    def complete_filelist(self, text, line, begidx, endidx):
        dirname = ''
        filename = ''

        if text.startswith('~'):
            text = text.replace('~', os.path.expanduser('~'), 1)
            text += '/'

        if '/' in text:
            dirname = '/'.join(text.split('/')[:-1])
            dirname += '/'

        if not dirname:
            dirname = './'

        filename = text.split('/')[-1]

        return [
            dirname +
            i for i in os.listdir(dirname) if i.startswith(filename)]

    def complete_hostlist(self, text, line, begidx, endidx, appendix=[]):
        return [
            i for i in list(
                self.targets) +
            appendix if i.startswith(text) and i not in line]

    def complete_hostlist_with_all(
            self,
            text,
            line,
            begidx,
            endidx,
            appendix=[]):
        return [
            i for i in list(
                self.targets) +
            ['all'] +
            appendix if i.startswith(text) and i not in line]

    def complete_enabled_hostlist(
            self,
            text,
            line,
            begidx,
            endidx,
            appendix=[]):
        return [
            i for i in list(
                self.targets.select(
                    enabled=True)) +
            appendix if i.startswith(text) and i not in line]

    def complete_enabled_hostlist_with_all(
            self,
            text,
            line,
            begidx,
            endidx,
            appendix=[]):
        return [
            i for i in list(
                self.targets.select(
                    enabled=True)) +
            ['all'] +
            appendix if i.startswith(text) and i not in line]

    def complete_packagelist(self, text, line, begidx, endidx, appendix=[]):
        return [i for i in self.metadata.get_package_list() if i.startswith(
            text) and i not in line]

    def complete_testopia_testcaselist(self, text, line, begidx, endidx):
        self.ensure_testopia_loaded()

        testcases = [
            i['summary'].replace(
                ' ',
                '_') for i in self.testopia.testcases.values()]
        return [i for i in testcases if i.startswith(text) and i not in line]

    def parse_error(self, method, args):
        self.println()
        self.log.error(
            'failed to parse command: %s %s' %
            (method.__name__.replace(
                'do_',
                ''),
                args))
        self.println(
            '{}: {}'.format(
                method.__name__.replace(
                    'do_',
                    ''),
                method.__doc__))


def user_deprecation(log, msg):
    log.warning(msg)
