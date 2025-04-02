import mysql.connector
import json
import os
import glob
from pathlib import Path
import sys


# Database configuration
config = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',
    'port': 8889,
    'database': 'jfk',
    'raise_on_warnings': True
}

# Connect to MySQL
cnx = mysql.connector.connect(**config)
cursor = cnx.cursor()


#Create 'documents' table if it doesn't exist, now including original_url
cursor.execute("""
CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id VARCHAR(100) UNIQUE,
    total_pages INT,
    original_url VARCHAR(2048)
) ENGINE=InnoDB;
""")

# Create 'pages' table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS pages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT,
    page_number INT,
    text LONGTEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id),
    FULLTEXT(text)
) ENGINE=InnoDB;
""")



json_folder_path = (Path.cwd().parent.parent / 'corpus' / 'jfk_combined_documents_json_nlp_with_original_url').resolve()
print(json_folder_path)




# Iterate over each JSON file in the folder
for json_file in glob.glob(os.path.join(json_folder_path, '*.json')):
    print(json_file)
    with open(json_file, 'r', encoding='utf-8') as file:
        document = json.load(file)
    
    doc_id = document['document_id']
    total_pages = document['total_pages']
    original_url = document.get('original_url', 'URL_NOT_FOUND')

    # Insert document metadata (ignore if already exists, update original_url)
    cursor.execute("""
    INSERT INTO documents (document_id, total_pages, original_url)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE total_pages=VALUES(total_pages), original_url=VALUES(original_url)
    """, (doc_id, total_pages, original_url))

    cnx.commit()

    # Get the auto-generated id for the current document
    cursor.execute("SELECT id FROM documents WHERE document_id=%s", (doc_id,))
    document_db_id = cursor.fetchone()[0]

    # Insert each page
    for page in document['pages']:
        page_number = page['page_number']
        text = page['text']

        # Avoid inserting duplicate pages
        cursor.execute("""
        SELECT COUNT(*) FROM pages 
        WHERE document_id=%s AND page_number=%s
        """, (document_db_id, page_number))
        
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO pages (document_id, page_number, text)
            VALUES (%s, %s, %s)
            """, (document_db_id, page_number, text))

    cnx.commit()

cursor.close()
cnx.close()

print("Import complete with original URLs!")
