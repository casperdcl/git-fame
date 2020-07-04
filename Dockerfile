FROM python:3.7-alpine
RUN apk update && apk add --no-cache git
COPY setup.py README.rst git-fame/
COPY gitfame git-fame/gitfame
RUN pip install -U setuptools_scm
RUN pip install -U ./git-fame[full]
ENTRYPOINT ["git-fame", "/repo"]
