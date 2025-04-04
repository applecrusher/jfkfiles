# 📚 Project Title

JFK Files Project: 

Goals
1) Convert PDFs into searchable text (corpus) that can link back to the original page (DONE)
2) Train and Make a Large Language Model (LLM) based on the corpus. (IN PROGRESS)

---

## 🧩 Steps Involved


### Important Information

All files are designed to be run from the current directory the file is in. For example, you must be in the download directory to run download.py. This is due to the way the the scripts are getting the file path to get the right input and output directories and files.

An example site can be found here: https://jfkdocsearch.com/

This was tested on a Macbook.

### 1. Downloading Files from the Archive 

Run the script download/download.py

### 2. Splitting PDFs into Individual Pages 

Run image_processing/PDFToImg main Java file.

### 3. OCR: Image to Text 

Stores the text image as JSON. Run the image_processing/img_to_text.py.

### 4. Combining JSON into Full Document Files 

Run text_processing/combine_docs.py

### 5. Running NLP to for use case and find word parts of speech 

Run the python script text_post_processing/clean_text.py

### 6. Get Original Links to Files

Run the script text_post_processing/get_original_urls_to_json_files.py to get the original source document links now associated with each json file. TODO: Incorporate this into Step 1 in the future. 

### 7. Combine original links with source json document 

We are recrawling the archive site to get the link for each document. Run text_post_processing/merge_links_with_json.py

### 8. Creating the MySQL Database 

Run web/mysql/import.py to create the tables and import the data. If you need to run this multiple times (AKA the table is already created), you can to drop the pages table and then drop the documents table. 

### 9. Creating the Website 

This requires LAMP. Copy and past the web/php contents into the root folder of your website. You should then see the initial page. Next you will need to unzip the pdfjs folder and then upload the original PDF files so users on mobile devices can go to the specific page we found the query.

### 10. Add the PDFs to your local file system 

Copy and extract the ZIP file in the root folder of your website, located here as well: https://jfkdocsearch.com/jfk_documents_original.zip

### 11. Building the LLM (TODO) 

Working on building an LLM based on Sebastian Raschka's book "Build A Large Language Model" but using the JFK corpus as the text to train on.

---

## 🔧 Tech Stack

- Python (3.11)
- PHP (8.3)
- MySQL (8.0.*)
- PDF.js
- OCR libraries (e.g., Tesseract, EasyOCR, PaddleOCR)
- HTML/CSS/JS
- Netbeans: Java (Version 21)

---

## 📄 License

MIT Licensing

---

## 🤝 Contributing

Please submit pull request if you would like to contribute to this project. If you would like to expand this to other document corpuses, I am willing to work on that as well and I am open to suggestions. 

---

## 📬 Contact

Primary Contact and Maintainer:

Name:  Karl Appel
Email: karl@kappeltech.com

