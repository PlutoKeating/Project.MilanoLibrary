class Item:
    def __init__(self, name="Untitled", description=""):
        self.name = name
        self.description = description
        self._content = []
        
    @property
    def content(self):
        return self._content
        
    def add_content(self, content):
        self._content.append(content)
        
    def __repr__(self):
        return f"Item(name='{self.name}', content_count={len(self._content)})"
