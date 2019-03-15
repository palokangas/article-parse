import os.path
from parser import Extractor

# TODO: Create datamodel

def extract(filename):

    # pdf = None
    # has_content = False
    # while has_content == False:
    #     with open(filename, "rb") as pdf_file:
    #         pdf = pdftotext.PDF(pdf_file)
    #     if len(pdf[0]) == 0:
    #         file_body, file_extension = os.path.splitext(filename)
    #         ocr_filename = file_body + "-ocr" + file_extension
    #         if os.path.isfile(ocr_filename) == True:
    #             print("OCRd file found. Using it.")
    #             filename = ocr_filename
    #         else:
    #             print("No OCRd file found. Generating searchable PDF")
    #             pdfmanipulate.scan(filename, len(pdf))
    #             filename = ocr_filename
    #     else:
    #         has_content = True

    article = Extractor(filename)
    article.read()
    article.detect_headers_footers()
    article.remove_headers_footers()
    article.detect_columns()
    article.two_columns_to_one()
    article.detect_reference_start()
    article.detect_references_layout()
    if article.references_layout == "indentation":
        article.indentation_parse()
    else:
        article.author_year_parse()

    print(f"Number of detected references: {len(article.references)}")
    for ref in article.references:
        print(f"- {type(ref)}")
