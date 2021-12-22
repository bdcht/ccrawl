Installation
============

ccrawl is written in Python, it supports versions >=3.8.
It depends on:

 - libclang_
 - Click_
 - traitlets_
 - pyparsing_
 - tinydb_
 - rapidjson_
 - pymongo_  (interface for MongoDB)

We recommend to install ccrawl in its own *virtualenv* with included ipython_ ::

  user@machine:~ % tar xzvf ccrawl.tgz; cd ccrawl

  user@machine:~/ccrawl % mkvirtualenv venv
  Running virtualenv with interpreter /usr/bin/python3
  New python executable in /home/user/lib/python-envs/venv/bin/python3
  Also creating executable in /home/user/lib/python-envs/venv/bin/python
  Installing setuptools, pkg_resources, pip, wheel...done.

  (venv) user@machine:~/ccrawl % pip install ipython
  [...]

  (venv) user@machine:~/ccrawl % pip install .
  [...]

  (venv) user@machine:~/ccrawl % cd /tmp

  (venv) user@machine:/tmp % cat > ccrawlrc
  c.Terminal.console = 'ipython'

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc

                               _ 
    ___ ___ _ __ __ ___      _| |
   / __/ __| '__/ _` \ \ /\ / / |
  | (_| (__| | | (_| |\ V  V /| |
   \___\___|_|  \__,_| \_/\_/ |_| v1.5.0


  In [1]: [^D]


.. _libclang: https://pypi.org/project/clang/
.. _Click: https://click.palletsprojects.com/en/7.x/
.. _traitlets: https://traitlets.readthedocs.io/en/stable/
.. _pyparsing: https://github.com/pyparsing/pyparsing
.. _tinydb: https://tinydb.readthedocs.io/en/latest/intro.html
.. _rapidjson: https://github.com/python-rapidjson/python-rapidjson
.. _pymongo: https://api.mongodb.com/python/current/
.. _ipython: https://ipython.org
