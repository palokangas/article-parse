class Author(object):
    def __init__(self,  firstname="", lastname=""):
        self.firstname = firstname
        self.lastname = lastname
    
    def __str__(self):
        try:
            return self.lastname + ", " + self.firstname[0]
        except:
            print("Author name fields are missing values. Returning empty string")
            return ""

    def get_author_with_initials(self):
        return self

    def get_author_fullname(self):
        try:
            return self.lastname + ", " + self.firstname
        except:
            print("Author name fields are missing values. Returning empty string")
            return ""