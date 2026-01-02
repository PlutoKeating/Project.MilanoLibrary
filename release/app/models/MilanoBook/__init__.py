class Paragraph:
    def __init__(self, start_time, end_time, text_content, multi_modal_data=None):
        self.start_time = start_time
        self.end_time = end_time
        self.text_content = text_content
        self.multi_modal_data = multi_modal_data or {}
        
    def __repr__(self):
        return f"Paragraph(start_time={self.start_time}, end_time={self.end_time}, text_content='{self.text_content[:50]}...')"

class MilanoBook:
    def __init__(self, title="Untitled", author="Unknown", source_url=""):
        self.title = title
        self.author = author
        self.source_url = source_url
        self._paragraphs = []
        self._items = []
        
    @property
    def paragraphs(self):
        return self._paragraphs
        
    @property
    def items(self):
        return self._items
        
    def add_paragraph(self, paragraph):
        self._paragraphs.append(paragraph)
        
    def add_item(self, item):
        self._items.append(item)
        
    def get_paragraphs_by_time(self, start_time, end_time):
        return [p for p in self._paragraphs if not (p.end_time < start_time or p.start_time > end_time)]
        
    def __repr__(self):
        return f"MilanoBook(title='{self.title}', author='{self.author}', paragraphs={len(self._paragraphs)}, items={len(self._items)})"


