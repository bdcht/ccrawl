from setuptools import setup, find_packages

long_descr = '''Crawl uses clang to parse C files and collect a database of
filtered Structures/Unions, Enums, Macros and Functions prototypes.'''

setup(
    name = 'crawl',
    version = '0.9.2',
    description = 'C source code crawler that creates a database of C-structures and constants',
    long_description = long_descr,
    # Metadata
    author = 'Axel Tillequin',
    author_email = 'bdcht3@gmail.com',
    license = 'GPLv2',
    classifiers=[
      'Development Status :: 3 - Alpha',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
      'Programming Language :: Python :: 2.7',
      'Programming Language :: Python :: 3',
      'Topic :: Scientific/Engineering :: Information Analysis',
      'Topic :: Security',
    ],
    keywords='Clang C-structure database',
    packages=find_packages(exclude=['doc','tests*']),
    url = 'https://github.com/bdcht/crawl',
    setup_requires=['pytest-runner',],
    tests_require=['pytest',],
    install_requires = ['clang<=6.0.0.2',
                        'click',
                        'traitlets',
                        'pyparsing',
                        'tinydb',
                        'ujson',
                        'requests'],
    package_data = {
    },
    data_files = [],
    entry_points={
       'console_scripts': ['crawl=crawl.main:cli'],
    },
)
