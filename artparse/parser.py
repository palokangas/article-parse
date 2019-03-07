import pdftotext
import inspect
import re

class Extractor(object):
    def __init__(self, pdffile):
        self.pdffile = pdffile
        self.pdf = None
        self.header_footer_info = None
        self.references_start_index = None
        self.references = []
        self.references_layout = None

    def __str__(self):
        if self.pdf:
            return "\n\n".join(self.pdf)
        else:
            print("The pdf file has not been converted to text, or there is no text (such as image pdf).")

    def get_fulltext(self):
        if self.pdf:
            return "\n\n".join(self.pdf) + "\n\n"
        else:
            return ""
          
    def read(self):
        """Read pdf from given file location into list of page strings"""

        if self.pdffile:
            try:
                with open(self.pdffile, "rb") as infile:
                    self.pdf = [page for page in pdftotext.PDF(infile)]
            except FileNotFoundError:
                print("Error: File not found")

    def detect_headers_footers(self):
        self.header_footer_info = inspect.detect_header_footer(self.pdf)

    def detect_columns(self):
        self.column_info = inspect.detect_columns(self.pdf)

    def detect_reference_start(self):

        self.references_start_index = 0
        pdftext = self.get_fulltext() #str(self.pdf)
        reference_regexes = [r"\breferences\b",           # Title: References
                            r"\bliterature cited\b"]     # Title: Literature cited                         
        potential_reference_starts = []

        for title_wording in reference_regexes:
            potential_reference_starts += [r.end() for r in re.finditer(title_wording, pdftext, re.IGNORECASE)]

        print("Found these starts of potential reference section")
        for ref in potential_reference_starts:
            print(f"MATCH: {pdftext[ref-1:ref+20]}... at location {ref}")

        print(f"There are {len(potential_reference_starts)} potential reference start points")

        if len(potential_reference_starts) == 0:
            print("Could not detect references start point.")
        elif len(potential_reference_starts) == 1:
            self.references_start_index = potential_reference_starts[0]
        else:
            print("There were more than one probable reference section. Detecting the most probable one.")
            most_probable_start_point = 0
            most_year_mentions = 0
            # Test of correct reference point is based on how many year numbers are followed by the keyword
            # As it is more likely for references to be in the end of the article (although not always the case)
            # The number of year numbers is multiplied by index of the finding...
            for index, test_start in enumerate(potential_reference_starts):
                test_text = pdftext[test_start:test_start+1000]
                nr_year_mentions = (index +1) * len(re.findall(r"[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;]", test_text))
                print(f"Position {test_start} is followed by {nr_year_mentions} year mentions.")
                if nr_year_mentions > most_year_mentions:
                    most_probable_start_point = test_start
                    most_year_mentions = nr_year_mentions
            self.references_start_index = most_probable_start_point

    def detect_references_layout(self):
        """
        Try to detect references layout on lines. At the moment only indentation really detected
        Layouts:
            indentation = reference starts in the beginning of line, next line(s) are indented
            not_detected = no layout can be inferred
        """
        empty_lines = 0
        starting_lines = 0
        indented_lines = 0
        rows = 0
        reference_section = self.get_fulltext()[self.references_start_index:self.references_start_index + 2000]
        for row in reference_section.splitlines():
            rows += 1
            if len(row) == 0 or row.isspace():
                empty_lines += 1
            elif row[0].isspace():
                indented_lines += 1
            else:
                starting_lines +=1

        if indented_lines > starting_lines / 2:
            self.references_layout = "indentation"
        else:
            self.references_layout = "not_detected"

    def _trim_left_margin(self, page):
        """
        Removes any whitespace margin from the left side of the page
        param1: page as string (or any string)
        returns trimmed page as string
        Note: ignores first and last rows on the page (possible left-over headers, page numbers)
        """

        #print("-------------------TRIMMING THIS")
        #print(page)
        # Detect margin
        total_rows = len(page.splitlines())
        left_start = 500
        for row_nr, row in enumerate(page.splitlines()):
            if row_nr == 0 or row_nr == total_rows - 1:
                continue
            row_start = 0
            for char_index, character in enumerate(row):
                if character.isspace():
                    row_start = char_index + 1
                else:
                    break
            if row_start < left_start:
                left_start = row_start
        # Remove margin
        newpage = []
        for row in page.splitlines():
            newpage.append(row[left_start:])
        #print("---------------------------INTO THIS:")
        #print("\n".join(newpage))

        return "\n".join(newpage)

    def remove_headers_footers(self):
        """
        Removes headers and footers from pages
        """

        with open("temptext2.txt", "w") as outfile:                     # REMOVE THIS: For debugging
            outfile.write("")

        # remove header and footer lines
        for page_nr, page in enumerate(self.pdf):
            with open("temptext2.txt", "a") as outfile:
                outfile.write(page)
            
            page_as_lines = page.splitlines()
            header_lines, footer_lines = self.header_footer_info

            for _ in range(header_lines):
                print(f"DEL: {page_as_lines[0]}")
                del page_as_lines[0]
            
            for _ in range(footer_lines):
                print(f"DEL: {page_as_lines[-1]}")
                del page_as_lines[-1]

            self.pdf[page_nr] = "\n".join(page_as_lines)

    def two_columns_to_one(self):
        """
        Lays out two columns into one.
        """

        with open("temptext3.txt", "w") as outfile:             ## REMOVE THIS: Only for debugging
            outfile.write("")

        for page_number, page in enumerate(self.pdf):
            with open("temptext3.txt", "a") as outfile:
                outfile.write(page + "\n" + "--- PAGE BREAK (only in this file) ---" + "\n")
            
            if self.column_info[page_number] != 0:
                page_as_lines = page.splitlines()

                singlestring = ""
                single_column_lines = []
                for row in page_as_lines:
                    single_column_lines.append(row[:self.column_info[page_number]])
                
                singlestring = self._trim_left_margin("\n".join(single_column_lines))
                single_column_lines = []

                for row in page_as_lines:
                    single_column_lines.append(row[self.column_info[page_number]:])

                singlestring += "\n" + self._trim_left_margin("\n".join(single_column_lines))
                self.pdf[page_number] = singlestring
            else:
                self.pdf[page_number] = self._trim_left_margin(page)

    def _trim_numbering(self, reference):
        """
        Detects and trims numbering from reference, return trimmed version
        """
        reference = re.sub(r"^\d+", "", reference)
        reference = re.sub(r"^\.", "", reference)
        reference = re.sub(r"^\s", "", reference)
        return reference

    def indentation_parse(self):
        """
        Parses the references string assuming references are separated by indendation
        Param1: reference section of an article as string
        Returns a list of detected references as strings
        """
        if self.references_start_index is None or self.references_start_index == 0:
            print("There is no info on reference start index. Doing nothing.")
            return

        reference_string = self.get_fulltext()[self.references_start_index:]

        print(f"Starting indentation parse on ref section on index {self.references_start_index} that looks like this:")
        print(reference_string[:400])

        MAX_LINES = 6     # MAX_LINES = how many consecutive lines with no indendation to tolerate before breaking
        current_reference = ""
        unindented_lines = 0

        for row in reference_string.splitlines():
            if len(row) == 0 or row.isspace():
                pass
            elif len(row) > 0 and row[0].isspace():
                current_reference += " " + row
                unindented_lines = 0
            else:
                if len(current_reference) != 0:
                    current_reference = self._trim_numbering(current_reference)
                    current_reference = re.sub(r"\s+", " ", current_reference)
                    if self._is_beyond_references(current_reference):
                        break
                    self.references.append(current_reference)
                current_reference = row
                unindented_lines += 1
                if unindented_lines > MAX_LINES:
                    break
        
        # If the article reached its end with the final reference, write the last reference
        if self._is_beyond_references == False:
            current_reference = self._trim_numbering(current_reference)
            current_reference = re.sub(r"\s+", " ", current_reference)
            self.references.append(current_reference)

        self._fix_references()

    def _is_beyond_references(self, reference):
        """Checks if parsing reached beyond references section. Returns boolean. """
        ending_indicators = [r"suggested citation",
                             r"would like to thank",
                             r"this article is",
                             r"further reading",
                             r"this article has been", 
                             r"by the authors",
                            ]

        for ending in ending_indicators:
            if len(re.findall(ending, reference, re.IGNORECASE)) > 0:
                return True        
        return False

    def _fix_references(self):
        """
        Apply small fixes to references here. Such as replace repetition symbols with author names
        """
        
        # Replace repetition symbols with author names
        for ref_index, reference in enumerate(self.references):
            if ref_index != 0 and reference[:2] in ["--", "––", "——"]:
                previous_reference = self.references[ref_index-1]
                authors_end_index = previous_reference.find(".")
                self.references[ref_index] = re.sub(r"^[-–—]+", previous_reference[:authors_end_index] + ".", reference)

        # Try detect if the last references are actually trailing info and delete as needed
        last_unclear = True
        while last_unclear == True:
            if len(re.findall(r"(?:19|20)\d\d", self.references[-1])) == 0:
                print("Deleting trailing text that does not seem to be a reference:")
                print(self.references[-1])
                del self.references[-1]
            else:
                last_unclear = False

    def author_year_parse(self):

        if self.references_start_index is None or self.references_start_index == 0:
            print("There is no info on reference start index. Doing nothing.")
            return

        reference_string = self.get_fulltext()[self.references_start_index:]

        reference_matcher = re.compile(r"\s*([A-ZÅÄÖØÆ].+[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;abcdef])")
        reference_starts = [r.start() for r in re.finditer(reference_matcher, reference_string)]

        slice_start = reference_starts[0] if len(reference_starts) > 0 else []
        for ref in reference_starts:
            ref_cleaned = re.sub(r"\s+", " ", reference_string[slice_start:ref].strip())

            if self._is_beyond_references(ref_cleaned):
                break
            self.references.append(ref_cleaned)
            slice_start = ref
 
        last_section = reference_string[slice_start:]
        potential_page_break = last_section.find("\n\n")
        if potential_page_break > 500:
            last_ref = last_section[:500]
        else:
            last_ref = last_section.strip()            
        
        last_ref = re.sub(r"\s+", " ", last_ref)
        if self._is_beyond_references(last_ref) == False:
            self.references.append(last_ref)

        self._fix_references()
