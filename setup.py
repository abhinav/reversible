#!/usr/bin/env python

from setuptools import setup, find_packages

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='reversible',
    version='0.1.1',
    description=(
        'A Python library to represent, construct, chain, and execute '
        'reversible actions.'
    ),
    long_description=long_description,
    author='Abhinav Gupta',
    author_email='mail@abhinavg.net',
    url='https://github.com/abhinav/reversible',
    packages=find_packages(exclude=('tests', 'test.*')),
    license='MIT',
    tests_require=['pytest', 'mock'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
