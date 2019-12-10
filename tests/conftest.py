import pytest
import os
import tempfile

samples_dir = os.path.join(os.path.dirname(__file__), 'samples')

@pytest.fixture
def c_headers():
    files=[]
    for R,D,F in os.walk(samples_dir):
        for f in F:
            if f.endswith('.h'):
                filename = os.path.join(R,f)
                files.append(filename)
    return files

@pytest.fixture
def c_empty():
    return samples_dir+'/00_empty.h'

@pytest.fixture
def c_header():
    return samples_dir+'/header.h'

@pytest.fixture
def c_sources():
    files=[]
    for R,D,F in os.walk(samples_dir):
        for f in F:
            if f.endswith('.c'):
                filename = os.path.join(R,f)
                files.append(filename)
    return files

@pytest.fixture
def cxx_headers():
    files=[]
    for R,D,F in os.walk(samples_dir):
        for f in F:
            if f.endswith('.hpp'):
                filename = os.path.join(R,f)
                files.append(filename)
    return files

@pytest.fixture
def cxx_sources():
    files=[]
    for R,D,F in os.walk(samples_dir):
        for f in F:
            if f.endswith('.cpp'):
                filename = os.path.join(R,f)
                files.append(filename)
    return files

@pytest.fixture
def db_doc1():
    doc = {'id':'xxx', 'cls':'cTypedef', 'val':'int'}
    return doc

@pytest.fixture
def db_doc2():
    docs = [{'id':'struct X',
            'cls':'cStruct',
            'val':[['char', 'a', 'comment a'],
                   ['yyyy', 'b', 'comment b']]},
            {'id': 'yyyy',
             'cls': 'cTypedef',
             'val': 'int *'}]
    return docs

@pytest.fixture(scope="session")
def configfile():
    fd,fname = tempfile.mkstemp('.conf',prefix='ccrawl-test')
    os.write(fd,bytes(\
u"""c.Terminal.debug = False
c.Collect.strict = False
c.Collect.cxx    = True
c.Terminal.console = 'ipython'
c.Database.local = 'test.db'
c.Database.url   = 'mongodb://localhost:27017'
""",'ascii'))
    os.close(fd)
    return fname

