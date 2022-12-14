import networkx as nx
import numpy as np
from itertools import product


'''API: generate_flight_schedule_graph'''

def generate_flight_schedule_graph(
    G_airport, 
    n_inbound, 
    n_outbound, 
    pace=54.4804182335, 
    mean_connecting_wait_time=.5,
    geom_p=.9
):
    '''generates a graph where nodes are flights and edges
    represent flight connections. Node attributes include
    gate and flight time, and edges store the time to
    escort between connecting flight gates
    '''
    G_schedule = nx.DiGraph()

    inbound_flights = _generate_flights(
        G_schedule, 
        G_airport, 
        n_inbound, 
        lambda i: f'in_{i+1}')

    outbound_flights = _generate_flights(
        G_schedule, 
        G_airport, 
        n_outbound, 
        lambda i: f'out_{i+1}')

    _generate_forward_connections(
        G_schedule, 
        G_airport, 
        inbound_flights, 
        outbound_flights, 
        pace,
        geom_p)

    _adjust_flight_times(
        G_schedule, 
        mean_connecting_wait_time)

    _generate_backward_connections(
        G_airport, 
        G_schedule, 
        inbound_flights, 
        outbound_flights, 
        pace)

    return G_schedule, inbound_flights, outbound_flights



'''helper functions'''

# we will call units in our coordinate system Scaled Airport Distance (SAD)
# 1 SAD = 242.288888889 ft
# pace units are in s^{-1}
# 1 unit of pace = 2.5 mph
# SAD / PACE = time in hours

def _generate_flights(
    G_schedule, 
    G_airport, 
    n_flights, 
    name_func
):
    '''generates `n_flights` flights with randomly selected gates
    and flight times sampled according to a Poisson process (i.e.
    uniformly distributed within the 0-24 hour range)
    '''
    flight_names = [name_func(i) for i in range(n_flights)]
    gates = np.random.choice(G_airport, n_flights)
    flight_times = np.random.uniform(0, 24, (n_flights,)) # Poisson process
    G_schedule.add_nodes_from((
        (name, {'gate': gate, 't': time})
        for name, gate, time in zip(flight_names, gates, flight_times)
    ))
    return flight_names



def _generate_forward_connections(
    G_schedule, 
    G_airport, 
    inbound_flights, 
    outbound_flights, 
    pace,
    geom_p
):
    '''randomly matches `n_connecting` pairs of inbound and outbound flights,
    adding an edge with attribute `t_escort`, the time to escort from the
    inbound gate to the outbound gate
    '''
    for in_flight, out_flight in product(inbound_flights, outbound_flights):
        in_gate = G_schedule.nodes[in_flight]['gate']
        out_gate = G_schedule.nodes[out_flight]['gate']
        if in_gate == out_gate:
            continue

        wheelchair_demand = np.random.geometric(geom_p) - 1
        if wheelchair_demand == 0:
            continue

        dist = nx.shortest_path_length(G_airport, in_gate, out_gate, weight='weight')
        t_escort = dist / pace

        G_schedule.add_edge(
            in_flight, 
            out_flight, 
            capacity=wheelchair_demand, 
            weight=-1, 
            t_escort=t_escort)



def _adjust_flight_times(
    G_schedule, 
    mean_connecting_wait_time
):
    '''for each outbound flight that is part of a connection, 
    set its departure time to be 
        `t_departure = t_arrival + t_escort + X`, 
    where
    - t_arrival is the arrival time of the inbound flight that's 
        the other part of the connection
    - t_escort is the time it takes to escort from the inbound 
        gate to the outbound gate
    - X ~ exponential(`mean_connecting_wait_time`).
    The first two terms make `t_departure` feasible, and `X` makes 
    it more realistic. If `t_arrival` and `t_departure` are then
    both shifted to fit within the 0-24 hour range.
    '''
    for in_flight, out_flight in G_schedule.edges:
        t_arrival = G_schedule.nodes[in_flight]['t']
        t_departure = G_schedule.nodes[out_flight]['t']
        t_escort = G_schedule[in_flight][out_flight]['t_escort']

        t_departure_new = t_arrival + t_escort + np.random.exponential(mean_connecting_wait_time)
        t_departure = max(t_departure, t_departure_new)

        if t_departure >= 24:
            # shift flight times to fit in 0-24 time
            delta = t_departure - 24
            t_arrival -= delta
            t_departure -= delta

        G_schedule.nodes[in_flight]['t'] = t_arrival
        G_schedule.nodes[out_flight]['t'] = t_departure



def _generate_backward_connections(
    G_airport, 
    G_schedule, 
    inbound_flights, 
    outbound_flights, 
    pace
):
    for in_flight, out_flight in product(inbound_flights, outbound_flights):
        t_arrival = G_schedule.nodes[in_flight]['t']
        in_gate = G_schedule.nodes[in_flight]['gate']

        t_departure = G_schedule.nodes[out_flight]['t']
        out_gate = G_schedule.nodes[out_flight]['gate']

        dist = nx.shortest_path_length(G_airport, out_gate, in_gate, weight='weight')
        t_escort = dist / pace

        if t_arrival > t_departure + t_escort:
            G_schedule.add_edge(out_flight, in_flight, weight=-1)