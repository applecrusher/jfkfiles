import os
import requests
from bs4 import BeautifulSoup
import time
from pathlib import Path

# URL of the webpage containing the PDF links
url = 'https://www.archives.gov/research/jfk/release-2025'



# Send a GET request to the webpage
response = requests.get(url)
response.raise_for_status()  # Ensure the request was successful

# Parse the webpage content
soup = BeautifulSoup(response.text, 'html.parser')

# Find all links ending with '.pdf' in the main table
pdf_links = soup.select('table a[href$=".pdf"]')

# Base URL for constructing absolute links
base_url = 'https://www.archives.gov'

link_file = (Path.cwd().parent / 'corpus' / 'all-pdf-links.txt').resolve()

f = open(link_file , "w")
#store linkns to file
for link in pdf_links:
    pdf_url = base_url + link['href']
    f.write(pdf_url)
    f.write("\n")












