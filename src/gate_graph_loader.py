import networkx as nx
import pandas as pd
import numpy as np
import pandas as pd

from .utils import *


class GateGraphLoader:
    def __init__(self, gate_pos_filename):
        self._setup_gate_graph(gate_pos_filename)


    def _setup_gate_graph(self, gate_pos_filename):
        self.G = nx.Graph() # direction does not matter for gate transport
        df = pd.read_csv(gate_pos_filename, index_col='gate')
        for terminal, (x,y) in df.iterrows():
            self.G.add_node(terminal, pos=(x,y))
            

    def create_dense(self):
        G = self.G.copy()

        # concourse A
        add_edge_euclidean(G, 'WH', 'A1')
        add_edge_euclidean(G, 'WH', 'A4A')
        connect_group_in_series(G, ['A1', 'A2', 'A3', 'A5'])
        connect_group_fully(G, ['A5', 'A7', 'A9', 'A10', 'A11', 'A12', 'A14', 'A15', 'A16', 'A17', 'A18', 'A19'])
        connect_group_in_series(G, ['A4A', 'A4B'])

        # concourse B
        add_edge_euclidean(G, 'WH', 'B1')
        connect_group_in_series(G, ['B1', 'B2', 'B3', 'B5'])
        connect_group_fully(G, ['B5', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12', 'B14', 'B15', 'B16', 'B17', 'B18', 'B19',
               'B20', 'B21', 'B22', 'B23', 'B24', 'B25', 'B26'])

        # concourse C
        add_edge_euclidean(G, 'WH', 'C1')
        connect_group_fully(G, ['C1', 'C2', 'C3'])
        
        return G


    def create_sparse(self):
        G = self.G.copy()

        # concourse A
        add_edge_euclidean(G, 'WH', 'A1')
        connect_group_in_series(G, ['WH', 'A4A', 'A4B'])
        connect_group_in_series(G, ['A1', 'A2', 'A3', 'A5'])
        connect_group_in_series(G, ['A5', 'A7', 'A9', 'A11', 'A15', 'A17'])
        connect_group_in_series(G, ['A10', 'A12', 'A14', 'A16', 'A15', 'A17'])
        connect_groups_accross(G, ['A9', 'A11', 'A14'], ['A10', 'A12', 'A15'])
        connect_group_in_series(G, ['A15', 'A17', 'A19', 'A18', 'A16', 'A14'])
        add_edge_euclidean(G, 'A7', 'A9')

        # concourse B
        add_edge_euclidean(G, 'WH', 'B1')
        connect_group_in_series(G, ['B1', 'B2', 'B3', 'B5'])
        add_edge_euclidean(G, 'B5', 'B7')
        group1 = ['B7', 'B9', 'B11', 'B15', 'B17', 'B19', 'B21']
        group2 = ['B8', 'B10', 'B12', 'B16', 'B18', 'B20', 'B22']
        connect_group_in_series(G, group1)
        connect_group_in_series(G, group2)
        connect_groups_accross(G, group1, group2)
        connect_group_fully(G, ['B14', 'B15', 'B16'])
        connect_group_in_series(G, ['B21', 'B23', 'B25', 'B26', 'B24', 'B22'])

        # concourse C
        add_edge_euclidean(G, 'WH', 'C1')
        connect_group_fully(G, ['C1', 'C2', 'C3'])

        return G