from setuptools import setup, find_packages


def readme():
    with open('README.md', 'r') as f:
        return f.read()


setup(
    name='mongo-migrator',
    version='0.0.1.10',
    description='',
    author='A O',
    packages=find_packages(),
    long_description=readme(),
    long_description_content_type='text/markdown',
    url='https://github.com/p1p1daster/mongo-migrator',
    install_requires=['motor>=3.5.0'],
    keywords='mongo migrator migrate',
    project_urls={
        'GitHub': 'https://github.com/p1p1daster/mongo-migrator'
    },
    python_requires='>=3.9',
    entry_points={
        'console_scripts': [
            'migrator=mongo_migrator.migrator:entry_point',
        ],
    },

)
