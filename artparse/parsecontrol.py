import re
import os.path
import pdftotext
from difflib import SequenceMatcher
import inspect
import pdfmanipulate

# TODO: Create datamodel

def trim_left_margin(page):
    """
    Removes any whitespace margin from the left side of the page
    param1: page as string
    returns a page with no left margin
    """
    #print("-------------------TRIMMING THIS")
    #print(page)
    # Detect margin
    left_margin = 500
    for row in page.splitlines():
        row_whitespace = 0
        for char_index, character in enumerate(row):
            if character.isspace():
                row_whitespace = char_index
            else:
                break
        if row_whitespace < left_margin:
            left_margin = row_whitespace
    # Remove margin
    newpage = []
    for row in page.splitlines():
        newpage.append(row[left_margin:])
    #print("---------------------------INTO THIS:")
    #print("\n".join(newpage))

    return "\n".join(newpage)    


def remove_headers_footers(original, headers_footers):
    """
    Removes headers and footers from pages
    param1: list of pages as strings
    param2: tuple: nr of header rows and nr of footer rows
    returns a modified copy of the original list - no side effects 
    """

    newpages = []
    with open("temptext2.txt", "w") as outfile:
        outfile.write("")

    # remove header and footer lines
    for page in original:
        with open("temptext2.txt", "a") as outfile:
            outfile.write(page)
        
        page_as_lines = page.splitlines()
        header_lines, footer_lines = headers_footers

        for _ in range(header_lines):
            print(f"DEL: {page_as_lines[0]}")
            del page_as_lines[0]
        
        for _ in range(footer_lines):
            print(f"DEL: {page_as_lines[-1]}")
            del page_as_lines[-1]

        newpages.append("\n".join(page_as_lines))
    
    return newpages      

def two_columns_to_one(pdf, column_info):
    """
    Lays out two columns into one.
    param1: list of pages as strings
    param2: list of second column start positions per page
    returns a copy of the original list of strings
    """
    text_pages = []

    with open("temptext3.txt", "w") as outfile:
        outfile.write("")

    # remove header and footer lines
    for page_number, page in enumerate(pdf):
        with open("temptext3.txt", "a") as outfile:
            outfile.write(page + "\n\n")
        
        page_as_lines = page.splitlines()

        # layout two columns into one, trimming each column of left margin
        if column_info[page_number] != 0:
            singlestring = ""
            #print(f"Processing two-column page {page_number} into one.")
            single_column_lines = []
            for row in page_as_lines:
                #print(f"LEFT:---{row[:column_info[page_number]].strip()}---")
                single_column_lines.append(row[:column_info[page_number]])
            
            singlestring = trim_left_margin("\n".join(single_column_lines))
            single_column_lines = []

            for row in page_as_lines:
                #print(f"RIGHT:---{row[column_info[page_number]:].strip()}---")
                single_column_lines.append(row[column_info[page_number]:])

            singlestring += "\n" + trim_left_margin("\n".join(single_column_lines))
            text_pages.append(singlestring)
        else:
            text_pages.append(trim_left_margin("\n".join(page_as_lines)))

    return text_pages



def pdf2plaintext(pdf, headers_footers, column_info):
    """
    Removes headers and footers from pdf and layouts two columns into one.
    param1: pdftotext.PDF object
    param2: tuple: nr of header rows and nr of footer rows
    param3: list of second column start positions per page
    returns: parsed text as string
    """

    text_pages = []

    with open("temptext2.txt", "w") as outfile:
        outfile.write("")

    # remove header and footer lines
    for page_number, page in enumerate(pdf):
        #page = re.sub(r"\t", "    ", page)
        with open("temptext2.txt", "a") as outfile:
            outfile.write(page)
        
        page_as_lines = page.splitlines()
        header_lines, footer_lines = headers_footers

        for _ in range(header_lines):
            print(f"DEL: {page_as_lines[0]}")
            del page_as_lines[0]
        
        for _ in range(footer_lines):
            print(f"DEL: {page_as_lines[-1]}")
            del page_as_lines[-1]            

        # layout two columns into one
        if column_info[page_number] != 0:
            #print(f"Processing two-column page {page_number} into one.")
            single_column_lines = []
            for row in page_as_lines:
                #print(f"LEFT:---{row[:column_info[page_number]].strip()}---")
                single_column_lines.append(row[:column_info[page_number]])
            for row in page_as_lines:
                #print(f"RIGHT:---{row[column_info[page_number]:].strip()}---")
                single_column_lines.append(row[column_info[page_number]:])
            text_pages.append("\n".join(single_column_lines))
        else:
            text_pages.append("\n".join(page_as_lines))

    return "\n\n".join(text_pages)

def extract(filename):

    pdf = None
    has_content = False

    while has_content == False:
        with open(filename, "rb") as pdf_file:
            pdf = pdftotext.PDF(pdf_file)
        if len(pdf[0]) == 0:
            file_body, file_extension = os.path.splitext(filename)
            ocr_filename = file_body + "-ocr" + file_extension
            if os.path.isfile(ocr_filename) == True:
                print("OCRd file found. Using it.")
                filename = ocr_filename
            else:
                print("No OCRd file found. Generating searchable PDF")
                pdfmanipulate.scan(filename, len(pdf))
                filename = ocr_filename
        else:
            has_content = True

    pdf_text = [re.sub(r"\r", "    ", page) for page in pdf]

    # Detect and remove headers and footers
    header_footer_info = inspect.detect_header_footer(pdf_text)
    pdf_text = remove_headers_footers(pdf_text, header_footer_info)
    
    # Detect columns and re-layout  
    column_info = inspect.detect_columns(pdf_text)
    for index, value in enumerate(column_info):
        print("{}: {}".format(index, value))
    pdf_text = two_columns_to_one(pdf_text, column_info)
    
    #trim_left_margin(pdf_text)

    article_as_string = "\n\n".join(pdf_text)

    with open("temptext.txt", "w") as outfile:
        outfile.write(article_as_string)

    reference_section_start = inspect.detect_reference_start_index(article_as_string)
    
    if reference_section_start == 0:
        return "Failed to detect reference start point" 
    else:
        reference_section = article_as_string[reference_section_start:]

    reference_matcher = inspect.detect_reference_style(reference_section.lstrip())
    print(reference_matcher)

    # Delete the line containing title "References"
    reference_section = re.sub(r"\n.*references.*?\n", "", reference_section, re.IGNORECASE)

    reference_starts = [r.start() for r in re.finditer(reference_matcher, reference_section)]

    references = []
    slice_start = reference_starts[0] if len(reference_starts) > 0 else []
    for ref in reference_starts:
        ref_cleaned = re.sub(r"\s+", " ", reference_section[slice_start:ref].strip())
        references.append(ref_cleaned)
        slice_start = ref
    
    print("\n- ".join(references))

    #print(references)
    #references = re.findall(r"\n\s+([A-Z].*\([12]\d\d\d\).*\.[\s\S]+?(?=\.))", reference_section)
    #references = [re.sub(r"\s+", ' ', ref) for ref in references]
    #return references
