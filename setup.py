import os

from setuptools import setup, find_packages

__here__ = os.path.dirname(os.path.abspath(__file__))

runtime = {'requests', 'six'}


develop = {'colorama', 'coverage>=4.4', 'flake8', 'ipython', 'jinja2', 'sphinx',
           'sphinx_rtd_theme', 'nbsphinx', 'recommonmark'}


setup(
    name='pantheon-uploader',
    version='0.0.1',
    packages=find_packages(),
    url='',
    author='randalap',
    author_email='randalap@redhat.com',
    description='Uploader for Pantheon artifacts (modules, assemblies etc.)',
    install_requires=list(runtime),
    extra_required={
        'develop': list(runtime|develop)
    }
)
