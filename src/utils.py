from itertools import product

import numpy as np
import networkx as nx

def euclidean(G, gate1, gate2):
    x1, y1 = G.nodes[gate1]['pos']
    x2, y2 = G.nodes[gate2]['pos']
    return np.sqrt((x1-x2)**2 + (y1-y2)**2) 


def connect_gates(G, gate1, gate2):
    G.add_edge(gate1, gate2, weight=euclidean(G, gate1, gate2))


def add_edges_euclidean(G, gate_pairs):
    G.add_weighted_edges_from((
        (gate1, gate2, euclidean(G, gate1, gate2))
        for gate1, gate2 in gate_pairs
    ))


def connect_group_in_series(G, group):
    add_edges_euclidean(G, zip(group[:-1], group[1:]))


def connect_group_fully(G, group):
    add_edges_euclidean(G, ((gate1, gate2) 
        for gate1, gate2 in product(group, group) 
        if gate1 != gate2
    ))


def connect_groups_accross(G, group1, group2):
    assert len(group1) == len(group2)
    add_edges_euclidean(G, zip(group1, group2))