from .__init__ import Item

class StuffList(Item):
    def __init__(self, name="Untitled", description=""):
        super().__init__(name, description)
        # content存储的是Paragraph对象或其他Item对象的列表
        
    def __repr__(self):
        return f"StuffList(name='{self.name}', item_count={len(self.content)})"
