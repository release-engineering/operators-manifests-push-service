"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

import re
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path


def get_project_version(version_file='omps/__init__.py'):
    """
    Read the declared version of the project from the source code.

    Args:
        version_file: The file with the version string in it. The version must
            be in the format ``__version__ = '<version>'`` and the file must be
            UTF-8 encoded.

    As seen in https://pagure.io/waiverdb/raw/master/f/setup.py
    """
    with open(version_file, 'r') as f:
        version_pattern = "^__version__ = '(.+)'$"
        match = re.search(version_pattern, f.read(), re.MULTILINE)
    if match is None:
        err_msg = 'No line matching %r found in %r'
        raise ValueError(err_msg % (version_pattern, version_file))
    return match.group(1)


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='omps',
    version=get_project_version(),
    description='Operators Manifests Push Service',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/release-engineering/operators-manifests-push-service',
    author='Martin Basti, Red Hat Inc.',
    author_email='mbasti@redhat.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='kubernetes operators quay.io push service',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    python_requires='>=3.6, <4',
    install_requires=[
        'Flask==1.0.*',
        'jsonschema',
        'koji',
        'requests',
        'operator-courier>=2.1.1',
        'ruamel.yaml',
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-cov',
            'requests-mock',
            'flexmock',
        ],
    },
)
