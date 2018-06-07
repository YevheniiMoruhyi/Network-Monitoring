# Use an official Python runtime as a parent image
FROM python:2.7-slim

#Install necessary libs
RUN apt-get update  && apt-get install -y python-dev gcc libsasl2-dev libldap2-dev libssl-dev libsnmp-dev

#Set the working directory in the container
WORKDIR /var/lib/code/

# Copy the current directory contents into the container at /var/lib/code
COPY . /var/lib/code/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Run app.py when the container launches
CMD ["python", "main.py"]
