import networkx as nx
import numpy as np
from itertools import product


'''API: generate_flight_schedule_graph'''

class FlightScheduleGen():

    def __init__(self,
        G_airport, 
        n_flights_in, 
        n_flights_out, 
        pace=54.4804182335, 
        mean_connecting_wait_time=.5,
        p_geom_connect=.9,
        p_geom_external=.1
    ):

        # we will call units in our coordinate system Scaled Airport Distance (SAD)
        # 1 SAD = 242.288888889 ft
        # pace units are in s^{-1}
        # 1 unit of pace = 2.5 mph
        # SAD / PACE = time in hours

        self.G_airport = G_airport
        self.n_flights_in = n_flights_in
        self.n_flights_out = n_flights_out
        self.pace = pace
        self.mean_connecting_wait_time = mean_connecting_wait_time
        self.p_geom_connect = p_geom_connect
        self.p_geom_external = p_geom_external



    def generate(self):
        self.G = nx.DiGraph()
        self.total_demand = 0

        n_external_in, n_external_out = \
            np.random.geometric(self.p_geom_external, size=2) - 1

        self.total_demand += n_external_in + n_external_out

        self._generate_nodes(n_external_in, incoming=True)
        self._generate_nodes(n_external_out, incoming=False)

        self._assign_external_nodes(forward=True)
        self._assign_external_nodes(forward=False)

        self._generate_forward_connections()

        self._adjust_flight_times()

        self._generate_backward_connections()

        self._add_s_and_t()

        return self.G



    @property
    def in_flight_nodes(self):
        return self.in_nodes[:self.n_flights_in]

    @property
    def in_external_nodes(self):
        return self.in_nodes[self.n_flights_in:]

    @property
    def out_flight_nodes(self):
        return self.out_nodes[:self.n_flights_out]

    @property
    def out_external_nodes(self):
        return self.out_nodes[self.n_flights_out:]




    def _generate_nodes(self, n_external, incoming):
        '''generates `n_flights` flights with randomly selected gates
        and flight times sampled according to a Poisson process (i.e.
        uniformly distributed within the 0-24 hour range)
        '''

        if incoming:
            n_flights = self.n_flights_in
            name_func = lambda i: f'in_{i+1}'
        else:
            n_flights = self.n_flights_out
            name_func = lambda i: f'out_{i+1}'

        node_names = [name_func(i) for i in range(n_flights + n_external)]

        gates = set(self.G_airport)
        gates = list(gates - set(['WH']))
        gates = list(np.random.choice(gates, n_flights))
        locations = gates + ['WH'] * n_external

        flight_times = np.random.uniform(0, 24, (n_flights + n_external,)) # Poisson process

        self.G.add_nodes_from((
            (name, {'loc': loc, 't': time})
            for name, loc, time in zip(node_names, locations, flight_times)
        ))

        if incoming:
            self.in_nodes = node_names
        else:
            self.out_nodes = node_names



    def _assign_external_nodes(self, forward):
        if forward:
            external_nodes = self.in_external_nodes
            flight_nodes = self.out_flight_nodes
        else:
            external_nodes = self.out_external_nodes
            flight_nodes = self.in_flight_nodes

        for external in external_nodes:
            flight = np.random.choice(flight_nodes)
            gate = self.G.nodes[flight]['loc']

            dist = nx.shortest_path_length(self.G_airport, 'WH', gate, weight='weight')
            t_escort = dist / self.pace

            edge = (external, flight) if forward else (flight, external)

            self.G.add_edge(
                *edge,
                capacity=1, 
                weight=-1, 
                t_escort=t_escort)



    def _generate_forward_connections(self):
        '''randomly matches `n_connecting` pairs of inbound and outbound flights,
        adding an edge with attribute `t_escort`, the time to escort from the
        inbound gate to the outbound gate
        '''

        for in_flight, out_flight in product(self.in_flight_nodes, self.out_flight_nodes):
            in_gate = self.G.nodes[in_flight]['loc']
            out_gate = self.G.nodes[out_flight]['loc']
            if in_gate == out_gate:
                continue

            wheelchair_demand = np.random.geometric(self.p_geom_connect) - 1
            if wheelchair_demand == 0:
                continue

            self.total_demand += wheelchair_demand

            dist = nx.shortest_path_length(self.G_airport, in_gate, out_gate, weight='weight')
            t_escort = dist / self.pace

            self.G.add_edge(
                in_flight, 
                out_flight, 
                capacity=wheelchair_demand, 
                weight=-1, 
                t_escort=t_escort)



    def _adjust_flight_times(self):
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
        for in_node, out_node in self.G.edges:
            t_arrival = self.G.nodes[in_node]['t']
            t_departure = self.G.nodes[out_node]['t']
            t_escort = self.G[in_node][out_node]['t_escort']

            t_departure_new = \
                t_arrival + t_escort + \
                np.random.exponential(self.mean_connecting_wait_time)

            t_departure = max(t_departure, t_departure_new)

            if t_departure >= 24:
                # shift flight times to fit in 0-24 time
                delta = t_departure - 24
                t_arrival -= delta
                t_departure -= delta

            self.G.nodes[in_node]['t'] = t_arrival
            self.G.nodes[out_node]['t'] = t_departure



    def _generate_backward_connections(self):
        for in_flight, out_flight in product(self.in_nodes, self.out_nodes):
            t_arrival = self.G.nodes[in_flight]['t']
            in_loc = self.G.nodes[in_flight]['loc']

            t_departure = self.G.nodes[out_flight]['t']
            out_loc = self.G.nodes[out_flight]['loc']

            dist = nx.shortest_path_length(self.G_airport, out_loc, in_loc, weight='weight')
            t_escort = dist / self.pace

            if t_arrival > t_departure + t_escort:
                self.G.add_edge(out_flight, in_flight, weight=-1)



    def _add_s_and_t(self):
        self.G.add_edges_from([('s', in_node, dict(weight=0)) for in_node in self.in_nodes])
        self.G.add_edges_from([(out_node, 't', dict(weight=0)) for out_node in self.out_nodes])
        self.G.add_edge('t', 's', weight=0)

