#!/usr/bin/env python

from setuptools import setup, find_packages

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='reversible',
    version='0.1.0',
    description=(
        'reversible lets you treat multiple reversible actions as a single '
        'transaction. If any of them fail, those that have been executed '
        'will be reverted.'
    ),
    long_description=long_description,
    author='Abhinav Gupta',
    author_email='mail@abhinavg.net',
    url='https://github.com/abhinav/reversible',
    packages=find_packages(exclude=('tests*',)),
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
