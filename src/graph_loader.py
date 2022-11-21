import networkx as nx
import pandas as pd
import numpy as np
import pandas as pd

from .utils import *


class GraphLoader:

    def __init__(self, gate_pos_filename):
        self._setup_gates_graph(gate_pos_filename)


    def _setup_gates_graph(self, gate_pos_filename):
        self.G = nx.Graph() # direction does not matter for gate transport
        df = pd.read_csv(gate_pos_filename, index_col='gate')
        for terminal, (x,y) in df.iterrows():
            self.G.add_node(terminal, pos=(x,y))
            

    def create_dense(self):
        G = self.G.copy()

        group_1 = ['A1', 'A2', 'A3', 'A5']
        group_2 = ['A5', 'A7', 'A9', 'A10', 'A11', 'A12', 'A14', 'A15', 'A16', 'A17', 'A18', 'A19']
        group_3 = ['A4A', 'A4B']
        group_4 = ['B1', 'B2', 'B3', 'B5']
        group_5 = ['B5', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12', 'B14', 'B15', 'B16', 'B17', 'B18', 'B19',
               'B20', 'B21', 'B22', 'B23', 'B24', 'B25', 'B26']
        group_6 = ['C1', 'C2', 'C3']

        connect_group_in_series(G, group_1)
        connect_group_fully(G, group_2)
        connect_group_in_series(G, group_3)
        connect_group_in_series(G, group_4)
        connect_group_fully(G, group_5)
        connect_group_fully(G, group_6)

        G.add_edge('WH', 'A1', length=euclidean(G, 'WH', 'A1'))
        G.add_edge('WH', 'A4A', length=euclidean(G, 'WH', 'A4A'))
        G.add_edge('WH', 'B1', length=euclidean(G, 'WH', 'B1'))
        G.add_edge('WH', 'C1', length=euclidean(G, 'WH', 'C1'))

        return G