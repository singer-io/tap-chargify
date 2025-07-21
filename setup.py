#!/usr/bin/env python
from setuptools import setup

setup(
    name="tap-chargify",
    version="0.1.1",
    description="Singer.io tap for extracting Chargify data",
    author="Stitch",
    url="http://github.com/singer-io/tap-chargify",
    classifiers=["Programming Language :: Python :: 3 :: Only"],
    py_modules=["tap_chargify"],
    install_requires=[
        "singer-python==5.13.2",
        "requests==2.32.4"
    ],
    extras_require={
        'dev': [
            'pylint',
            'ipdb'
        ]
    },
    entry_points="""
    [console_scripts]
    tap-chargify=tap_chargify:main
    """,
    packages=["tap_chargify"],
    package_data = {
        "schemas": ["tap_chargify/schemas/*.json"]
    },
    include_package_data=True,
)
