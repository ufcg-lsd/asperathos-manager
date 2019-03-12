from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='broker',

    version='0.1.0',

    description='Entry point component of BIGSEA Asperathos framework',

    url='',

    author='Telles Nobrega, Roberto Nascimento Jr.',
    author_email='tellesnobrega@gmail.com, robertonscjr@gmail.com',

    license='Apache 2.0',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        'License :: OSI Approved :: Apache 2.0',

        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',

    ],
    keywords='webservice broker application management asperathos bigsea',

    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),

    install_requires=['flask'],

    entry_points={
        'console_scripts': [
            'broker=broker.cli.main:main',
        ],
        'broker.execution.plugins': [
            'spark_sahara=broker.plugins.spark_sahara.plugin:SaharaProvider',
            'fake=broker.plugins.fake.plugin:FakeProvider',
            'spark_generic=broker.plugins.spark_generic.'
            'plugin:SparkGenericProvider',
            'openstack_generic=broker.plugins.openstack_generic.'
            'plugin:OpenStackGenericProvider',
            'chronos=broker.plugins.chronos.plugin:ChronosGenericProvider',
            'spark_mesos=broker.plugins.spark_mesos.plugin:SparkMesosProvider',
            'kubejobs=broker.plugins.kubejobs.plugin:KubeJobsProvider'
        ],
    },
)
