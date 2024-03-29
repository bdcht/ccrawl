import pytest
import os
import tempfile

samples_dir = os.path.join(os.path.dirname(__file__), "samples")


@pytest.fixture
def c_headers():
    files = []
    for R, D, F in os.walk(samples_dir):
        for f in F:
            if f.endswith(".h"):
                filename = os.path.join(R, f)
                files.append(filename)
    return files


@pytest.fixture
def c_empty():
    return samples_dir + "/00_empty.h"


@pytest.fixture
def c_header():
    return samples_dir + "/header.h"


@pytest.fixture
def cxx_myclass():
    return """\
//// MyClass comment
class MyClass
{
  int field;
  newstruct method(wchar_t w) {
    newstruct x;
    myint z;
    z = (myint) w;
    x.X = &z;
    return x;
  };
  virtual char vmethod(int a,MyClass &b) {
    return 'c' & char((a+*(b.pubfield))&0xff);
  };
public: 
  myint *pubfield; 
  MyClass(int x) : field(x) {};
  ~MyClass() {};
  virtual int  vmethod(int);
  const int constmeth(char);
  virtual void pmethod() {};
protected:
  static const int static_field = 10; 
  static int static_method() { return static_field; };
};
"""


@pytest.fixture
def c_sources():
    files = []
    for R, D, F in os.walk(samples_dir):
        for f in F:
            if f.endswith(".c"):
                filename = os.path.join(R, f)
                files.append(filename)
    return files


@pytest.fixture
def cxx_headers():
    files = []
    for R, D, F in os.walk(samples_dir):
        for f in F:
            if f.endswith(".hpp"):
                filename = os.path.join(R, f)
                files.append(filename)
    return files


@pytest.fixture
def cxx_sources():
    files = []
    for R, D, F in os.walk(samples_dir):
        for f in F:
            if f.endswith(".cpp"):
                filename = os.path.join(R, f)
                files.append(filename)
    return files


@pytest.fixture
def db_doc1():
    doc = {"id": "xxx", "cls": "cTypedef", "val": "int"}
    return doc


@pytest.fixture
def db_doc2():
    docs = [
        {
            "id": "struct X",
            "cls": "cStruct",
            "val": [["char", "a", "comment a"], ["yyyy", "b", "comment b"]],
        },
        {"id": "yyyy", "cls": "cTypedef", "val": "int *"},
    ]
    return docs


@pytest.fixture(autouse=True, scope="module")
def configfile():
    fd, fname = tempfile.mkstemp(".conf", prefix="ccrawl-test-")
    S = u"""c.Terminal.debug = False
c.Terminal.quiet = True
c.Collect.strict = False
c.Collect.cxx    = True
c.Terminal.console = 'ipython'
c.Database.local = 'test.db'
c.Database.url   = 'mongodb://localhost:27017'
"""
    try:
        os.write(fd, bytes(S, "ascii"))
    except TypeError:
        os.write(fd, str(S))
    os.close(fd)
    yield fname
    os.remove(fname)


@pytest.fixture(autouse=True, scope="session")
def dbfile():
    fd, fname = tempfile.mkstemp(".db", prefix="ccrawl-test-")
    os.close(fd)
    yield fname
    os.remove(fname)
