FROM python:3
ENV PYTHONUNBUFFERED 1
WORKDIR /code
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
RUN pip install -r requirements.txt
COPY . /code/
RUN chmod +x /code/initserver.sh
RUN chmod +x /code/runserver.sh
