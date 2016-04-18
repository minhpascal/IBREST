# From this tutorial http://containertutorials.com/docker-compose/flask-simple-app.html
FROM ubuntu:14.04.4
MAINTAINER Jason Haury "jason.haury@gmail.com"
RUN apt-get update -y
RUN apt-get install -y python-pip
 #python-dev build-essential
COPY app /app
COPY requirements.txt /
#RUN pip install -r /requirements.txt
RUN pip install flask-restful
WORKDIR /app
CMD chmod +x ./app.py
ENTRYPOINT ["python", "./app.py"]
