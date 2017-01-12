# -*- coding: utf-8 -*-

from mtui.commands._command import Command

from mtui.commands.commit import Commit
from mtui.commands.config import Config
from mtui.commands.hoststate import HostState
from mtui.commands.hostslock import HostLock
from mtui.commands.hostsunlock import HostsUnlock
from mtui.commands.listpackages import ListPackages
from mtui.commands.reportbug import ReportBug
from mtui.commands.whoami import Whoami
from mtui.commands.simplelists import ListBugs, ListHosts, ListLocks, ListSessions
from mtui.commands.simplelists import ListTimeout, ListUpdateCommands, ListMetadata
from mtui.commands.simplelists import ListLog, ListVersions, ListHistory
from mtui.commands.simpleset import SetLocation, SessionName, SetLogLevel, SetTimeout
from mtui.commands.setrepo import SetRepo
from mtui.commands.update import Update
from mtui.commands.removehost import RemoveHost
from mtui.commands.downgrade import Downgrade
from mtui.commands.addhost import AddHost
from mtui.commands.zypper import Install, Uninstall
from mtui.commands.shell import Shell
from mtui.commands.run import Run
from mtui.commands.prepare import Prepare
from mtui.commands.oscqam import OSCAssign, OSCApprove, OSCReject
from mtui.commands.testsuite import TestSuiteList, TestSuiteRun, TestSuiteSubmit
from mtui.commands.terms import Terms
from mtui.commands.quit import DEOF, Quit, QExit
from mtui.commands.save import DoSave
from mtui.commands.loadtemplate import LoadTemplate
from mtui.commands.export import Export
from mtui.commands.sftpcmd import SFTPPut, SFTPGet
from mtui.commands.checkout import Checkout
