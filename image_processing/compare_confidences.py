import os
import json
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import platform
from pathlib import Path
import sys
from statistics import median



def get_file_contents(json_dir, file_path):
    with open(json_dir / file_path, 'r') as file:
        return json.load(file)

# Only set path manually if needed (e.g., not in PATH)
if platform.system() == 'Windows':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
elif platform.system() == 'Darwin':  # macOS
    pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'  # or /usr/local/bin
elif platform.system() == 'Linux':
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'


JSON_DIR_1 = (Path.cwd().parent / 'corpus' / 'jfk_documents_json_v1').resolve()
JSON_DIR_2 =  (Path.cwd().parent / 'corpus' / 'jfk_documents_json_v2').resolve()




json_files_1 = sorted([
    f for f in os.listdir(JSON_DIR_1)
    if f.lower().endswith('.json') and not f.lower().startswith(".")
])

json_files_2 = sorted([
    f for f in os.listdir(JSON_DIR_2)
    if f.lower().endswith('.json') and not f.lower().startswith(".")
])

file_mapping = {}

for i in range(len(json_files_1)):
    j1 = json_files_1[i]
    j2 = json_files_2[i]
    if os.path.basename(j1) != os.path.basename(j2):
        break
    file_mapping[j1] = j2

if len(file_mapping) != len(json_files_1):
    print("Unmatched files in sorting")
    sys.exit(1)



# {
#   "filename": "104-10004-10213_page_0003.png",
#   "text": "13-00000\n\n* 6. In response ty a question from Mr. Slawsoa I stated that most\nof the'26 cases upon which we based Gur statements involved foreign\n’ students, exchange teachers and other relatively transient persons,\n- and while a number of cases have certain points is common, they bear\n* Little similarity to the OSWALD case in that none involved a defector who -\n‘married prior to repatriating. I noted that paragraph 6 of our 6 April\n1964 memorandum to the Commission had pointed this out. Mr. Slawson\n‘indicated that hg was now satisfied on this matter. ‘\n\n‘9. Concerning the length of time taken by Soviet authorities to\nprocess exit visas for Suvict citizens married to foreign nationals\n(question 3c above), I stated that, in my upinion, the information\nprovided by State (in the third enclosure to Mr. Meeker's letter)\nsubstantially corresponded to the views expressed in paragraphs 6 and 7\nof our memorandum to the Commission dated 6 April 1964. Mr. Slawson\nasked if it would be possible to elaborate paragraph 7 of our memorandum\nof 6 April by providing 2 statistical breakdown of the cases on which our\nstatements were based. ] indicated that this could be done.\n\n8. At this point Mr. Slawson stated that as a result of our discussion\n\nhe felt that the question of possible inconsistenciés had been resolved.\n\n- However, he asked that «e send a brief written reply to the Commission's\nletter of 3 July 1964 embodying the substance of what [had said concerning\nthe basis for staternente included in our 6 April 1965 memorandum. [This\nwould include the gist of the draft reply to the Commission which I showed\nto C/SR on 8 July plus an elaboration of our statements concerning Soviet\n\nvisa applications. ]\n\n9. Mr. Slawson indicated that he would be sending parts of his report\ndealing with the Sovict inteHigence services to CIA for checking as to\ntheir accuracy. ‘He did nut say when this would ocaar.\n\n10. After concluding the meeting with Mr. Slawson, I yead Volume 52\nof the transcript cf testimony before the Commissiom. TjGs included the\nreinterview of Marina OSWALD.\n\nt-\n\n‘Lee H. Wigren\nC/SR/Ci/Research",
#   "metadata": {
#     "page_number": 12,
#     "dimensions": [
#       2544,
#       3319
#     ],
#     "avg_confidence": 0.899,
#     "median_confidence": 0.95,
#     "ocr_engine": "Tesseract 5.5.0",
#     "tesseract_config": "-l eng --oem 3 --psm 3"
#   }    


avg_confidence_j1_sum = 0.0
avg_confidence_j2_sum = 0.0
median_confidence_j1_array = []
median_confidence_j2_array = []
j1_avg_beats = 0
j2_avg_beats = 0
avg_equal = 0

for count, (j1, j2) in enumerate(file_mapping.items(), start=1):
    j1_json = get_file_contents(JSON_DIR_1, j1)
    j2_json = get_file_contents(JSON_DIR_2, j2)

    j1_conf = j1_json["metadata"]["confidence"]
    j2_conf = j2_json["metadata"]["confidence"]

    avg_confidence_j1_sum += j1_conf
    avg_confidence_j2_sum += j2_conf

    median_confidence_j1_array.append(j1_conf)
    median_confidence_j2_array.append(j2_conf)

    if j1_conf > j2_conf:
        j1_avg_beats += 1
    elif j1_conf < j2_conf:
        j2_avg_beats += 1
    else:
        avg_equal += 1

    if count % 100 == 0:
        print(f"Processed {count} files")

        




j1_overall_avg = avg_confidence_j1_sum/num_files
j1_overall_median = median_confidence_j1_array[num_files/2]

j2_overall_avg = avg_confidence_j2_sum/num_files
j2_overall_median = median_confidence_j2_array[num_files/2]


print("J1 Overall Median")
print(j1_overall_median)
print("J2 Overall Median")
print(j2_overall_median)

print()

print("J1 Overall Avg")
print(j1_overall_avg)
print("J2 Overall Avg")
print(j2_overall_avg)

print()
print()

print("J1 Beats J2")
print("Avg")
print(j1_avg_beats)

print()

print("J2 Beats J1")
print("Avg")
print(j1_avg_beats)

print()

print("Tied")
print("Avg")
print(avg_equal)




