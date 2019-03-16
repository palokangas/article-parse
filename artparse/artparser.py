import pdftotext
from collections import defaultdict
from difflib import SequenceMatcher
import reference, author
import re

class Extractor(object):
    def __init__(self, pdffile):
        self.pdffile = pdffile
        self.pdf = None
        self.header_footer_info = None
        self.column_info = None
        self.references_start_index = None
        self.references = []
        self.references_layout = None
        self.reference_style = None
        self.is_using_semicolons = None

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

    def get_references(self):
        if len(self.references) > 0:
            return self.references
        else:
            self.read()
            self.detect_headers_footers()
            self.remove_headers_footers()
            self.detect_columns()
            self.two_columns_to_one()
            self.detect_reference_start()
            self.detect_references_layout()
            if self.references_layout == "indentation":
                self.indentation_parse()
            else:
                self.author_year_parse()
            return self.references

    def _is_using_semicolons(self):
        if self.is_using_semicolons is None:
            number_of_semicolons = 0
            for ref in self.references:
                found_semicolons = re.findall(";", ref.rawtext)
                number_of_semicolons += len(found_semicolons)
            print(f"Number of semicolons: {number_of_semicolons} in {len(self.references)} references.")
            if number_of_semicolons > len(self.references) / 4:
                self.is_using_semicolons = True
                return True
            else:
                self.is_using_semicolons = False
                return False
        else:
            return self.is_using_semicolons
        
    def read(self):
        """Read pdf from given file location into list of page strings"""

        if self.pdffile:
            try:
                with open(self.pdffile, "rb") as infile:
                    self.pdf = [page for page in pdftotext.PDF(infile)]
            except FileNotFoundError:
                print("Error: File not found")

    def detect_margins(self, page):
        
        left_margin = 0
        right_margin = -1
        left_found = False
        right_found = False
        longest_line = max([len(line) for line in page.splitlines()])

        while left_found == False:
            nonspaces = 0
            for row in page.splitlines():
                if len(row) > left_margin and row[left_margin].isspace():
                    pass
                else:
                    nonspaces +=1
            #print(f"Found {nonspaces} nonspaces at margin {left_found}")
            if nonspaces > 2:
                left_found = True
                print(f"Left margin found at {left_margin}")
            else:
                left_margin += 1

        while right_found == False:
            nonspaces = 0
            for row in page.splitlines():
                if row[right_margin].isspace():
                    pass
                else:
                    nonspaces +=1
            #print(f"Found {nonspaces} nonspaces at margin {right_margin}")
            if nonspaces > 2:
                right_found = True
                print(f"Right margin found at {right_margin}")
            else:
                right_margin -= 1
        
        return (left_margin, longest_line + right_margin)

    # TODO: Make work with matching but differenent even and odd page headers and footers
    def detect_headers_footers(self):
        """
        Detects the number of header and footer lines from pdf_object
        """
        header_lines = 0
        footer_lines = 0
        line_to_investigate = 0

        if len(self.pdf) < 2:
            print("There should be at least 2 pages to identify header and footer by similarity.")
            self.header_footer_info = (0 , 0)

        while line_to_investigate != "stop":

            lines_to_compare = []    
            for page in self.pdf:
                # get the line in question, remove whitespace, add to list
                lines_to_compare.append(re.sub(r"\s+", " ", page.splitlines()[line_to_investigate]))
            
            similarity_scores = []
            line1 = lines_to_compare[0]
            for line2 in lines_to_compare[1:]:
                similarity_scores.append(SequenceMatcher(None, line1, line2).ratio())
                #print(SequenceMatcher(None, line1, line2).ratio())
                line1 = line2

            print("For line {} the similarity score is {}".format(line_to_investigate, (sum(similarity_scores) / len(similarity_scores))))
            if (sum(similarity_scores) / len(similarity_scores)) > 0.7:
                if line_to_investigate >= 0:
                    header_lines += 1
                    line_to_investigate += 1
                else:
                    footer_lines += 1
                    line_to_investigate -= 1
            else:
                if line_to_investigate >= 0:
                    line_to_investigate = -1
                else:
                    line_to_investigate = "stop"
        
        self.header_footer_info = (header_lines, footer_lines)

    def detect_columns(self):
        """
        Detects if there are one or two columns
        Stores second column start indexes in a list of integers
        """

        second_columns_start_indexes = []

        for page in self.pdf:
            left_margin, right_margin = self.detect_margins(page)
            longest_line = 0
            for row in page.splitlines():
                if len(row) > longest_line:
                    longest_line = len(row)

            spaces = defaultdict(int)
            rows = 0
            for row in page.splitlines():
                if len(row) < longest_line:
                    row = row + (" " * (longest_line-len(row)))
                rows += 1
                for space_location in re.finditer(r" ", row):
                    position = space_location.start(0)

                    if len(row) > 40 and position > 19 and position < len(row) - 19:
                    #if position >= left_margin or position <= right_margin:
                        spaces[position] += 1

            print(f"{max(spaces.values())} / {rows} = {max(spaces.values()) / rows}")
            if (max(spaces.values()) / rows) < 0.61:
                second_columns_start_indexes.append(0)
                continue

            highest_space_nr = 0
            index_of_second_column = 0
            #for position, value in spaces.items():
            for position, value in sorted(spaces.items()):
                if value >= highest_space_nr:
                    highest_space_nr = value
                    index_of_second_column = position
                    print(f"Changing column start value to {position}")
            index_of_second_column += 1

            second_columns_start_indexes.append(index_of_second_column)

        self.column_info = second_columns_start_indexes

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
            # As it is more likely for references to be in the end of the self (although not always the case)
            # The number of year numbers is multiplied by index of the finding...
            for index, test_start in enumerate(potential_reference_starts):
                test_text = pdftext[test_start:test_start+1000]
                nr_year_mentions = (index +1) * len(re.findall(r"[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;]", test_text))
                print(f"Position {test_start} is followed by {nr_year_mentions} year mentions.")
                if nr_year_mentions > most_year_mentions:
                    most_probable_start_point = test_start
                    most_year_mentions = nr_year_mentions
            self.references_start_index = most_probable_start_point

    def detect_reference_style(self):

        """
        Detects reference style: currently author-year-title-publication vs. author-title-publication-year
        The detection is based simply on location of the year in the reference: end vs. start
        This also detects whether the publication year is parenthesized.
        """
        if len(self.references) < 1:
            print("There are no references.")
            return
        
        self.reference_style = {}

        # Try to detect ISO 690 type references style based on location of year number
        year_positions = []
        for reference in self.references:
            years = [r.end() for r in re.finditer(r"(?:19|20)\d\d", reference.rawtext)] 
            for match in years: 
                year_positions.append(match/len(reference))
        
        if sum(year_positions)/len(year_positions) > 0.6:
            self.reference_style['bibref'] = 'iso690'
        else:
            self.reference_style['bibref'] = 'apa'

        # Detect if year numbers are parenthesized
        parenthesized = 0
        for reference in self.references:
            years = [r.end() for r in re.finditer(r"(?:19|20)\d\d", reference.rawtext)] 
            for match in years: 
                if match < len(reference) - 1:
                    if reference.rawtext[match] == ")":
                        parenthesized += 1

        if parenthesized / len(self.references) > 0.5:
            self.reference_style['parenthesis'] = True
        else:
            self.reference_style['parenthesis'] = False
        
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
        Param1: reference section of an self as string
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
                    self.references.append(reference.Reference(current_reference))
                current_reference = row
                unindented_lines += 1
                if unindented_lines > MAX_LINES:
                    break
        
        # If the self reached its end with the final reference, write the last reference
        if self._is_beyond_references == False:
            current_reference = self._trim_numbering(current_reference)
            current_reference = re.sub(r"\s+", " ", current_reference)
            self.references.append(reference.Reference(current_reference))

        self._fix_references()

    def _is_beyond_references(self, reference):
        """Checks if parsing reached beyond references section. Returns boolean. """
        ending_indicators = [r"suggested citation",
                             r"would like to thank",
                             r"this self is",
                             r"further reading",
                             r"this self has been", 
                             r"by the authors",
                            ]

        for ending in ending_indicators:
            if len(re.findall(ending, reference, re.IGNORECASE)) > 0:
                return True        
        return False

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
            self.references.append(reference.Reference(ref_cleaned))
            slice_start = ref
 
        last_section = reference_string[slice_start:]
        potential_page_break = last_section.find("\n\n")
        if potential_page_break > 500:
            last_ref = last_section[:500]
        else:
            last_ref = last_section.strip()            
        
        last_ref = re.sub(r"\s+", " ", last_ref)
        if self._is_beyond_references(last_ref) == False:
            self.references.append(reference.Reference(last_ref))

        self._fix_references()

    def _fix_references(self):
        """
        Apply small fixes to references here. Such as replace repetition symbols with author names
        """
        
        # Replace repetition symbols with author names
        for ref_index, reference in enumerate(self.references):
            if ref_index != 0 and reference.rawtext[:2] in ["--", "––", "——"]:
                previous_reference = self.references[ref_index-1]
                authors_end_index = previous_reference.rawtext.find(".")
                self.references[ref_index].rawtext = re.sub(r"^[-–—]+", previous_reference.rawtext[:authors_end_index] + ".", reference.rawtext)

        # Try detect if the last references are actually trailing info and delete as needed
        last_unclear = True
        while last_unclear == True:
            if len(re.findall(r"(?:19|20)\d\d", self.references[-1].rawtext)) == 0:
                print("Deleting trailing text that does not seem to be a reference:")
                print(self.references[-1])
                del self.references[-1]
            else:
                last_unclear = False

    # TODO: Distinguish authors of an edited book = ending with (eds.), "(ed.)" etc.
    def create_authors(self, ref, overwrite=True):
        """
        Creates a list of Author objects from raw reference text.
        To prevent overwriting existing information, set overwrite to False        
        """
        
        if len(ref.authors) > 0 and overwrite == False:
            print("Detected authors exist for this reference and overwrite set to False. Not doing anything.")
            return

        if self.reference_style['bibref'] == "apa":
            if self.reference_style['parenthesis'] == True:
                year_matcher = re.compile(r"\((?:19|20)\d\d")
            else:
                year_matcher = re.compile(r"(?:19|20)\d\d")

            try:
                year_start = re.search(year_matcher, ref.rawtext).start()
            except:
                print("Cannot find year in reference. Returning with no success.")
                return

            author_splice = ref.rawtext[:year_start]
            author_matcher = re.compile(r"[A-Z].+?,(?:\s*[A-ZÄÖÅ-].*?\.*)+\s*[;,.&]")
            detected_authors = re.finditer(author_matcher, author_splice)
            number_of_authors = 0

            # If matching people names are found, add them as authors
            for single_author in detected_authors:
                number_of_authors += 1
                author_string = single_author.group()
                print(f"Parsing author {author_string}")
                comma = author_string.find(",")
                firstname = author_string[comma+1:].strip()
                lastname = author_string[:comma].strip()
                if firstname[-1] in ["&", ",", "("]: firstname = firstname[:-1]
                if lastname[-1] in ["&", ",", "("]: lastname = lastname[:-1]
                new_author = author.Author(firstname=firstname, lastname=lastname)
                ref.authors.append(new_author)
                print(new_author)
                author_splice = author_splice[single_author.end():]
                print(f"Remaining string to parse into authors: {author_splice}")

            # If no people names are found, assume the author is an institution, anonymous report, software etc.
            if number_of_authors == 0:
                new_author = author.Author(non_person_author=author_splice.strip())
                ref.authors.append(new_author)
                print(f"Found non-person-author: {new_author}")

        elif self.reference_style['bibref'] == "iso690":
            author_splice = ref.rawtext.strip()
            author_matcher = re.compile(r"^[A-Z].{0,25}?,(?:\s*[A-ZÄÖÅ-]?\.*)+\s*[;,.&]")
            number_of_authors = 0
            more_to_parse = True

            # Search for formatted author names one by one
            while more_to_parse:
                author_match = re.search(author_matcher, author_splice)
                if author_match is None:
                    more_to_parse = False
                else:
                    number_of_authors += 1
                    author_string = author_match.group()
                    print(f"Parsing author {author_string}")
                    comma = author_string.find(",")
                    firstname = author_string[comma+1:].strip()
                    lastname = author_string[:comma].strip()
                    if firstname[-1] in ["&", ",", "(", ";"]: firstname = firstname[:-1]
                    if lastname[-1] in ["&", ",", "(", ";"]: lastname = lastname[:-1]
                    new_author = author.Author(firstname=firstname, lastname=lastname)
                    ref.authors.append(new_author)
                    print(new_author)
                    author_splice = author_splice[author_match.end():].strip()
                    print(f"Remaining string to parse into authors: {author_splice}")

            # If no people names are found, assume the author is an institution, anonymous report, software etc.
            if number_of_authors == 0:
                # Assume the name ends with period and whitespace character. This might yield limited results
                # If name is of type "BIG INSTITUTION. Sub-department." etc. but we will still get BIG INSTITUTION.
                name_end = re.search(r"\.\s", author_splice)
                author_splice = author_splice[:name_end.start()].strip()
                if author_splice[-1] in ["&", ",", "(", ";"]: author_splice = author_splice[:-1]               
                new_author = author.Author(non_person_author=author_splice.strip())
                ref.authors.append(new_author)
                print(f"Found non-person-author: {new_author}")

        else:
            print("No reference style available. Trying blindfolded with possibly broken success")
            

    