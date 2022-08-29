import pytest
from click.testing import CliRunner
from ccrawl.main import *


def test_00_cmd_collect(configfile, dbfile):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "-l",
            dbfile,
            "-b",
            "None",
            "-c",
            configfile,
            "collect",
            os.path.join(os.path.dirname(__file__), "samples/xxx"),
        ],
    )
    assert result.exit_code == 0


def test_01_cmd_search(configfile, dbfile):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["-l", dbfile, "-b", "None", "-c", configfile, "search", r".*\?_\w+"]
    )
    assert result.exit_code == 0
    l = result.output.split("\n")
    assert len(l) == 5
    assert "struct xt_string_info" in result.output
    assert 'found cUnion identifer "union ?_' in result.output


def test_02_cmd_select(configfile, dbfile):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["-l", dbfile, "-b", "None", "-c", configfile, "select", "constant", "10"]
    )
    assert result.exit_code == 0
    assert result.output == "C1\n"


def test_03_cmd_select(configfile, dbfile):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli, ["-l", dbfile, "-b", "None", "-c", configfile, "select", "struct", "*:1"]
    )
    assert result.exit_code == 0
    l = result.stdout.strip().split("\n")
    assert len(l) == 2
    assert "struct ?_" in l[0]
    assert "struct ?_" in l[1]


def test_04_cmd_show(configfile, dbfile):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "-l",
            dbfile,
            "-b",
            "None",
            "-c",
            configfile,
            "show",
            "-f",
            "C",
            "struct xt_string_info",
        ],
    )
    assert result.exit_code == 0
    l = result.output.split("\n")
    assert l[0] == "struct xt_string_info {"
    assert l[3] == "  int (*pfunc)(myu8, int);"

def test_05_cmd_graph(configfile, dbfile):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "-l",
            dbfile,
            "-b",
            "None",
            "-c",
            configfile,
            "graph",
            "struct grG",
        ],
    )
    assert result.exit_code == 0
    l = result.output.split("\n")
    assert l[0] == "//graph is connected"
    assert l[1] == "//graph has a strongly connected component of size 3"
    assert l[2] == "//graph has a strongly connected component of size 4"
    assert l[3] == "digraph {"
    assert l[6] == '  v0 [label="struct grG"  shape="box"]'
