from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection = db['user_enrollments']

# Print total number of documents
print(f"Total documents in user_enrollments: {collection.count_documents({})}")

# Print sample documents
print("\nSample documents:")
for doc in collection.find().limit(3):
    print(doc)

# Close the connection
client.close() 