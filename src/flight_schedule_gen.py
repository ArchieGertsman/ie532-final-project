import networkx as nx
import numpy as np


'''API: generate_flight_schedule_graph'''

def generate_flight_schedule_graph(
    G_airport, 
    n_inbound, 
    n_outbound, 
    n_connecting, 
    pace=54.4804182335, 
    mean_connecting_wait_time=.5
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

    in_connecting, out_connecting = _generate_connections(
        G_schedule, 
        G_airport, 
        n_connecting, 
        inbound_flights, 
        outbound_flights, 
        pace)

    _adjust_flight_times(
        G_schedule, 
        in_connecting, 
        out_connecting, 
        mean_connecting_wait_time)

    return G_schedule, inbound_flights



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


def _generate_connections(
    G_schedule, 
    G_airport, 
    n_connecting, 
    inbound_flights, 
    outbound_flights, 
    pace
):
    '''randomly matches `n_connecting` pairs of inbound and outbound flights,
    adding an edge with attribute `t_escort`, the time to escort from the
    inbound gate to the outbound gate
    '''
    assert n_connecting <= min(len(inbound_flights), len(outbound_flights))

    in_connecting = np.random.choice(inbound_flights, n_connecting, replace=False)
    out_connecting = np.random.choice(outbound_flights, n_connecting, replace=False)

    for in_flight, out_flight in zip(in_connecting, out_connecting):
        in_gate = G_schedule.nodes[in_flight]['gate']
        out_gate = G_schedule.nodes[out_flight]['gate']
        dist = nx.shortest_path_length(G_airport, in_gate, out_gate, weight='weight')
        t_escort = dist / pace
        G_schedule.add_edge(in_flight, out_flight, t_escort=t_escort)

    return in_connecting, out_connecting


def _adjust_flight_times(
    G_schedule, 
    in_connecting, 
    out_connecting, 
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
    for in_flight, out_flight in zip(in_connecting, out_connecting):
        t_arrival = G_schedule.nodes[in_flight]['t']
        t_escort = G_schedule[in_flight][out_flight]['t_escort']

        t_departure = t_arrival + t_escort + np.random.exponential(mean_connecting_wait_time)

        if t_departure >= 24:
            # shift flight times to fit in 0-24 time
            delta = t_departure - 24
            t_arrival -= delta
            t_departure -= delta

        G_schedule.nodes[in_flight]['t'] = t_arrival
        G_schedule.nodes[out_flight]['t'] = t_departure
