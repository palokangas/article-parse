import os.path
import subprocess

# Create images from PDF file
# NOTE: Currently does not yield satisfactory results and this is not used by the parser.Extractor

def pdf2images(pdfimage):
    print("Converting image pdf to tiff-images")
    convertoutput = subprocess.run(["gs", "-dNOPAUSE", "-dBATCH", "-sDEVICE=tiffg4", r"-sOutputFile=tmp/scan_%d.tif", pdfimage])
    if convertoutput.returncode == 0:
        print("Successfully converted pdf to images.")
    else:
        print("No images created")

def scan(pdfimage, number_of_pages):

    pdf2images(pdfimage)

    for page in range(1, number_of_pages +1):
        subprocess.run(["tesseract", f"tmp/scan_{page}.tif", f"tmp/scan_{page}", "pdf"])

    page_names = ["tmp/scan_" + str(nr) + ".pdf" for nr in range(1, number_of_pages +1)]
    
    file_body, file_extension = os.path.splitext(pdfimage)
    output_filename = file_body + "-ocr" + file_extension
    subprocess.run(["pdfunite", *page_names, output_filename])
    subprocess.run(["rm", "tmp/scan*"])
