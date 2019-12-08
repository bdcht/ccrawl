Installation
============

ccrawl is written in Python, it supports versions >=2.7 and >=3.5.
It depends on:

 - libclang_ == 6.0.0.2
 - Click_
 - traitlets_
 - pyparsing_
 - tinydb_
 - ujson_
 - pymongo_  (interface for MongoDB)

We recommend to install ccrawl in its own *virtualenv* with included ipython_ ::

  user@machine:~ % tar xzvf ccrawl.tgz; cd ccrawl

  user@machine:~/ccrawl % mkvirtualenv venv
  Running virtualenv with interpreter /usr/bin/python2
  New python executable in /home/user/lib/python-envs/venv/bin/python2
  Also creating executable in /home/user/lib/python-envs/venv/bin/python
  Installing setuptools, pkg_resources, pip, wheel...done.

  (venv) user@machine:~/ccrawl % sudo apt install libclang1-6.0

  (venv) user@machine:~/ccrawl % pip install ipython
  [...]

  (venv) user@machine:~/ccrawl % python setup.py install
  [...]

  (venv) user@machine:~/ccrawl % cd /tmp

  (venv) user@machine:~/ccrawl % locate libclang-6.0.so
  /usr/lib/llvm-6.0/lib/libclang-6.0.so.1
  /usr/lib/x86_64-linux-gnu/libclang-6.0.so.1

  (venv) user@machine:/tmp % cat > ccrawlrc
  c.Terminal.console = 'ipython'
  c.Collect.lib = '/usr/lib/llvm-6.0/lib/libclang-6.0.so.1'

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc

                           _
    ___ _ __ __ ___      _| |
   / __| '__/ _` \ \ /\ / / |
  | (__| | | (_| |\ V  V /| |
   \___|_|  \__,_| \_/\_/ |_| v1.0


  In [1]: [^D]


.. _libclang: https://pypi.org/project/clang/
.. _Click: https://click.palletsprojects.com/en/7.x/
.. _traitlets: https://traitlets.readthedocs.io/en/stable/
.. _pyparsing: https://github.com/pyparsing/pyparsing
.. _tinydb: https://tinydb.readthedocs.io/en/latest/intro.html
.. _ujson: https://pypi.org/project/ujson/
.. _pymongo: https://api.mongodb.com/python/current/
