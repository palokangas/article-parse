import re
import pdftotext

# TODO: Create datamodel

def extract(filename):

    pdf = None
    with open(filename, "rb") as pdf_file:
        pdf = pdftotext.PDF(pdf_file)

    pdf_text = "\n\n".join(pdf)

    # Find start position of any word reference that starts a line (should return only one match)
    potential_reference_starts = [r.start(0) for r in re.finditer(r"\n\s*references", pdf_text, re.IGNORECASE)]

    if len(potential_reference_starts) == 1:
        reference_split = pdf_text[potential_reference_starts[0]:]

    # OK. This now works for well formatted APA. Let's check with other sources
    references = re.findall(r"\n\s+([A-Z].*\([12]\d\d\d\).*\.[\s\S]+?(?=\.))", reference_split)
    
    references = [re.sub(r"\s+", ' ', ref) for ref in references]

    return references





# Tämä löytää referenssin alusta vuosiluvun jälkeiseen toiseen pisteeseen, jos vuosiluvussa sulkeet
# re.findall(r"\n\s+([A-Z].*\([12]\d\d\d\).*\.[\s\S]+?(?=\.))", teksti)
