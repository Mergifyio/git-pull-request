

class PRContent:
    
    def __init__(self, title: str ="", body: str ="", content: str = "", file: str =""):
        self.title = title
        self.body = body

        if content:
            self._init_from_content(content)
        elif file:
            with open(file, "r+") as f:
                self._init_from_content(f.read())

    def _init_from_content(self, content: str):
        self.title, _, self.body  = content.strip("\n ").partition("\n")
        self.title = self.title.strip("\n")
        self.body = self.body.strip("\n")
        
    def fill_empty(self, other: "PRContent"):
        if not self.title:
            self.title = other.title
        if not self.body:
            self.body = other.body
        return self

    def __str__(self):
        return self.title + "\n\n" + self.body + "\n"
    
    def __bool__(self):
        return all([self.__dict__[attr] for attr in self.__dict__.keys()])

    def write_to_file(self, fn):
        with open(fn, "w") as f:
            f.write(self.__str__().encode("utf-8"))


