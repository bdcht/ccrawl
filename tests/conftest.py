import pytest
import os

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
def c_sources():
    files=[]
    for R,D,F in os.walk(samples_dir):
        for f in F:
            if f.endswith('.c'):
                filename = os.path.join(R,f)
                files.append(filename)
    return files

