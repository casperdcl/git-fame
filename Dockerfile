FROM python:3.13-alpine
RUN apk update && apk add --no-cache git
COPY dist/*.whl .
RUN pip install -U $(ls *.whl)[full] && rm *.whl
ENTRYPOINT ["git-fame", "/repo"]
