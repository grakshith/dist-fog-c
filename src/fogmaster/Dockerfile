FROM python:2.7.14-slim-jessie 
MAINTAINER Rakshith "hehaichi@gmail.com"
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8080
ENTRYPOINT ["python"]
CMD ["app.py"]
