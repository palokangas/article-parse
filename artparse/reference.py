from difflib import SequenceMatcher
from unicodedata import normalize, name
import sys

class Reference(object):
    def __init__(self, rawtext="", reference_style=None):
        self.rawtext = rawtext
        self.reference_style = reference_style
        self.title = ""
        self.authors = []
        self.pdffile = ""
        self.year = None
        # Store references span tuples especially for implementing interactive fixing of complicated references
        self.span_authors = ()
        self.span_title = ()
        self.span_year = ()
        self.span_journal = ()

    def __len__(self):
        return len(self.rawtext)
    
    def __str__(self):
        return self.rawtext

    def add_author(self, author):
        """ Add author to list of authors for this reference. If author (name matching) already exists, return -1"""
        if str(author) not in [str(a) for a in self.authors]:
            self.authors.append(author)
        else:
            print("This author already exists in authors for this reference")
            return -1   ## TODO: Convert this to custom Exception

    def get_normalized_authors(self):
        author_string = ""
        # If this reference only has a non-person author
        if len(self.authors) == 1 and self.authors[0].is_person_author == False:
            return self.authors[0].non_person_author

        # If we have person authors(s)
        for aut in self.authors:
            author_string += aut.lastname + ', ' + aut.firstname + " ;"
        author_string = author_string[:-2]
        return author_string

    # def title_matching_sequence_len(self, this_title, other_title):
    #     """Return the length of matching sequences between two titles"""
    #     sequence_matches = SequenceMatcher(lambda x: x == " ", this_title, other_title).get_matching_blocks()
    #     longest_match = 0
    #     for seq_match in sequence_matches:
    #         if seq_match[2] > longest_match:
    #             longest_match = seq_match[2]
    #     return longest_match

    # # TODO: Convert this to return match score, for example between 0 and 1
    # def authors_matches(self, this_author, other_author):
    #     if this_author is None or other_author is None:
    #         return None
        
    #     #this_author = re.sub(r"\s", "", this_author.lower())
    #     #other_author = re.sub(r"\s", "", other_author.lower())
    #     similarity_score = SequenceMatcher(lambda x: x == " ", this_author, other_author).ratio()
    #     if similarity_score == 1:
    #         print("Authors have full match.")
    #         authors_match = True
    #     elif similarity_score > 0.8:
    #         author1_ascii = normalize('NFD', this_author).encode('ascii', 'ignore').decode('utf8')    
    #         author2_ascii = normalize('NFD', other_author).encode('ascii', 'ignore').decode('utf8')    
    #         similarity_ascii = SequenceMatcher(lambda x: x == " ", author1_ascii, author2_ascii).ratio()
    #         if similarity_ascii == 1:
    #             print("Authors have match when normalized to ascii.")
    #             authors_match = True
    #         else:
    #             print("Authors do not match on utf or ascii level.")
    #             authors_match = False
    #     else:
    #         print("Authors do not match.")
    #         return False
    #     return authors_match


    # def year_matches(self, this_year, other_year):
    #     if this_year != other_year:
    #         print("Year does not match. Returning false")
    #         return False
    #     else:
    #         print("Year matches")
    #         return True


    # # TODO: Refactor this to return binary match/unmatch AND uncertain matches for interactive use
    # def is_same(self, comparison):
    #     """
    #     Checks whether the comparison reference is the same as this one.
    #     Comparison based on publication year, names and title
    #     For now, only return True or False
    #     """
    #     try:
    #         year_match = self.year_matches(self.year, comparison.year)
    #         if year_match == False or year_match is None:
    #             return year_match

    #         # authors_match = self.authors_matches(self.get_normalized_authors(), comparison.get_normalized_authors())
    #         # if authors_match == False or authors_match is None:
    #         #     return authors_match
            
    #         # If authors and years match, the match is highly likely
    #         # Since titles can contain only partial information, even a partial substring match
    #         # Likely means that the references are the same
    #         match_length = self.title_matching_sequence_len(self.title, comparison.title)
    #         shortest_title = len(self.title) if len(self.title) < len(comparison.title) else len(comparison.title)
    #         if shortest_title > 9 and match_length / shortest_title > 0.9:
    #             print("Title matches.")
    #             return True
    #         else:
    #             print("Title does not match.")
    #             return False

    #     except TypeError as e:
    #         print(e)
    #     except NameError as e:
    #         print(e)
    #     except:
    #         e = sys.exc_info()[0]
    #         print(e)
    #         print("Cannot make comparison. Returning None")
    #         return None

        #SequenceMatcher(None, line1, line2).ratio())

