import re

def indentation_parse(reference_string):
    """
    Parses the references string assuming references are separated by indendation
    Param1: reference section of an article as string
    Returns a list of detected references as strings
    """

    ending_indicators = [r"suggested citation", r"would like to thank",
                         r"this article is", r"further reading", r"this article has been", 
                         ]

    MAX_LINES = 6     # MAX_LINES = how many consecutive lines with no indendation to tolerate before breaking
    references = []
    current_reference = ""
    start_lines = 0

    for row in reference_string.splitlines():
        if len(row) == 0 or row.isspace():
            pass
        elif len(row) > 0 and row[0].isspace():
            current_reference += " " + row
            start_lines = 0
        else:
            if len(current_reference) != 0:
                current_reference = trim_numbering(current_reference)
                current_reference = re.sub(r"\s+", " ", current_reference)

                ### Check for possible indicators of this being reference section end
                end_now = False
                for ending in ending_indicators:
                    if len(re.findall(ending, current_reference, re.IGNORECASE)):
                        end_now = True
                if end_now == True:
                    break
                references.append(current_reference)
            current_reference = row
            start_lines += 1
            if start_lines > MAX_LINES:
                break
    
    current_reference = trim_numbering(current_reference)
    current_reference = re.sub(r"\s+", " ", current_reference)
    references.append(current_reference)

    # Try detect if the last reference is actually a reference 
    last_unclear = True
    while last_unclear == True:
        if len(re.findall(r"(?:19|20)\d\d", references[-1])) == 0:
            print("Deleting trailing text that does not seem to be a refernce:")
            print(references[-1])
            del references[-1]
        else:
            last_unclear = False

    return references

def trim_numbering(reference):
    """
    Detects and trims numbering from reference, return trimmed version
    """
    reference = re.sub(r"^\d+", "", reference)
    reference = re.sub(r"^\.", "", reference)
    reference = re.sub(r"^\s", "", reference)
    return reference
