class Author(object):
    def __init__(self,  firstname=None, lastname=None, non_person_author=None):
        self.firstname = firstname
        self.lastname = lastname
        self.non_person_author = non_person_author
        if self.firstname is None and self.lastname is None and self.non_person_author:
            self.is_person_author = False
        elif self.firstname and self.lastname and self.non_person_author is None:
            self.is_person_author = True
        else:
            self.is_person_author = None

    def __str__(self):
        if self.is_person_author:
            try:
                return self.lastname + ", " + self.firstname
            except:
                print("Author name fields are missing values. Returning empty string")
                return ""
        elif self.is_person_author == False:
            try:
                return self.non_person_author
            except TypeError:
                print("Author name fields are missing values. Returning empty string")
                return ""
        else:          
            print("Missing author information")
            return ""

    def get_author_fullname(self):
        return self

    # TODO: Make this more fuzzy, ie. strip umlauts, check for full firstnames vs. initials etc.
    def is_same(self, comparison):
        they_match = False
        if self.is_person_author and comparison.is_person_author:
            if self.lastname == comparison.lastname and self.firstname == comparison.firstname:
                they_match = True
        elif self.is_person_author == False and comparison.is_person_author == False:
            if self.non_person_author == comparison.non_person_author:
                they_match = True
        else:
            they_match = False       
        return they_match
