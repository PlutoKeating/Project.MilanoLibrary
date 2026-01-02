from .__init__ import Item

class RelationGraph(Item):
    def __init__(self, name="Untitled", description=""):
        super().__init__(name, description)
        self._nodes = []
        self._edges = []
        
    @property
    def nodes(self):
        return self._nodes
        
    @property
    def edges(self):
        return self._edges
        
    def add_node(self, node):
        if node not in self._nodes:
            self._nodes.append(node)
        
    def add_edge(self, source_node, target_node, relation_type):
        if source_node not in self._nodes:
            self._nodes.append(source_node)
        if target_node not in self._nodes:
            self._nodes.append(target_node)
        
        self._edges.append((source_node, target_node, relation_type))
        
    def get_related_nodes(self, node, relation_type=None):
        related = []
        for source, target, rel_type in self._edges:
            if source == node:
                if relation_type is None or rel_type == relation_type:
                    related.append((target, rel_type))
            elif target == node:
                if relation_type is None or rel_type == relation_type:
                    related.append((source, rel_type))
        return related
        
    def __repr__(self):
        return f"RelationGraph(name='{self.name}', nodes={len(self._nodes)}, edges={len(self._edges)})"
