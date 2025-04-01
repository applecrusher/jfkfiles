import os
import requests
from bs4 import BeautifulSoup
import time
from pathlib import Path



# URL of the webpage containing the PDF links
url = 'https://www.archives.gov/research/jfk/release-2025'

# Create a directory to save the downloaded PDFs
output_dir = (Path(__file__).resolve().parent.parent / 'corpus' / 'jfk_documents')
os.makedirs(output_dir, exist_ok=True)

# Send a GET request to the webpage
response = requests.get(url)
response.raise_for_status()  # Ensure the request was successful

# Parse the webpage content
soup = BeautifulSoup(response.text, 'html.parser')

# Find all links ending with '.pdf' in the main table
pdf_links = soup.select('table a[href$=".pdf"]')

# Base URL for constructing absolute links
base_url = 'https://www.archives.gov'

# Download each PDF only if it doesn't already exist
for link in pdf_links:
    pdf_url = base_url + link['href']
    pdf_name = os.path.join(output_dir, os.path.basename(link['href']))

    if os.path.exists(pdf_name):
        print(f'Skipping {pdf_name}, already downloaded.')
        continue

    print(f'Downloading {pdf_name}...')
    pdf_response = requests.get(pdf_url)
    pdf_response.raise_for_status()
    
    with open(pdf_name, 'wb') as pdf_file:
        pdf_file.write(pdf_response.content)

    print(f'{pdf_name} downloaded successfully.')
    time.sleep(0.01)

print('All PDFs have been processed.')





