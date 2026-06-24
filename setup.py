#!/usr/bin/env python
from setuptools import setup

setup(
    name="tap-chargify",
    version="2.0.1",
    description="Singer.io tap for extracting Chargify data",
    author="Stitch",
    url="http://github.com/singer-io/tap-chargify",
    classifiers=["Programming Language :: Python :: 3 :: Only"],
    py_modules=["tap_chargify"],
    install_requires=[
        "singer-python==6.8.0",
        "requests==2.34.2"
    ],
    extras_require={
        'dev': [
            'pylint',
            'ipdb',
            'pytest'
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
