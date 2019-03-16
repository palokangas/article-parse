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