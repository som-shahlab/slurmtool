# setup.py
from setuptools import setup

setup(
    name='slurmtool',
    version='0.1',
    py_modules=['slurmtool'],
    entry_points={
        'console_scripts': [
            'slurmtool=slurmtool:main',
        ],
    },
)
