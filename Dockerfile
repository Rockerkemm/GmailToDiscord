# Use an official Python runtime as a base image
FROM python:3.11.2

# Set the working directory inside the container
WORKDIR /GMAILTODISCORD

# Copy the current directory contents into the container
COPY . /GMAILTODISCORD

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["python", "gmail_webhook.py"]
