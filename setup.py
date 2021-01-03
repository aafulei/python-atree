#!/usr/bin/env python3

import setuptools

with open("README.md") as file:
    long_description = file.read()

setuptools.setup(
    author="Aaron Fu Lei",
    author_email="aaron.fu@alumni.ust.hk",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: System :: Filesystems",
        "Topic :: Terminals"
    ],
    description="An augmented version of the `tree` command",
    entry_points = { "console_scripts": ["atree=atree:main"] },
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    name="atree",
    packages=setuptools.find_packages(),
    py_modules=["atree"],
    python_requires=">=3.6",
    url="https://github.com/aafulei/atree",
    version="1.0.0a1",
)
