class Reference(object):
    def __init__(self, rawtext="", reference_style=None):
        self.rawtext = rawtext
        self.reference_style = reference_style
        self.title = ""
        self.authors = []
        self.pdffile = ""

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


