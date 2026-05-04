FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for ML libraries (XGBoost/Scikit-learn)
RUN apt-get update && apt-get install -y build-essential libgomp1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the data generator and train the model during the build phase
# This ensures the model is serialized and ready before the server starts
RUN python -m app.ml.data_generator
RUN python -m app.ml.train_model

# Create startup script to seed database before starting server
RUN echo '#!/bin/bash\nset -e\necho "Waiting for MongoDB to be ready..."\nsleep 5\necho "Seeding database..."\npython -m app.ml.seed_database\necho "Starting application..."\nexec uvicorn app.main:app --host 0.0.0.0 --port 8000' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]