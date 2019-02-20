Installation
============

Crawl est un outil écrit en Python, supportant les versions >=2.7 et >=3.5.
Il dépend des paquets suivants:

 - libclang <= 6.0.0.2
 - Click
 - traitlets
 - pyparsing
 - tinydb
 - ujson
 - requests (interface avec CouchDB)
 - pymongo  (interface avec MongoDB)

Il est conseillé d'utiliser crawl dans un virtualenv python avec ipython::

  user@machine:~ % tar xzvf crawl.tgz; cd crawl

  user@machine:~/crawl % mkvirtualenv sstic
  Running virtualenv with interpreter /usr/bin/python2
  New python executable in /home/user/lib/python-envs/sstic/bin/python2
  Also creating executable in /home/user/lib/python-envs/sstic/bin/python
  Installing setuptools, pkg_resources, pip, wheel...done.

  (sstic) user@machine:~/crawl % sudo apt install libclang1-6.0

  (sstic) user@machine:~/crawl % pip install ipython
  [...]

  (sstic) user@machine:~/crawl % python setup.py install
  [...]

  (sstic) user@machine:~/crawl % cd /tmp

  (sstic) user@machine:~/crawl % locate libclang-6.0.so
  /usr/lib/llvm-6.0/lib/libclang-6.0.so.1
  /usr/lib/x86_64-linux-gnu/libclang-6.0.so.1

  (sstic) user@machine:/tmp % cat > crawlrc
  c.Terminal.console = 'ipython'
  c.Collect.lib = '/usr/lib/llvm-6.0/lib/libclang-6.0.so.1'

  (sstic) user@machine:/tmp % crawl -c crawlrc

                           _
    ___ _ __ __ ___      _| |
   / __| '__/ _` \ \ /\ / / |
  | (__| | | (_| |\ V  V /| |
   \___|_|  \__,_| \_/\_/ |_| v0.9.1


  In [1]: [^D]

