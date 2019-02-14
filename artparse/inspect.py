import re, pdftotext
from collections import defaultdict
from difflib import SequenceMatcher

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
            for position in re.finditer(r" ", row):
                # exclude possible margins
                if len(row) > 20 and position.start(0) > 19 and position.start(0) < len(row) - 19:
                        spaces[position.start(0)] += 1

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
    del reference_lines[0]   # delete the headline "references"

    for line in reference_lines:
        if line.isspace():
            print("Ignoring empty line")
        else:
            match_year = re.search(r"\s*[A-ZÅÄÖØÆ].+([12][09]\d\d)\D", line)
            print(match_year.string)
            left_paren = line[match_year.regs[1][0] - 1]
            right_paren = line[match_year.regs[1][1]]
            if left_paren == '(' and right_paren == ')':
                return re.compile(r"\n\s*([A-ZÅÄÖØÆ].+[12][09]\d\d\))")
            else:
                return re.compile(r"\n\s*([A-ZÅÄÖØÆ].+[12][09]\d\d)")

