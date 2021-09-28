

class PRContent:
    
    def __init__(self, title: str =None, message: str =None, content: str = None, file: str =None):
        self.title = title
        self.message = message

        if content:
            self._init_from_content(content)
        elif file:
            with open(file, "r+") as f:
                self._init_from_content(f.read())

    def _init_from_content(self, content: str):
        self.title, _, self.message  = content.strip(" ").partition("\n")

    def __str__(self):
        return self.title + "\n\n" + self.message