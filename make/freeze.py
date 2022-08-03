"""
PC-BASIC make.freeze
common definitions for cx_Freeze packaging utilities

(c) 2015--2022 Rob Hagemans
This file is released under the GNU GPL version 3 or later.
"""

import sys
import os

from distutils.util import get_platform
from setuptools import find_packages
from setuptools.command import sdist, build_py

from .common import VERSION, AUTHOR
from .common import HERE, MANIFEST_FILE
from .common import prepare, stamp_release


SHORT_VERSION = u'.'.join(VERSION.split('.')[:2])

# platform tag (build directories etc.)
PLATFORM_TAG = '{}-{}.{}'.format(
    get_platform(), sys.version_info.major, sys.version_info.minor
)

# non-python files to include
INCLUDE_FILES = (
    '*.md',
    '*.txt',
    'pcbasic/data/',
    'pcbasic/basic/data/',
)

# python files to exclude from distributions
EXCLUDE_FILES = (
    'tests/', 'make/', 'docs/',
)
EXCLUDE_PACKAGES=[
    _name+'*' for _name in os.listdir(HERE) if _name != 'pcbasic'
]

EXCLUDE_EXTERNAL_PACKAGES = [
    'pygame',
    'pip', 'wheel', 'unittest', 'pydoc_data',
    'email', 'xml',
]

SETUP_OPTIONS = dict(
    name="pcbasic",
    version=VERSION,
    author=AUTHOR,
    # contents
    # only include subpackages of pcbasic: exclude tests, docs, make etc
    # even if these are excluded in the manifest, bdist_wheel will pick them up (but sdist won't)
    packages=find_packages(exclude=EXCLUDE_PACKAGES),
    ext_modules=[],
    # include package data from MANIFEST.in (which is created by packaging script)
    include_package_data=True,
    # launchers
    entry_points=dict(
        console_scripts=['pcbasic=pcbasic:main'],
    ),
)

def build_manifest(includes, excludes):
    """Build the MANIFEST.in."""
    manifest = u''.join(
        u'include {}\n'.format(_inc) for _inc in includes if not _inc.endswith('/')
    ) + u''.join(
        u'graft {}\n'.format(_inc[:-1]) for _inc in includes if _inc.endswith('/')
    ) + u''.join(
        u'exclude {}\n'.format(_exc) for _exc in excludes if not _exc.endswith('/')
    ) + u''.join(
        u'prune {}\n'.format(_exc[:-1]) for _exc in excludes if _exc.endswith('/')
    )
    with open(MANIFEST_FILE, 'w') as manifest_file:
        manifest_file.write(manifest)



###############################################################################
# setup.py new/extended commands
# see http://seasonofcode.com/posts/how-to-add-custom-build-steps-and-commands-to-setup-py.html

def new_command(function):
    """Add a custom command without having to faff around with an overbearing API."""

    class _NewCommand(cmd.Command):
        description = function.__doc__
        user_options = []
        def run(self):
            function()
        def initialize_options(self):
            pass
        def finalize_options(self):
            pass

    return _NewCommand

def extend_command(parent, function):
    """Extend an existing command."""

    class _ExtCommand(parent):
        def run(self):
            function(self)

    return _ExtCommand

def build_py_ext(obj):
    """Run custom build_py command."""
    prepare()
    #build_manifest(INCLUDE_FILES + ('pcbasic/lib/*/*',), EXCLUDE_FILES)
    build_py.build_py.run(obj)


# setup commands
COMMANDS = {
    'build_py': extend_command(build_py.build_py, build_py_ext),
}
