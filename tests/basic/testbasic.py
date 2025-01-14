"""
PC-BASIC tests.basic
tests against original BASICs

(c) 2015--2023 Rob Hagemans
This file is released under the GNU GPL version 3 or later.
"""

from __future__ import print_function

import sys
import os
import shutil
import filecmp
import traceback
import time
import json
import logging
import platform
from copy import copy, deepcopy
from contextlib import contextmanager
try:
    # Python 3 only
    from importlib import reload
except ImportError:
    pass
# process_time not in py2; clock deprecated in py3
try:
    from time import process_time
except ImportError:
    from time import clock as process_time

try:
    import colorama
    colorama.init()
except ImportError:
    # only needed on Windows
    # without it we still work but look a bit garbled
    class colorama:
        def init(): pass


# make pcbasic package accessible
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path = [os.path.join(HERE, '..', '..')] + sys.path


# copy of pythonpath for use by testing cycle
PYTHONPATH = copy(sys.path)
# test timing file
TEST_TIMES = os.path.join(HERE, '..', '_settings', 'slowtest.json')
# number of slowest tests to show or exclude
SLOWSHOW = 20


# statuses
CRASHED = 'crashed'
PASSED = 'passed'
NEWPASSED = 'newly passed'
ACCEPTED = 'accepted'
KNOWN = 'known to fail'
OLDFAILED = 'failed'
NEWFAILED = 'newly failed'
SKIPPED = 'skipped'
NONESUCH = 'not found'

# ANSI colours for test status
STATUS_COLOURS = {
    CRASHED: '01;37;41',
    PASSED: '00;32',
    NEWPASSED: '01;32',
    ACCEPTED: '00;36',
    KNOWN: '00;33',
    OLDFAILED: '00;31',
    NEWFAILED: '01;31',
    SKIPPED: '00;30',
    NONESUCH: '00;31',
}


def is_same(file1, file2):
    try:
        return filecmp.cmp(file1, file2, shallow=False)
    except EnvironmentError:
        return False

@contextmanager
def suppress_stdio(do_suppress):
    if not do_suppress:
        yield
    else:
        with pcbasic.compat.stdio.quiet():
            yield


class TestFrame(object):

    def __init__(self, category, name, reraise, skip, loud):
        self._dirname = os.path.join(HERE, category, name)
        self._reraise = reraise
        self.skip = testname(category, name) in skip
        self._loud = loud

    @contextmanager
    def check_output(self):
        if os.path.isdir(self._dirname) and 'PCBASIC.INI' in os.listdir(self._dirname):
            self.exists = True
        else:
            self.exists = False
            yield self
            return
        if self.skip:
            yield self
            return
        self._output_dir = os.path.join(self._dirname, 'output')
        self._model_dir = os.path.join(self._dirname, 'model')
        self._accepted_dir = os.path.join(self._dirname, 'accepted')
        self._known_dir = os.path.join(self._dirname, 'known')
        self.old_fail = False
        if os.path.isdir(self._output_dir):
            self.old_fail = True
            shutil.rmtree(self._output_dir)
        os.makedirs(self._output_dir)
        for filename in os.listdir(self._dirname):
            if os.path.isfile(os.path.join(self._dirname, filename)):
                shutil.copy(
                    os.path.join(self._dirname, filename),
                    os.path.join(self._output_dir, filename)
                )
        self._top = os.getcwd()
        os.chdir(self._output_dir)
        yield self
        self.passed = True
        self.accepted = os.path.isdir(self._accepted_dir)
        self.known = os.path.isdir(self._known_dir)
        self.failfiles = []
        for path, dirs, files in os.walk(self._model_dir):
            for f in files:
                filename = os.path.join(path[len(self._model_dir)+1:], f)
                if (
                        not is_same(
                            os.path.join(self._output_dir, filename),
                            os.path.join(self._model_dir, filename)
                        )
                        and not os.path.isfile(os.path.join(self._dirname, filename))
                    ):
                    self.failfiles.append(filename)
                    self.passed = False
        if not self.passed:
            for path, dirs, files in os.walk(self._accepted_dir):
                for f in files:
                    filename = os.path.join(path[len(self._accepted_dir)+1:], f)
                    self.accepted = (
                        os.path.isdir(self._accepted_dir) and
                        is_same(
                            os.path.join(self._output_dir, filename),
                            os.path.join(self._accepted_dir, filename)
                        )
                    )
        if not self.passed and not self.accepted:
            for path, dirs, files in os.walk(self._known_dir):
                for f in files:
                    filename = os.path.join(path[len(self._known_dir)+1:], f)
                    self.known = (
                        os.path.isdir(self._known_dir) and
                        is_same(
                            os.path.join(self._output_dir, filename),
                            os.path.join(self._known_dir, filename)
                        )
                    )
        for path, dirs, files in os.walk(self._output_dir):
            for f in files:
                filename = os.path.join(path[len(self._output_dir)+1:], f)
                if (
                        not os.path.isfile(os.path.join(self._model_dir, filename))
                        and not os.path.isfile(os.path.join(self._dirname, filename))
                    ):
                    self.failfiles.append(filename)
                    self.passed = False
                    self.accepted = self.accepted and (
                        os.path.isfile(os.path.join(self._accepted_dir, filename))
                    )
                    self.known = self.known and (
                        os.path.isfile(os.path.join(self._known_dir, filename))
                    )
        os.chdir(self._top)
        if self.passed:
            try:
                shutil.rmtree(self._output_dir)
                shutil.rmtree(self._accepted_dir)
                shutil.rmtree(self._known_dir)
            except EnvironmentError:
                pass

    @contextmanager
    def check_crash(self):
        self.crash = None
        try:
            yield self
        except Exception as e:
            self.crash = e
            if self._reraise:
                raise
            if self._loud:
                traceback.print_exc()


    @contextmanager
    def guard(self):
        with self.check_output():
            with self.check_crash():
                yield self

    @property
    def status(self):
        if not self.exists:
            return NONESUCH
        if self.skip:
            return SKIPPED
        if self.crash:
            return CRASHED
        if self.passed:
            if self.accepted or self.old_fail:
                return NEWPASSED
            return PASSED
        if self.accepted:
            return ACCEPTED
        if self.known:
            return KNOWN
        if self.old_fail:
            return OLDFAILED
        return NEWFAILED


