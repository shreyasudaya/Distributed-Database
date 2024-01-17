FROM python:3.8
EXPOSE 5555
WORKDIR .
ENV FLASK_APP=app.py
COPY requirements.txt requirements.txt 
RUN pip3 install -r requirements.txt
COPY . .
CMD ["python", "-u", "app.py"]
