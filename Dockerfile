# Use an official Python runtime as a base image
FROM python:3.11.2-slim

# Set the working directory inside the container
WORKDIR /GMAILTODISCORD

# Copy the current directory contents into the container
COPY . /GMAILTODISCORD

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Clean up requirements file after installation
RUN rm requirements.txt

# Create last_processed.json with default content if it doesn't exist
RUN [ ! -f /GMAILTODISCORD/last_processed.json ] && echo '{"last_id": null}' > /GMAILTODISCORD/last_processed.json || true

# Command to run the application
CMD ["python", "gmail_webhook.py"]
