import re
import pdftotext
from difflib import SequenceMatcher
import inspect

# TODO: Create datamodel

def pdf2plaintext(pdf, headers_footers, column_info):
    """
    Removes headers and footers from pdf and layouts two columns into one.
    param1: pdftotext.PDF object
    param2: list of header and footer rows
    param3: list of second column start positions per page
    returns: parsed text as string
    """

    text_pages = []

    with open("temptext2.txt", "w") as outfile:
        outfile.write("")

    # remove header and footer lines
    for page_number, page in enumerate(pdf):
        page = re.sub(r"\t", "    ", page)
        with open("temptext2.txt", "a") as outfile:
            outfile.write(page)
        page_as_lines = page.splitlines()

        for line_to_remove in headers_footers:
            print(f"DEL: {page_as_lines[line_to_remove]}")
            del page_as_lines[line_to_remove]

        # layout two columns into one
        if column_info[page_number] != 0:
            print(f"Processing two-column page {page_number} into one.")
            single_column_lines = []
            for row in page_as_lines:
                print(f"LEFT:---{row[:column_info[page_number]].strip()}---")
                single_column_lines.append(row[:column_info[page_number]])
            for row in page_as_lines:
                print(f"RIGHT:---{row[column_info[page_number]:].strip()}---")
                single_column_lines.append(row[column_info[page_number]:])
            text_pages.append("\n".join(single_column_lines))
        else:
            text_pages.append("\n".join(page_as_lines))

    return "\n\n".join(text_pages)

def extract(filename):

    pdf = None
    with open(filename, "rb") as pdf_file:
        pdf = pdftotext.PDF(pdf_file)

    header_footer_info = inspect.detect_header_footer(pdf)
    column_info = inspect.detect_columns(pdf)
    for index, value in enumerate(column_info):
        print("{}: {}".format(index, value))

    pdf_text = pdf2plaintext(pdf, header_footer_info, column_info)
    #print(pdf_text)
    with open("temptext.txt", "w") as outfile:
        outfile.write(pdf_text)

    # Find start position of any word reference that starts a line (should return only one match)
    potential_reference_starts = [r.start(0) for r in re.finditer(r"\n\s*references", pdf_text, re.IGNORECASE)]
    print("Found {} lines that could be the title of reference section.".format(len(potential_reference_starts)))

    if len(potential_reference_starts) == 1:
        reference_section = pdf_text[potential_reference_starts[0]:]

    # Find text start position where there is line change and whitespace before capital letter (how about von Neumann and de Welt?)
    reference_starts = [r.start(0) for r in re.finditer(r"\n\s+([A-Z].*\([12]\d\d\d\).*\.[\s\S]+?(?=\.))", reference_section)]

    slice_start = reference_starts[0] if len(reference_starts) > 0 else []
    for ref in reference_starts:
        #print(reference_section[slice_start:ref])
        slice_start = ref
    
    #print(references)
    #references = re.findall(r"\n\s+([A-Z].*\([12]\d\d\d\).*\.[\s\S]+?(?=\.))", reference_section)
    #references = [re.sub(r"\s+", ' ', ref) for ref in references]
    #return references





# Tämä löytää referenssin alusta vuosiluvun jälkeiseen toiseen pisteeseen, jos vuosiluvussa sulkeet
# re.findall(r"\n\s+([A-Z].*\([12]\d\d\d\).*\.[\s\S]+?(?=\.))", teksti)