class Timer(object):

    @contextmanager
    def time(self):
        start_time = time.time()
        start_cpu = process_time()
        yield self
        self.wall_time = time.time() - start_time
        self.cpu_time = process_time() - start_cpu



def testname(cat, name):
    return '/'.join((cat, name))

def normalise(name):
    if name.endswith('/'):
        name = name[:-1]
    #_, name = name.split(os.sep, 1)
    # e.g. basic/gwbasic/TestName
    try:
        _dir, name = os.path.split(name)
        _, category = os.path.split(_dir)
    except ValueError:
        category = 'gwbasic'
    return category, name


def run_tests(tests, all, fast, loud, reraise, **dummy):
    print('Running tests with Python', platform.python_version(), 'on', platform.platform())
    if all:
        dirs = [
            _preset
            for _preset in sorted(os.listdir(HERE))
            if os.path.isdir(os.path.join(HERE, _preset))
            and _preset != '__pycache__'
        ]
        tests = [
            os.path.join(_preset, _test)
            for _preset in dirs
            for _test in sorted(os.listdir(os.path.join(HERE, _preset)))
        ]
    try:
        with open(TEST_TIMES) as timefile:
            times = dict(json.load(timefile))
    except EnvironmentError:
        times = {}
    if fast:
        # exclude slowest tests
        skip = dict(sorted(times.items(), key=lambda _p: _p[1], reverse=True)[:SLOWSHOW])
    else:
        skip = {}
    results = {}
    with Timer().time() as overall_timer:
        # preserve environment
        startdir = os.path.abspath(os.getcwd())
        save_env = deepcopy(os.environ)
        # run all tests
        for number, fullname in enumerate(tests):
            # reset testing environment
            os.chdir(startdir)
            os.environ = deepcopy(save_env)
            # normalise test name
            category, name = normalise(fullname)
            fullname = testname(category, name)
            print(
                '\033[00;37mRunning test {number}/{total} [{time:.2f}s] {category}/\033[01m{name} \033[00;37m.. '.format(
                    number=number+1, total=len(tests), time=times.get(fullname, 0),
                    category=category, name=name
                ),
                end=''
            )
            with suppress_stdio(not loud):
                with Timer().time() as timer:
                    with TestFrame(category, name, reraise, skip, loud).guard() as test_frame:
                        if test_frame.exists and not test_frame.skip:
                            # we need to include the output dir in the PYTHONPATH
                            # for it to find extension modules
                            sys.path = PYTHONPATH + [os.path.abspath('.')]
                            # run PC-BASIC
                            pcbasic.main('--interface=none')
            # update test time
            if test_frame.exists and not test_frame.skip and not test_frame.crash:
                times[fullname] = timer.wall_time
            # report status
            results[fullname] = test_frame.status
            print('\033[{colour}m{status}.\033[00;37m'.format(
                colour=STATUS_COLOURS[test_frame.status],
                status=test_frame.status,
            ))
    # update stored times
    with open(TEST_TIMES, 'w') as timefile:
        json.dump(times, timefile)
    return results, times, overall_timer

def report_results(results, times, overall_timer):
    res_stat = {
        _status: [_test for _test, _teststatus in results.items() if _teststatus == _status]
        for _status in set(results.values())
    }
    print()
    print(
        '\033[00mRan %d tests in %.2fs (wall) %.2fs (cpu):\033[00;37m' %
        (len(results), overall_timer.wall_time, overall_timer.cpu_time)
    )
    for status, tests in res_stat.items():
        if status == PASSED:
            print('    %d %s' % (len(tests), status), end='')
            print('.')
    for status, tests in res_stat.items():
        if status != PASSED:
            print('    %d %s' % (len(tests), status), end='')
            print(':\n        \033[%sm%s\033[00;37m.' % (
                STATUS_COLOURS[status], '\n        '.join(tests)
            ))

def run_basic_tests(**arg_dict):
    # import late because of coverage
    # see https://stackoverflow.com/questions/22146864/pytest-2-5-2-coverage-reports-missing-lines-which-must-have-been-processed
    global pcbasic
    import pcbasic
    results = run_tests(**arg_dict)
    report_results(*results)
    print()
