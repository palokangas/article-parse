# TODO: Author parsing fails if author format changes in single reference
# eg. lastname-firstname --> firstname-lastname: "Lastname1, E., F. Lastname2"

import sys
import pdftotext
from collections import defaultdict
from difflib import SequenceMatcher
from . import reference
from . import author
#import reference
#import author
import regex as re

class Extractor(object):
    def __init__(self, pdffile=None):
        self.pdffile = pdffile
        self.pdf = None
        self.header_footer_info = None
        self.column_info = None
        self.margin_info = None
        self.references_start_index = None
        self.references = []
        self.references_layout = None
        self.reference_style = {"semicolons": None, "parenthesis": None, "bibref": None, "comma_inside_name": None}

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
            self.remove_document_margins()
            self.detect_columns()
            self.two_columns_to_one()
            self.detect_reference_start()
            self.detect_references_layout()
            if self.references_layout == "indentation":
                self.indentation_parse()
            else:
                self.author_year_parse()
            return self.references

    def detect_semicolons(self):
        number_of_semicolons = 0
        for ref in self.references:
            found_semicolons = re.findall(";", ref.rawtext)
            number_of_semicolons += len(found_semicolons)
        if number_of_semicolons > len(self.references) / 4:
            self.reference_style["semicolons"] = True
            return True
        else:
            self.reference_style["semicolons"] = False
            return False
        
    def read(self):
        """Read pdf from given file location into list of page strings"""

        if self.pdffile:
            try:
                with open(self.pdffile, "rb") as infile:
                    self.pdf = [page for page in pdftotext.PDF(infile)]
            except FileNotFoundError:
                print("Error: File not found")

    def remove_document_margins(self):
        """ Remove margins from the whole document. Only allow fully succesful results."""
        try:
            newpdf = []
            for page in self.pdf:
                newpdf.append(self.remove_page_margins(page))
            self.pdf = newpdf
        except:
            e = sys.exc_info()[0]
            print("Something went wrong removing margins from whole document")
            print(e) 

    def remove_page_margins(self, page):
        """ Removes margins from document"""
        try:
            self.detect_margins(page, allow_junk=2)
            left_start, right_end = (self.margin_info)
            stripped_page = "\n".join(row[left_start:right_end+1] for row in page.splitlines())
            #print(f"----- MARGIN INFO: {self.margin_info} STRIPPED PAGE:")
            #print(stripped_page)
            return stripped_page
        except TypeError as e:
            print(e)
        except:
            e = sys.exc_info()[0]
            print("Something went wrong removing margins from page. Page unmodified")
            print(e)
            return page

    def detect_margins(self, page, allow_junk=2):
        """
        Detects margins on a page.
        Allowed levels of junk in the margin can vary:
        0: margin needs to be all whitespace
        1: margin can contain isolated numbers and punctuation (to match page numbers etc.)
        2: left margin can contain isolated text (to match small layout elements, such as names or keywords)
           and don't strip any text from right margin
        """

        rows = page.splitlines()
        column_length = len(rows)
        longest_row = max([len(row) for row in rows])
        start_of_text = 0
        end_of_text = longest_row -1

        page_as_columns = [[] for _ in range(0, longest_row)]
        for row in rows:
            if len(row) < longest_row:
                row = row + " " * (longest_row - len(row)) 
            for index, char in enumerate(row):
                page_as_columns[index].append(char)

        columns_info = []
        for column in page_as_columns:
            column_data = {"spaces": 0, "numbers": 0, "punctuation": 0, "text": 0, "other": 0}
            for char in column:
                if char.isspace():
                    column_data['spaces'] += 1
                elif char.isnumeric():
                    column_data['numbers'] += 1
                elif char in [",", ";", "(", ")", ".", "{", "}", "[", "]"]:
                    column_data['punctuation'] += 1
                elif char.isalpha():
                    column_data['text'] += 1
                else:
                    column_data['other'] += 1   
            columns_info.append(column_data)

        # left margin detection
        for index, info in enumerate(columns_info):
            if allow_junk == 0:
                if info['spaces'] == column_length:
                    start_of_text += 1
                else: break
            if allow_junk == 1:
                if (info['spaces'] + info['numbers'] + info['punctuation']) == column_length:
                    if info['numbers'] < 6:
                        start_of_text += 1
                    else: break
                else: break
            if allow_junk == 2:
                if info['text'] < 6 and info['numbers'] < 6:
                    start_of_text += 1
                else: break

        # right margin detection: since right can be unaligned, strip very carefully and no text at all
        for index, info in reversed(list(enumerate(columns_info))):
            if allow_junk == 0:
                if info['spaces'] == column_length:
                    end_of_text -= 1
                else: break
            if allow_junk == 1 or allow_junk == 2:
                if (info['spaces'] + info['numbers'] + info['punctuation']) == column_length:
                    if info['numbers'] < 2:
                        end_of_text -= 1
                    else: break
                else: break
 
        self.margin_info = (start_of_text, end_of_text)

    # TODO: Make work with matching but differenent even and odd page headers and footers
    def detect_headers_footers(self, page_parity="even"):
        """
        Detects the number of header and footer lines from pdf_object
        set page_parity for even or odd pages (headers and footers often vary between even and odd pages)
        """
        header_lines = 0
        footer_lines = 0
        line_to_investigate = 0
        start_page = 0 if page_parity == "even" else 1

        if len(self.pdf) < 5:
            print("There should be at least 4 pages to identify header and footer by similarity.")
            self.header_footer_info = (0 , 0)

        while line_to_investigate != "stop":
            page_number = start_page
            lines_to_compare = []
            while page_number < len(self.pdf):
                print(f"Investingating page number {page_number} for headers and footers")
                page = self.pdf[page_number]
                # get the line in question, remove whitespace, add to list
                lines_to_compare.append(re.sub(r"\s+", " ", page.splitlines()[line_to_investigate]))
                page_number += 2

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
            longest_line = max([len(row) for row in page.splitlines()])
            print(f"Longest line = {longest_line} characters")
            spaces = defaultdict(int)
            rows = 0
            try:
                for row in page.splitlines():
                    if len(row) < longest_line:
                        row = row + (" " * (longest_line-len(row)))
                        print(f"New row: {row}")
                    rows += 1
                    for space_location in re.finditer(r" ", row):
                        position = space_location.start(0)
                        midpoint = len(row) / 2 if len(row) > 40 else 0
                        if abs(position - midpoint) < 20:
                        #if len(row) > 40 and position > 19 and position < len(row) - 19:
                            spaces[position] += 1
            except:
                e = sys.exc_info()[0]
                print("Something went wrong trying to detect space locations for page")
                print(e)

            index_of_second_column = 0
            try:
                print(f"Ratio of highest whitespace to rows: {max(spaces.values())} / {rows} = {max(spaces.values()) / rows}")
                if (max(spaces.values()) / rows) < 0.61:
                    #second_columns_start_indexes.append(0)
                    continue

                highest_space_nr = 0
                for position, value in sorted(spaces.items()):
                    if value >= highest_space_nr:
                        highest_space_nr = value
                        index_of_second_column = position
                        #print(f"Changing column start value to {position}")
                index_of_second_column += 1

            except ValueError as e:
                print("Getting ValueError, which probably means there are no columns on this page")
                print(e)
            finally:
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
        Detects reference style:
        author-year-title-publication vs. author-title-publication-year
        The detection is based simply on location of the year in the reference: end vs. start
        This also detects whether the publication year is parenthesized.
        This also detects whether style "Author F, Author DI" or "Author, F., Author D. I." is used.
        """
        if len(self.references) < 1:
            print("There are no references.")
            return
        
        self.reference_style = {}
        # Try to detect ISO 690 type references style based on location of year number
        print("Try to detect ISO 690")
        year_positions = []
        for reference in self.references:
            years = [r.end() for r in re.finditer(r"(?:19|20)\d\d", reference.rawtext)] 
            for match in years: 
                year_positions.append(match/len(reference))
        
        if sum(year_positions)/len(year_positions) > 0.6:
            self.reference_style['bibref'] = 'iso690'
        else:
            self.reference_style['bibref'] = 'apa'

        
        # Detect use of semicolons
        self.reference_style['semicolons'] = self.detect_semicolons()

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
        
        # Detect whether "Author F, Author DI" vs. "Author, F., Author, D.I." is used
        self.reference_style['comma_inside_name'] = True
        commas = 0
        for reference in self.references:
            commas += self.extract_authors(reference, just_count=True)
        self.reference_style['comma_inside_name'] = False
        nocommas = 0
        for reference in self.references:
            nocommas += self.extract_authors(reference, just_count=True)
        if commas > nocommas:
            self.reference_style['comma_inside_name'] = True

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

        with open("temptext-new-layout.txt", "w") as outfile:             ## REMOVE THIS: Only for debugging
            outfile.write("")

        for page_number, page in enumerate(self.pdf):
            
            if self.column_info[page_number] != 0:
                page_as_lines = page.splitlines()

                singlestring = ""
                single_column_lines = []
                for row in page_as_lines:
                    single_column_lines.append(row[:self.column_info[page_number]])
                
                #singlestring = self.remove_page_margins("\n".join(single_column_lines))
                singlestring = self._trim_left_margin("\n".join(single_column_lines))
                single_column_lines = []

                for row in page_as_lines:
                    single_column_lines.append(row[self.column_info[page_number]:])

                #singlestring += "\n" + self.remove_page_margins("\n".join(single_column_lines))
                singlestring += "\n" + self._trim_left_margin("\n".join(single_column_lines))
                self.pdf[page_number] = singlestring
            else:
                #self.pdf[page_number] = self.remove_page_margins(page)
                self.pdf[page_number] = self._trim_left_margin(page)
            
            with open("temptext-new-layout.txt", "a") as outfile:
                outfile.write(page + "\n" + "--- PAGE BREAK (only in this file) ---" + "\n")

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
        Param1: reference section of self as string
        Returns a list of detected references as strings
        """
        if self.references_start_index is None or self.references_start_index == 0:
            print("There is no info on reference start index. Doing nothing.")
            return

        reference_string = self.get_fulltext()[self.references_start_index:]
        print("----------- FULL REFERENCE SECTION STARTS -----------")
        print(reference_string)
        print("----------- FULL REFERENCE SECTION ENDS -----------")
        
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
        
        print(f"Current: {current_reference}")
        print(f"Value of beyond refernces = {self._is_beyond_references(current_reference)}")
        # If the self reached its end with the final reference, write the last reference
        if self._is_beyond_references(current_reference) == False:
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
        reference_matcher = re.compile(r"\s*(\p{Lu}.+[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;abcdef])")
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
    def extract_authors(self, ref, just_count=False):
        """
        Creates a list of Author objects from raw reference text.
        Toggling just_count will not store anything, just return how many authors are matched
        """
        number_of_authors = 0
        year_position = -1
        author_splice = ref.rawtext.lstrip()
        #print("Author-splice in the beginning is:")
        #print(author_splice)
        # Narrow down the searched string for apa-style references
        if self.reference_style['bibref'] == "apa":
            # if self.reference_style['parenthesis'] == True:
            #     year_matcher = re.compile(r"\((?:19|20)\d\d[abcdef]{0,1}\)")
            # else:
            #     year_matcher = re.compile(r"(?:19|20)\d\d[abcdef]{0,1}")
            try:
                #year_position = re.search(year_matcher, ref.rawtext)
                #print("We have APA-style reference, and now the splice is:")
                #print(author_splice)
                # Make sure there is whitespace in the end for regex purposes
                author_splice = ref.rawtext[:ref.span_authors_end].lstrip() + " "
            except AttributeError as e:
                print("AttributeError getting year from reference")
                print(e)
            except IndexError as e:
                print("IndexError splicing reference text.")
                print(e)
            except:
                e = sys.exc_info()[0]
                print(e)
                print("Cannot find year in reference. Returning 0 authors found.")
                return 0

        print("\n-----------------Starting to extract authors from this text:")
        print(author_splice)

        if self.reference_style['comma_inside_name'] == True:
            # Matches "Author, F.N." -style:
            #author_matcher = re.compile(r"^([A-ZÅÖÄØŒÆØ].{0,25}?,(?:\s*[A-ZÅÖÄØŒÆØ-]?\.*)+\s*[;,.&])")
            author_matcher = re.compile(r"^(\p{Lu}.{0,25}?,(?:\s*[\p{Lu}-]?\.*)+\s*[;,.&])")
         
        elif self.reference_style['comma_inside_name'] == False:
            # Matches "Author FN" -style
            #author_matcher = re.compile(r"^((?:[A-ZÖÄØŒÆ][\w-]+\s){1,3}[A-ZÖÄØŒÆ-]{1,3})[\s,.(]")
            author_matcher = re.compile(r"^((?:\p{Lu}[\w-]+\s){1,3}[\p{Lu}-]{1,3})[\s,.(]")

        more_to_parse = True
        print(f"--------\n---->Starting to parse this: {author_splice} <--------")
        
        try:
            # Search for formatted author names one by one
            while more_to_parse:
                author_match = re.search(author_matcher, author_splice)
                if author_match is None:
                    more_to_parse = False
                else:
                    number_of_authors += 1
                    author_string = author_match.group()
                    print(f"Parsing author {author_string}")
                    if self.reference_style['comma_inside_name'] == True:
                        comma = author_string.find(",")
                        firstname = author_string[comma+1:].strip()
                        lastname = author_string[:comma].strip()                    
                    else:
                        while author_string[-1] in ["&", ",", "(", ";"]:
                            author_string = author_string[:-1]
                        split_name = author_string.strip().split()
                        lastname = " ".join(split_name[0:-1])
                        firstname = ""
                        firstname_part = split_name[-1]
                        dash = firstname_part.find("-")
                        if dash == -1:
                            for letter in firstname_part:
                                firstname = firstname + letter + "."
                        elif dash > 0 and dash < len(firstname_part) - 2 and len(firstname_part) > 2:
                            for index, letter in enumerate(firstname_part):
                                if index not in [dash-1, dash, dash+1]:
                                    firstname = letter + "."
                                else:
                                    firstname = firstname + letter
                        else:
                            print("Not prepared for this kind of firstname. Just store the full abbreviation")
                            firstname = firstname_part.strip()

                    
                    while len(firstname) > 0 and firstname[-1] in ["&", ",", "(", ";"]:
                        firstname = firstname[:-1].strip()
                    while len(lastname) > 0 and lastname[-1] in ["&", ",", "(", ";"]:
                        lastname = lastname[:-1].strip()
                    
                    if just_count == False:
                        new_author = author.Author(firstname=firstname, lastname=lastname)
                        ref.authors.append(new_author)
                        print(f"Adding: {new_author}")
                        if self.reference_style['bibref'] == "iso690":
                            ref.span_authors_end = re.search(author_string, ref.rawtext).end()
                            ref.span_title_start = ref.span_authors_end +1

                    author_splice = author_splice[author_match.end():].lstrip()
                    try:
                        if author_splice.split()[0] == "and":
                            author_splice = author_splice[3:].lstrip()
                        elif author_splice.split()[0] == "&":
                            author_splice = author_splice[1:].lstrip()
                    except IndexError:
                        pass # nothing more to parse
                    print(f"Remaining string to parse into authors: {author_splice}")
        except IndexError as e:
            print("IndexError when extracting authors from string")
            print(e)
        except AttributeError as e:
            print("AttributeError when extracting authors from string")
            print(e)
        
        except:
            e = sys.exc_info()[0]
            print(e) 

        # If no people names are found, assume the author is an institution, anonymous report, software etc.
        if number_of_authors == 0:
            # Assume the name ends with period and whitespace character. This might yield limited results
            # if name is of type "BIG INSTITUTION. Sub-department." etc. but we will still get BIG INSTITUTION.
            if self.reference_style['bibref'] == "apa":
                name_end = len(author_splice) - 1
            else:
                first_comma = re.search(r"\.\s", author_splice)
                name_end = first_comma.start()
                title_start = first_comma.end()

            author_splice = author_splice[:name_end].strip()
            while len(author_splice) > 0 and author_splice[-1] in ["&", ",", "(", ";"]:
                author_splice = author_splice[:-1]               
            
            if just_count == False:
                new_author = author.Author(non_person_author=author_splice.strip())
                ref.authors.append(new_author)
                print(f"Adding non-person-author: {new_author}")
                if self.reference_style['bibref'] == "iso690":
                    ref.span_authors_end = name_end
                    ref.span_title_start = title_start

        if just_count == True:
            return number_of_authors
           
    def extract_year(self, ref):
        """
        Extract publication year from reference text. Update reference year and year index span info
        """
        year_matcher = re.compile(r"(?:19|20)\d\d[abcdef]{0,1}")         
        if self.reference_style['bibref'] == "apa":
            try:
                year_position = re.search(year_matcher, ref.rawtext)
                ref.year = int(year_position.group()[:4])
                ref.span_year_start = year_position.start()
                ref.span_year_end = year_position.end()
                ref.span_authors_end = year_position.start()
                ref.span_title_start = ref.span_year_end +1
            except:
                print("Something went wrong extracting apa-year information. Returning with no success.")
                return -1

        elif self.reference_style['bibref'] == "iso690":
            try:
                year_positions = [r for r in re.finditer(year_matcher, ref.rawtext)]
                ref.year = int(year_positions[-1].group()[:4])
                ref.span_year_start = year_positions[-1].start()
                ref.span_year_end = year_positions[-1].end()
            except:
                e = sys.exc_info()[0]
                print(e)
                print("Something went wrong extracting iso690-year information. Returning with no success.")
                return -1
        else:
            print("No reference style info exists. Cannot realiably detect publication year")

    def extract_title(self, ref):
        """
        Extract title - or the first period-terminated part of the title from reference
        Requires author and year extraction first to detect the position of title start
        """
        if self.reference_style['semicolons']:
            separator = ";"
        else:
            separator = "."

        if isinstance(ref.span_title_start, int):
            # remove any whitespace or extra punctuation from title start
            start_of_title = ref.span_title_start
            start_unclear = True
            while start_unclear:
                if ref.rawtext[start_of_title].isalpha() or ref.rawtext[start_of_title].isnumeric():
                    start_unclear = False
                else:
                    if len(ref.rawtext) -1 <= start_of_title:
                        print("Title search reached end of string. Returning None.")
                        return None
                    else:
                        start_of_title += 1

            title = ref.rawtext[start_of_title:]
            title_end = title.find(separator)
            ref.title = title[:title_end]
            print(f"Found title: {ref.title}")

        else:
            print("The start of title index is not set. Not able to detect title")
            return None
 
