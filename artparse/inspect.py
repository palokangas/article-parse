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

def detect_margins(page):
    
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

def detect_columns(pdf):

    """
    param: pdftools.PDF object
    return: a list with 2:n column start values for pages
            note: value of 0 indicates a 1 column layout
    """

    second_columns_start_indexes = []

    for page in pdf:
        left_margin, right_margin = detect_margins(page)

        spaces = defaultdict(int)
        rows = 0
        for row in page.splitlines():
            rows += 1
            for space_location in re.finditer(r" ", row):
                position = space_location.start(0)

                #if len(row) > 40 and position > 19 and position < len(row) - 19:
                if position >= left_margin or position <= right_margin:
                    spaces[position] += 1

        print(f"{max(spaces.values())} / {rows} = {max(spaces.values()) / rows}")
        if max(spaces.values()) / rows < 0.61:
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
    header_lines = 0
    footer_lines = 0
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
    
    return (header_lines, footer_lines)


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

            ## Does not work because there can be references 2016a, 2016b etc...
            ## Switched temporarily to not return parentheses search even though it is more accurate....
            match_year = re.search(r"\s*[A-ZÅÄÖØÆ].+[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;]", line)
            #match_year = re.search(r"\s*[A-ZÅÄÖØÆ].+[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;]", line)
            print(match_year.string)
            print(match_year.groups())
            left_paren = line[match_year.regs[1][0] - 1]
            right_paren = line[match_year.regs[1][1]]
            if left_paren == '(' and right_paren == ')':
                #return re.compile(r"\s*([A-ZÅÄÖØÆ].+\((?:19|20)\d\d\))")
                return re.compile(r"\s*([A-ZÅÄÖØÆ].+[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;abcdef])")
            else:
                return re.compile(r"\s*([A-ZÅÄÖØÆ].+[\s\(\.,;]((?:19|20)\d\d)[\s\)\.,;abcdef])")
        except:
            print("Ignoring a non-reference line")

def detect_reference_start_index(pdftext):

    references_start_index = 0
    #reference_regexes = [r"(?:\n|\n\s+|\n.*\s+)(references)",           # Title: References
    #                     r"(?:\n|\n\s+|\n.*\s+)(literature cited)"]     # Title: Literature cited
    reference_regexes = [r"references.*(\n)",           # Title: References
                         r"literature cited.*(\n)"]     # Title: Literature cited                         
    potential_reference_starts = []

    for title_wording in reference_regexes:
        potential_reference_starts += [r.start(1) + 1 for r in re.finditer(title_wording, pdftext, re.IGNORECASE)]

    print(f"There are {len(potential_reference_starts)} potential reference start points")

    if len(potential_reference_starts) == 0:
        return 0
    elif len(potential_reference_starts) == 1:
        references_start_index = potential_reference_starts[0]
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
        references_start_index = most_probable_start_point

    return references_start_index

