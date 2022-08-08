"""
PC-BASIC test.main
unit tests for main script

(c) 2022 Rob Hagemans
This file is released under the GNU GPL version 3 or later.
"""

import io
import sys
from tempfile import NamedTemporaryFile

from pcbasic import main
from pcbasic.compat import stdio
from tests.unit.utils import TestCase, run_tests


class MainTest(TestCase):
    """Unit tests for main script."""

    tag = u'main'

    def test_version(self):
        """Test version call."""
        # currently can only redirect to bytes io
        output = io.BytesIO()
        with stdio.redirect_output(output, 'stdout'):
            main('-v')
        assert output.getvalue().startswith(b'PC-BASIC')

    def test_debug_version(self):
        """Test debug version call."""
        # currently can only redirect to bytes io
        output = io.BytesIO()
        with stdio.redirect_output(output, 'stdout'):
            main('-v', '--debug')
        assert output.getvalue().startswith(b'PC-BASIC')

    def test_usage(self):
        """Test usage call."""
        output = io.BytesIO()
        with stdio.redirect_output(output, 'stdout'):
            main('-h')
        assert output.getvalue().startswith(b'SYNOPSIS')

    def test_script(self):
        """Test script run."""
        output = io.BytesIO()
        with stdio.redirect_output(output, 'stdout'):
            main('-nqe', '?1')
        assert output.getvalue() == b' 1 \r\n'

    # exercise interfaces

    def test_cli(self):
        """Exercise cli run."""
        with stdio.quiet():
            main('-bq')

    def test_text(self):
        """Exercise text-based run."""
        with stdio.quiet():
            main('-tq')

    def test_graphical(self):
        """Exercise graphical run."""
        with stdio.quiet():
            main('-q')

    def test_bad_interface(self):
        """Exercise run with bad interface."""
        with stdio.quiet():
            main('--interface=_no_such_interface_', '-q')

    # exercise sound

    def test_cli_beep(self):
        """Exercise cli run."""
        with stdio.quiet():
            main('-bqe', 'beep')

    def test_graphical_beep(self):
        """Exercise graphical run."""
        with stdio.quiet():
            main('-qe', 'beep')

    # resume

    def test_resume_output(self):
        """Test resume with open empty output file."""
        with NamedTemporaryFile('w+b', delete=False) as state_file:
            with stdio.quiet():
                main(
                    "--exec=A=1:open\"z:output.txt\" for output as 1:SYSTEM",
                    '--mount=z:%s' % self.output_path(), '-b',
                    '--state=%s' % state_file,
                )
                main(
                    '--resume', '--keys=?#1,A:close:system\\r', '-b',
                    '--state=%s' % state_file,
                )
        with open(self.output_path('OUTPUT.TXT'), 'rb') as outfile:
            output = outfile.read()
        assert output == b' 1 \r\n\x1a', repr(output)

    def test_resume_output_used(self):
        """Test resume with open used output file."""
        with NamedTemporaryFile('w+b', delete=False) as state_file:
            with stdio.quiet():
                main(
                    "--exec=A=1:open\"z:output.txt\" for output as 1:?#1,2:SYSTEM",
                    '--mount=z:%s' % self.output_path(), '-n',
                    '--state=%s' % state_file,
                )
                main(
                    '--resume', '--keys=?#1,A:close:system\\r', '-n',
                    '--state=%s' % state_file,
                )
        with open(self.output_path('OUTPUT.TXT'), 'rb') as outfile:
            output = outfile.read()
        assert output == b' 2 \r\n 1 \r\n\x1a', repr(output)

    def test_resume_input(self):
        """Test resume with open input file."""
        with NamedTemporaryFile('w+b', delete=False) as state_file:
            with stdio.quiet():
                main(
                    '-n',
                    "--exec=open\"z:test.txt\" for output as 1:?#1,1,2:close:open\"z:test.txt\" for input as 1:input#1,a:SYSTEM",
                    '--mount=z:%s' % self.output_path(),
                    '--state=%s' % state_file,
                )
                main(
                    '--resume', '--keys=input#1,B:close:open "output.txt" for output as 1:?#1, a; b:close:system\\r', '-n',
                    '--state=%s' % state_file,
                )
        with open(self.output_path('OUTPUT.TXT'), 'rb') as outfile:
            output = outfile.read()
        assert output == b' 1  2 \r\n\x1a', repr(output)

    def test_resume_music(self):
        """Test resume with music queue."""
        with NamedTemporaryFile('w+b', delete=False) as state_file:
            with stdio.quiet():
                main(
                    '--exec=play"mbcdefgab>cdefgab"','-nq',
                    '--mount=z:%s' % self.output_path(),
                    '--state=%s' % state_file,
                )
                main(
                    '--resume',
                    '--state=%s' % state_file,
                    '-nk',
                    'q=play(0)\ropen"z:output.txt" for output as 1:?#1,q:close:system\r',
                )
        with open(self.output_path('OUTPUT.TXT'), 'rb') as outfile:
            output = outfile.read()
        assert output == b' 13 \r\n\x1a', repr(output)


