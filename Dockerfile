FROM python:2.7

RUN pip install setuptools tox flake8

COPY . /asperathos-manager/

WORKDIR /asperathos-manager

ENTRYPOINT ./run.sh
