# FROM python:3.10.6
FROM python:3.9-slim

# Set the working directory in the container.
WORKDIR /app

COPY requirements.txt .

# Install any necessary dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app.
COPY . .

# Expose the port Streamlit is running on
EXPOSE 8080

# Run the Streamlit app
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.enableCORS=false"]