# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy all your project files into the container
COPY . .

# Install your dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Tell the app to run on port 7860 (Hugging Face requirement)
ENV PORT=7860
EXPOSE 7860

# Start the app
CMD ["python", "app.py"]