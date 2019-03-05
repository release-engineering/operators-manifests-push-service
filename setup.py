"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='omps',
    version='0.1.dev',
    description='Operators Manifests Push Service',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/release-engineering/operators-manifests-push-service',
    author='Martin Basti, Red Hat Inc.',
    author_email='mbasti@redhat.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
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
        'requests',
        'operator-courier',
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
