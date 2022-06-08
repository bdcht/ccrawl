import pytest
from ccrawl import conf


def test_noconf():
    assert conf.config is None


def test_Terminal():
    t = conf.Terminal(config=None)
    assert hasattr(t, "trait_names")
    params = t.trait_names()
    assert "console" in params
    assert "verbose" in params
    assert not conf.DEBUG
    t.debug = True
    assert conf.DEBUG
    t.debug = False
    assert conf.DEBUG == False


def test_Config(configfile):
    c = conf.Config(configfile)
    assert c.src is not None
    assert c.Terminal.debug is False
    assert conf.DEBUG is False
    assert c.Terminal.console == "ipython"
    assert not c.Collect.strict
    assert c.Collect.cxx
    assert c.Database.local == "test.db"
    assert c.Database.url == "mongodb://localhost:27017"
