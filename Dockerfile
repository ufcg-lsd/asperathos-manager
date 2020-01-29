FROM python:3.7
COPY . /asperathos-manager
WORKDIR /asperathos-manager
RUN pip install setuptools tox flake8
ENTRYPOINT ./run.sh
