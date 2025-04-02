import os
import json
import glob
from pathlib import Path



json_input_folder = (Path.cwd().parent / 'corpus' / 'jfk_combined_documents_json_nlp').resolve()
json_output_folder = (Path.cwd().parent / 'corpus' / 'jfk_combined_documents_json_nlp_with_original_url').resolve()
pdf_folder = (Path.cwd().parent / 'corpus' / 'jfk_documents').resolve()

link_file = (Path.cwd().parent / 'corpus' / 'all-pdf-links.txt').resolve()


os.makedirs(json_output_folder, exist_ok=True)



f = open(link_file, "r")

urlMap = {}
for line in f:
    doc_num = line.split('/')[-1]
    doc_num = doc_num.split('.')[0]
    print(doc_num)
    print(line)
    urlMap[doc_num] = line.replace("\n" ,"")




json_files = glob.glob(os.path.join(json_input_folder, '*.json'))


for json_file in json_files:
    if json_file.endswith("."):
        continue
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    document_id = data.get('document_id', '')

    # Retrieve the URL if exists
    original_url = urlMap.get(document_id, 'URL_NOT_FOUND')

    # Add the original URL to the JSON data
    data['original_url'] = original_url

    # Save the updated JSON to the new folder
    output_path = os.path.join(json_output_folder, os.path.basename(json_file))
    with open(output_path, 'w', encoding='utf-8') as out_f:
        json.dump(data, out_f, ensure_ascii=False, indent=2)

print(f'All documents processed and URLs added to {json_output_folder}.')









