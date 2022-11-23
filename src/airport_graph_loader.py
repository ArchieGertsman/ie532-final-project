from itertools import product

import networkx as nx
import pandas as pd
import numpy as np

from .utils import *
        

'''API: load_dense and load_sparse'''

def load_dense(gate_pos_filename):
    G = _load_gate_graph(gate_pos_filename)

    # concourse A
    _connect_gates(G, 'WH', 'A1')
    _connect_gates(G, 'WH', 'A4A')
    _connect_group_in_series(G, ['A1', 'A2', 'A3', 'A5'])
    _connect_group_in_series(G, ['A4A', 'A4B'])
    _connect_group_fully(G, 
        ['A5', 'A7', 'A9', 'A10', 'A11', 'A12', 'A14', 'A15', 'A16', 'A17', 'A18', 'A19'])

    # concourse B
    _connect_gates(G, 'WH', 'B1')
    _connect_group_in_series(G, ['B1', 'B2', 'B3', 'B5'])
    _connect_group_fully(G, 
        ['B5', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12', 'B14', 'B15', 'B16', 'B17', 
            'B18', 'B19', 'B20', 'B21', 'B22', 'B23', 'B24', 'B25', 'B26'])

    # concourse C
    _connect_gates(G, 'WH', 'C1')
    _connect_group_fully(G, ['C1', 'C2', 'C3'])

    assert nx.is_connected(G)
    return G


def load_sparse(gate_pos_filename):
    G = _load_gate_graph(gate_pos_filename)

    # concourse A
    _connect_gates(G, 'WH', 'A1')
    _connect_group_in_series(G, ['WH', 'A4A', 'A4B'])
    _connect_group_in_series(G, ['A1', 'A2', 'A3', 'A5'])
    _connect_group_in_series(G, ['A5', 'A7', 'A9', 'A11', 'A15', 'A17'])
    _connect_group_in_series(G, ['A10', 'A12', 'A14', 'A16', 'A15', 'A17'])
    _connect_groups_accross(G, ['A9', 'A11', 'A14'], ['A10', 'A12', 'A15'])
    _connect_group_in_series(G, ['A15', 'A17', 'A19', 'A18', 'A16', 'A14'])
    _connect_gates(G, 'A7', 'A9')

    # concourse B
    _connect_gates(G, 'WH', 'B1')
    _connect_group_in_series(G, ['B1', 'B2', 'B3', 'B5'])
    _connect_gates(G, 'B5', 'B7')
    group1 = ['B7', 'B9', 'B11', 'B15', 'B17', 'B19', 'B21']
    group2 = ['B8', 'B10', 'B12', 'B16', 'B18', 'B20', 'B22']
    _connect_group_in_series(G, group1)
    _connect_group_in_series(G, group2)
    _connect_groups_accross(G, group1, group2)
    _connect_group_fully(G, ['B14', 'B15', 'B16'])
    _connect_group_in_series(G, ['B21', 'B23', 'B25', 'B26', 'B24', 'B22'])

    # concourse C
    _connect_gates(G, 'WH', 'C1')
    _connect_group_fully(G, ['C1', 'C2', 'C3'])

    assert nx.is_connected(G)
    return G



'''helper functions'''

def _load_gate_graph(gate_pos_filename):
    '''add gates to graph as nodes, reading node positions
    from csv named `gate_pos_filename`'''
    G = nx.Graph() # direction does not matter for gate transport
    df = pd.read_csv(gate_pos_filename, index_col='gate')
    for terminal, (x,y) in df.iterrows():
        G.add_node(terminal, pos=(x,y))
        G.add_edge(terminal, terminal, weight=0)
    return G


def _euclidean(G, gate1, gate2):
    x1, y1 = G.nodes[gate1]['pos']
    x2, y2 = G.nodes[gate2]['pos']
    return np.sqrt((x1-x2)**2 + (y1-y2)**2) 


def _connect_gates(G, gate1, gate2):
    G.add_edge(gate1, gate2, weight=_euclidean(G, gate1, gate2))


def _add_edges_euclidean(G, gate_pairs):
    G.add_weighted_edges_from((
        (gate1, gate2, _euclidean(G, gate1, gate2))
        for gate1, gate2 in gate_pairs
    ))


def _connect_group_in_series(G, group):
    _add_edges_euclidean(G, zip(group[:-1], group[1:]))


def _connect_group_fully(G, group):
    _add_edges_euclidean(G, ((gate1, gate2) 
        for gate1, gate2 in product(group, group) 
        if gate1 != gate2
    ))


def _connect_groups_accross(G, group1, group2):
    assert len(group1) == len(group2)
    _add_edges_euclidean(G, zip(group1, group2))