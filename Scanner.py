import numpy
import pytesseract
import cv2
from PIL import Image
import functools
import json
import difflib

TOP = 490
BOTTOM = 540
LEFT = 0
RIGHT = 1280

# diagnostic functions -------------------------------------------------
def read_single_frame(file_name, frame_number):
    cap = cv2.VideoCapture(file_name)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    ret, frame = cap.read()
    if ret:
        cropped_region = frame[TOP:BOTTOM, LEFT:RIGHT]
        gray = cv2.cvtColor(cropped_region, cv2.COLOR_BGR2GRAY)
        # gray = cv2.bitwise_not(gray)
        cv2.imshow("Frame", gray)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        cap.release()
        return gray
    cap.release()

def ocr_single_frame(frame):
    image_new = Image.fromarray(frame)
    text = pytesseract.image_to_string(image_new, lang='eng')
    print(text)


# -------------------------------------------------
"""
Implementations of the scanner itself, codes written based on EhsanKia Catalog Scanner
https://github.com/EhsanKia/CatalogScanner
"""


def read_frames(file_name: str):
    """
    using cv2 - capture each frame from the video file, crop the image to the second to last
    row & turn image into gray scale to reduce noise, return the cropped image as an array
    :param file_name: name of the mp4 file
    :return: an array
    """
    cap = cv2.VideoCapture(file_name)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    print(total_frames)

    # loop through each frame, crop, and turn into grayscale
    for i in range(int(total_frames)):
        cap.set(cv2.CAP_PROP_FRAME_COUNT, i)
        ret, frame = cap.read()
        if ret:
            cropped_region = frame[TOP:BOTTOM, LEFT:RIGHT]
            gray = cv2.cvtColor(cropped_region, cv2.COLOR_BGR2GRAY)
            yield gray

    cap.release() # release resources

# NOTE: for some reason this method doesn't seem to capture as much item as the method above
# def read_frames(file_name):
#     cap = cv2.VideoCapture(file_name)
#     total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
#     print(total_frames)
#
#     frame_index = 0
#     while True:
#         print(frame_index)
#         ret, frame = cap.read()
#         if not ret:
#             break
#         cropped_region = frame[TOP:BOTTOM, LEFT:RIGHT]
#         gray = cv2.cvtColor(cropped_region, cv2.COLOR_BGR2GRAY)
#         yield gray
#
#         frame_index += 1
#
#     cap.release()


def run_ocr(file_name, raw_result_file_name):
    """
    run tesseract-oct to detect text in image, append to a .txt file
    :param file_name: name of mp4 video file
    :param raw_result_file_name: name of the output .txt file
    """
    for frame in read_frames(file_name):
        image_new = Image.fromarray(frame)
        text = pytesseract.image_to_string(image_new, lang='eng')

        processed_text = text.strip().lower()
        if processed_text:
            formatted_text = f"{processed_text}\n"
            with open(raw_result_file_name, mode="a", encoding="utf-8") as result_file:
                result_file.write(formatted_text)
                print(formatted_text)


@functools.lru_cache(maxsize=None)
def get_items_db(file):
    """
    read a list of existing diys and stored as an array.
    Source: https://github.com/EhsanKia/CatalogScanner/blob/master/recipes/names.json
    """
    items_list = set()
    with open(file, "r", encoding='utf-8') as db:
        json_items = json.load(db)
        for i in range(len(json_items)):
            items_list.add(json_items[i][0].lower())
    return items_list


def clean_results(result_file, db, cleaned_result_file_name, write=False):
    """
    clean up result from run_ocr and match each entry with the current db
    :param result_file: result file generated by run_ocr
    :param db: array generated by get_items_db
    :param cleaned_result_file_name: name of the output file
    :param write: True if wants the output to be written to a .txt file, default is false
    :return: an array of items detected
    """
    raw_result = []
    with open(result_file, mode='r', encoding='utf-8') as raw_file:
        for each in raw_file:
            raw_result.append(each.strip())

    cleaned_result = set()

    for i in range(len(raw_result)):
        if raw_result[i] in db:
            cleaned_result.add(raw_result[i])
        else:
            matches = difflib.get_close_matches(raw_result[i], db, n=1, cutoff=0.7)
            if matches:
                print(f'unmatched word: {raw_result[i]}')
                print(f'found matches: {matches}')
                cleaned_result.add(matches[0])

    sorted_cleaned_result = sorted(list(cleaned_result))

    if write:
        with open(cleaned_result_file_name, mode="w", encoding='utf-8') as out_file:
            for each in sorted_cleaned_result:
                formatted = f'{each} DIY\n'
                out_file.write(formatted)
    return sorted_cleaned_result


def run_scanner(video_file_name):
    """
    Scanner code
    :param video_file_name: name of the video file
    """
    # set tesseract path script
    pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'

    # run ocr, write to a file
    raw_result_file_name = f'result_{video_file_name}.txt'
    run_ocr(video_file_name, raw_result_file_name)

    # get item db
    item_db = get_items_db('names.json')

    # get cleaned result
    cleaned_result_file_name = f'cleaned_result_{video_file_name}.txt'
    clean_results(raw_result_file_name, item_db, cleaned_result_file_name, True)

# functions for analysis purpose---------------------------------------------


def read_in_file(file_name):
    file = []
    with open(file_name, mode='r', encoding='utf-8') as in_file:
        for each in in_file:
            file.append(each.strip())
    return file


def compare(result_file, expected_file):
    # read in expected file
    expected = read_in_file(expected_file)
    result = read_in_file(result_file)

    missing = []
    for i in range(len(result)):
        if result[i] not in expected:
            missing.append(result[i])

    print(f'missing the following recipes: {missing}')
    percent_captured = (len(result) / len(expected)) * 100
    print(f'percent captured: {percent_captured}')
# --------------------------------------------------------------------------


def main():
    # set tesseract path script
    # Note: I have to do this, otherwise tesseract will throw an error, not sure why :(
    pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
    # run ocr, write to a file
    video_file_name = 'barrelbathtub-end.mp4'
    raw_result_file_name = f'result_{video_file_name}.txt'
    run_ocr(video_file_name, raw_result_file_name)
    # get item db
    item_db = get_items_db('names.json')
    # get cleaned result
    cleaned_result_file_name = f'cleaned_result_{video_file_name}.txt'
    clean_results(raw_result_file_name, item_db, cleaned_result_file_name, True)

    # diagnostic & analysis only
    # frame = read_single_frame(video_file_name, 350)
    # ocr_single_frame(frame)
    # compare('cleaned_result.txt', 'expected.txt')


if __name__ == "__main__":
    main()