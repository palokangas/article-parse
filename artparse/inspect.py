import sys,re
import pdftotext
from collections import defaultdict
from difflib import SequenceMatcher


def get_years_per_page(pdf):
    """
        Finds possible publication years (1800-2099) from pages
        param: pdftotext.PDF object
        returns: list of  
    """
    years_per_page = []
    for page in pdf:
        years_per_page.append(re.findall(r"[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;]"))

    return years_per_page


def detect_columns(pdf):

    """
    param: pdftools.PDF object
    return: a list with 2:n column start values for pages
            note: value of 0 indicates a 1 column layout
    """

    second_columns_start_indexes = []

    for page in pdf:

        spaces = defaultdict(int)
        rows = 0
        for row in page.splitlines():
            rows += 1
            for position in [pos.start(0) for pos in re.finditer(r" ", row)]:
                
                # exclude possible left margin
                if position < len(row)/2:
                    if row[:position].isspace:
                        continue
                elif position > len(row)/2:
                    if row[position:].isspace:
                        continue

                #if len(row) > 40 and position.start(0) > 19 and position.start(0) < len(row) - 19:
                spaces[position] += 1

        #print(f"{max(spaces.values())} / {rows} = {max(spaces.values()) / rows}")
        if max(spaces.values()) / rows < 0.51:
            second_columns_start_indexes.append(0)
            continue

        highest_space_nr = 0
        index_of_second_column = 0
        for position, value in sorted(spaces.items()):
            if value >= highest_space_nr:
                highest_space_nr = value
                index_of_second_column = position
        index_of_second_column += 1

        second_columns_start_indexes.append(index_of_second_column)
        
        #for position, value in sorted(spaces.items()):
        #    print("pos: {}, {}".format(position, value)), 
        #print("---")

    return second_columns_start_indexes


def detect_header_footer(pdf_object):
    """
        Detects header and footer lines from pdf_object
        param1: pdftotext.PDF-object
        return: list of ints: header lines (positive ints) and footer lines (negative ints)
    """

    headers_and_footers = []
    line_to_investigate = 0

    if len(pdf_object) < 2:
        print("There should be at least 2 pages to identify header and footer by similarity.")
        return headers_and_footers

    while line_to_investigate != "stop":

        lines_to_compare = []    
        for page in pdf_object:
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
            headers_and_footers.append(line_to_investigate)

            if line_to_investigate >= 0:
                line_to_investigate += 1
            else:
                line_to_investigate -= 1
        else:
            if line_to_investigate >= 0:
                line_to_investigate = -1
            else:
                line_to_investigate = "stop"
    
    return headers_and_footers


def detect_reference_style(reference_text):

    """
        returns a regular expression object for matching from first author to year
    """
    reference_lines = reference_text.splitlines()
    #reference_lines[0] = re.sub(r"(=?\n|\n.+)references", "", reference_lines[0], re.IGNORECASE)
    #del reference_lines[0]   # delete the headline "references"
    #print(f"The first line is now: {reference_lines[0]}")

    for line in reference_lines:
        try:
            print("Trying to detect ref style based on this line:")
            print(line)
            match_year = re.search(r"\s*[A-ZÅÄÖØÆ].+[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;]", line)
            print(match_year.string)
            print(match_year.groups())
            left_paren = line[match_year.regs[1][0] - 1]
            right_paren = line[match_year.regs[1][1]]
            if left_paren == '(' and right_paren == ')':
                return re.compile(r"\s*([A-ZÅÄÖØÆ].+\((?:19|20)\d\d\))")
            else:
                return re.compile(r"\s*([A-ZÅÄÖØÆ].+[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;])")
        except:
            print("Ignoring a non-reference line")

def detect_reference_start_index(pdftext):

    reference_regexes = [r"(?:\n|\n\s+|\n.*\s+)(references)",           # Title: References
                         r"(?:\n|\n\s+|\n.*\s+)(literature cited)"]     # Title: Literature cited
    potential_reference_starts = []

    for title_wording in reference_regexes:
        potential_reference_starts += [r.start() for r in re.finditer(title_wording, pdftext, re.IGNORECASE)]
        
    if len(potential_reference_starts) == 0:
        return 0
    elif len(potential_reference_starts) == 1:
        return potential_reference_starts[0]
    else:
        print("There were more than one probable reference section. Detecting the most probable one.")
        most_probable_start_point = 0
        most_year_mentions = 0
        for test_start in potential_reference_starts:
            test_text = pdftext[test_start:test_start+1000]
            nr_year_mentions = len(re.findall(r"[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;]", test_text))
            print(f"Position {test_start} is followed by {nr_year_mentions} year mentions.")
            if nr_year_mentions > most_year_mentions:
                most_probable_start_point = test_start
                most_year_mentions = nr_year_mentions
        return most_probable_start_point


