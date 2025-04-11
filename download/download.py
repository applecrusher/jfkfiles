import os
import requests
from bs4 import BeautifulSoup
import time
from pathlib import Path

# URL of the webpage containing the PDF links
url = 'https://www.archives.gov/research/jfk/release-2025'

# Create a directory to save the downloaded PDFs
output_dir = Path(__file__).resolve().parent.parent / 'corpus' / 'jfk_documents'
output_dir.mkdir(parents=True, exist_ok=True)

# Send a GET request to the webpage
response = requests.get(url)
response.raise_for_status()

# Parse the webpage content
soup = BeautifulSoup(response.text, 'html.parser')

# Find all PDF links in the table
pdf_links = soup.select('table a[href$=".pdf"]')
base_url = 'https://www.archives.gov'

print(f"Found {len(pdf_links)} PDF links.")

for link in pdf_links:
    relative_href = link['href']
    pdf_url = base_url + relative_href
    pdf_path = output_dir / Path(relative_href).name

    if pdf_path.exists():
        print(f"✅ Skipping {pdf_path.name}, already downloaded.")
        continue

    try:
        print(f"⬇️  Downloading {pdf_path.name}...")
        pdf_response = requests.get(pdf_url)
        pdf_response.raise_for_status()
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_response.content)

        print(f"✅ {pdf_path.name} downloaded successfully.")
    except Exception as e:
        print(f"❌ Failed to download {pdf_url}: {e}")

    time.sleep(0.01)  # Be polite to the server

print("🎉 All PDFs have been processed.")


