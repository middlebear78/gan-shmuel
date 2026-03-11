FROM python:3.12.3-slim
WORKDIR /app
#Create User without premissions
RUN useradd -m appuser
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
#Change owner (recursive) User:Group
RUN chown -R appuser:appuser /app
#Swithced to the user we created
USER appuser
EXPOSE 5000
CMD ["python", "app.py"]