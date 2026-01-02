from .__init__ import Item

class Timeline(Item):
    def __init__(self, name="Untitled", description=""):
        super().__init__(name, description)
        self._content = []
        
    @property
    def content(self):
        return self._content
        
    def add_timeline_item(self, time_point, item):
        self._content.append((time_point, item))
        self._content.sort(key=lambda x: x[0])
        
    def get_items_by_time_range(self, start_time, end_time):
        return [item for time_point, item in self._content if start_time <= time_point <= end_time]
        
    def __repr__(self):
        return f"Timeline(name='{self.name}', item_count={len(self._content)})"
