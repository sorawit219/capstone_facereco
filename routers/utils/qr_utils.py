import hashlib
import random
import math
from io import BytesIO

def rand_num():
    """Generate a random 6-digit number as a string"""
    num = "0123456789"
    six_digits = ""
    for i in range(6):
        six_digits = six_digits + num[math.floor(random.random()*10)]
    return six_digits

def process_qr_data(qr_data: str) -> str:
    """
    Process QR code data to generate a consistent hash
    
    This function ensures the hash is consistent between QR code 
    generation and reading operations.
    
    Args:
        qr_data: The QR code data to process
        
    Returns:
        str: SHA-256 hash of the processed QR code data
    """
    # Clean the input data by removing whitespace
    clean_data = qr_data.strip()
    
    # Hash the clean data using SHA-256
    sha256 = hashlib.sha256()
    sha256.update(clean_data.encode('utf-8'))
    return sha256.hexdigest()

def generate_qr_data(name: str) -> str:
    """
    Generate QR code data in a consistent format
    
    Args:
        name: The name to include in the QR code data
        
    Returns:
        str: Shuffled QR code data combining random number and name
    """
    x = rand_num()  # generate number
    qr_data = f"{x}_{name}"  # Combining random number and name
    shuffled_data = ''.join(random.sample(qr_data.strip(" "), len(qr_data)))  # Shuffle the data
    return shuffled_data 