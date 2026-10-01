#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025
import glob
from os import path

from setuptools import find_packages, setup  # type: ignore
from dotclient.const import title

workspace = path.abspath(path.dirname(__file__))
README = open(path.join(workspace, 'README.md')).read()

DATA = [
    ('etc', [f for f in glob.glob(path.join('etc', '*'))]),
    ('templates', [f for f in glob.glob(path.join('templates', '*'))]),
]

dependencies = [
    'six==1.16.0',
    'ruamel.yaml==0.18.16',
    'requests<=2.32.4'
]

entry_points = {
    "console_scripts": [
        "dotclient = main.entrypoint"
    ]
}


setup(
    name=title,
    version="0.01",
    author="Alex Savatieiev",
    author_email="a.savex@gmail.com",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.12"
    ],
    keywords="dota2, opendota, dota2 api, dota2 client",
    entry_points=entry_points,
    url="",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        '': ['*.conf', '*.env', '*.list', '*.html']
    },
    zip_safe=False,
    install_requires=dependencies,
    data_files=DATA,
    license="",
    description="Simple client for opendota API",
    long_description=README
)