class ConvertTest(TestCase):
    """Unit tests for convert script."""

    tag = u'convert'

    def test_ascii_to_tokenised(self):
        """Test converter run."""
        with NamedTemporaryFile('w+b', delete=False) as outfile:
            with NamedTemporaryFile('w+b', delete=False) as infile:
                infile.write(b'10 ? 1\r\n\x1a')
                infile.seek(0)
                main('--convert=b', infile.name, outfile.name)
            outfile.seek(0)
            outstr = outfile.read()
            assert outstr == b'\xff\x76\x12\x0a\x00\x91\x20\x12\x00\x00\x00\x1a', outstr

    def test_ascii_to_protected(self):
        """Test converter run."""
        with NamedTemporaryFile('w+b', delete=False) as outfile:
            with NamedTemporaryFile('w+b', delete=False) as infile:
                infile.write(b'10 ? 1\r\n\x1a')
                infile.seek(0)
                main('--convert=p', infile.name, outfile.name)
            outfile.seek(0)
            assert outfile.read() == b'\xfe\xe9\xa9\xbf\x54\xe2\x12\xad\xf1\x89\xf9\x1a'

    def test_tokenised_to_ascii(self):
        """Test converter run."""
        with NamedTemporaryFile('w+b', delete=False) as outfile:
            with NamedTemporaryFile('w+b', delete=False) as infile:
                infile.write(b'\xff\x76\x12\x0a\x00\x91\x20\x12\x00\x00\x00\x1a')
                infile.seek(0)
                main('--convert=a', infile.name, outfile.name)
            outfile.seek(0)
            assert outfile.read() == b'10 PRINT 1\r\n\x1a'

    def test_protected_to_ascii(self):
        """Test converter run."""
        with NamedTemporaryFile('w+b', delete=False) as outfile:
            with NamedTemporaryFile('w+b', delete=False) as infile:
                infile.write(b'\xfe\xe9\xa9\xbf\x54\xe2\x12\xad\xf1\x89\xf9\x1a')
                infile.seek(0)
                main('--convert=a', infile.name, outfile.name)
            outfile.seek(0)
            assert outfile.read() == b'10 PRINT 1\r\n\x1a'

    def test_tokenised_to_protected(self):
        """Test converter run."""
        with NamedTemporaryFile('w+b', delete=False) as outfile:
            with NamedTemporaryFile('w+b', delete=False) as infile:
                infile.write(b'\xff\x76\x12\x0a\x00\x91\x20\x12\x00\x00\x00\x1a')
                infile.seek(0)
                main('--convert=p', infile.name, outfile.name)
            outfile.seek(0)
            # note that the EOF gets encrypted too
            assert outfile.read() == b'\xfe\xe9\xa9\xbf\x54\xe2\x12\xad\xf1\x89\xf9\x73\x1a'

    def test_protected_to_tokenised(self):
        """Test converter run."""
        with NamedTemporaryFile('w+b', delete=False) as outfile:
            with NamedTemporaryFile('w+b', delete=False) as infile:
                infile.write(b'\xfe\xe9\xa9\xbf\x54\xe2\x12\xad\xf1\x89\xf9\x1a')
                infile.seek(0)
                main('--convert=b', infile.name, outfile.name)
            outfile.seek(0)
            assert outfile.read() == b'\xff\x76\x12\x0a\x00\x91\x20\x12\x00\x00\x00\x1a'

    def test_default(self):
        """Test converter run."""
        with NamedTemporaryFile('w+b', delete=False) as outfile:
            with NamedTemporaryFile('w+b', delete=False) as infile:
                infile.write(b'\xfe\xe9\xa9\xbf\x54\xe2\x12\xad\xf1\x89\xf9\x1a')
                infile.seek(0)
                main('--convert', infile.name, outfile.name)
            outfile.seek(0)
            assert outfile.read() == b'10 PRINT 1\r\n\x1a'


class DebugTest(TestCase):
    """Unit tests for debugging main calls."""

    tag = u'debug_main'

    def test_debug_version(self):
        """Test debug version call."""
        # currently can only redirect to bytes io
        output = io.BytesIO()
        with stdio.redirect_output(output, 'stdout'):
            main('-v', '--debug')
        assert output.getvalue().startswith(b'PC-BASIC')

    def test_crash_direct(self):
        """Exercise graphical run and trigger bluescreen from direct mode."""
        with stdio.quiet():
            main('--debug', '-qe', '_CRASH')

    def test_crash_in_program(self):
        """Exercise graphical run and trigger bluescreen from a program line."""
        with stdio.quiet():
            main('--debug', '-k', '10 _crash\rrun\r')


if __name__ == '__main__':
    run_tests()
