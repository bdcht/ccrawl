from setuptools import setup, find_packages

long_descr = """ccrawl uses clang to parse C files and collect a database of
filtered Structures/Unions, Enums, Macros and Functions prototypes."""

setup(
    name="ccrawl",
    version="1.7",
    description="C source code crawler that creates a database of C-structures, prototypes and macros",
    long_description=long_descr,
    # Metadata
    author="Axel Tillequin",
    author_email="bdcht3@gmail.com",
    license="GPLv3",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Security",
    ],
    keywords="Clang C C++ data-structures database",
    packages=find_packages(exclude=["doc", "tests*"]),
    url="https://github.com/bdcht/ccrawl",
    setup_requires=[
        "pytest-runner",
    ],
    tests_require=[
        "pytest",
    ],
    install_requires=[
        "libclang==14.0.1",
        "click",
        "traitlets",
        "pyparsing",
        "tinydb",
        "python-rapidjson",
        "requests",
        "pymongo",
    ],
    package_data={},
    data_files=[],
    entry_points={
        "console_scripts": ["ccrawl=ccrawl.main:cli"],
    },
)
