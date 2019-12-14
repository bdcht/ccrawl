import pytest
from click.testing import CliRunner
import tempfile
from ccrawl.main import *

def test_00_cmd_collect(configfile,dbfile):
    c = conf.Config(configfile)
    c.Terminal.quiet = True
    c.Terminal.timer = False
    c.Collect.strict = False
    c.Collect.cxx    = False
    conf.config = c
    runner = CliRunner()
    result = runner.invoke(cli, ['-l',dbfile,'-b','None',
                           'collect', os.path.join(os.path.dirname(__file__), 'samples/xxx')])
    assert result.exit_code == 0
    assert result.stdout.startswith('[100%]')
    assert 'xxx/yyy/somewhere.h' in result.stdout

def test_01_cmd_search(dbfile):
    runner = CliRunner()
    result = runner.invoke(cli, ['-l',dbfile,'-b','None',
                           'search', '\?_\w'])
    assert result.exit_code == 0
    l = result.output.split('\n')
    assert len(l)==5
    assert 'struct xt_string_info' in result.output
    assert 'found cUnion identifer "union ?_' in result.output


def test_02_cmd_select(dbfile):
    runner = CliRunner()
    result = runner.invoke(cli, ['-l',dbfile,'-b','None',
                           'select', 'constant', '10'])
    assert result.exit_code == 0
    assert result.output == 'C1\n'


def test_03_cmd_show(dbfile):
    runner = CliRunner()
    result = runner.invoke(cli, ['-l',dbfile,'-b','None',
                           'show', '-f', 'C', 'struct xt_string_info'])
    assert result.exit_code == 0
    l = result.output.split('\n')
    assert l[0] == 'struct xt_string_info {'
    assert l[3] == '  int (*pfunc)();'
