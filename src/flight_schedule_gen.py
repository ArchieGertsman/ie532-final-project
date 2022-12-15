from itertools import product

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

PACE = 54.4804182335


class FlightScheduleGen():
    '''
    Nodes attribtues:
        -`loc`: location of the node. If it's a flight
            node, then the location is a randomly sampled
            gate. If it's an external node, then it's the
            wheelchair hub (WH).
        - `t`: time of the event associated with the node.
            If it's a flight node, then it's the arrival or
            departure time of the flight. If it's an external
            node, then it's the arrival or departure of a
            car/taxi to/from the airport.
    Edge attributes:
        - `t_escort`: time it takes to escort a wheelchair
            between the two locations that edge connects
        - `capacity`: the wheelchair demand along an edge if
            specified. Infinity if not specified. Used in 
            min-cost-flow.
        - `weight`: -1 along all edges non-adjacent to `s` and `t`,
            zero for the remaining edges. Used in min-cost-flow.
            Intuitively, we want to use as many (-1)-weight edges
            as possible to reuse wheelchairs and thus reduce cost.
    '''

    def __init__(self, G_airport):
        # we will call units in our coordinate system Scaled Airport Distance (SAD)
        # 1 SAD = 242.288888889 ft
        # pace units are in s^{-1}
        # 1 unit of pace = 2.5 mph
        # SAD / PACE = time in hours

        self.G_airport = G_airport
        



    def generate(self, 
        n_flights_in, 
        n_flights_out, 
        p_geom_connect=.9,
        p_geom_external=.1,
        mean_connecting_wait_time=.5
    ):
        '''parameters:
            - `n_flights_in`: number of inbound flights
            - `n_flights_out`: number of outbound flights
            - `p_geom_connect`: parameter for geometric distribution
                used in sampling wheelchair demand between two
                connecting flights. lower p = higher demand
            - `p_geom_external`: parameter for geometric distribution
                used in sampling wheelchair demand from arrivals and
                departures external to the airport (i.e. people arriving
                and departing by car/taxi). lower p = higher demand
            - `mean_connecting_wait_time`: expected time, in hours,
                that a passenger will wait until their connecting
                flight departs, from the time they arrive to the
                gate of the departing flight. Parameter for 
                exponential distribution.
        '''
        self.n_flights_in = n_flights_in
        self.n_flights_out = n_flights_out
        self.p_geom_connect = p_geom_connect
        self.p_geom_external = p_geom_external
        self.mean_connecting_wait_time = mean_connecting_wait_time

        self.G = nx.DiGraph()
        self.total_demand = 0

        n_external_in, n_external_out = \
            np.random.geometric(self.p_geom_external, size=2)

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



    def visualize(self):
        plt.figure(figsize=(8,6))
        pos, node_sizes = self._draw_nodes()
        self._draw_edges(pos, node_sizes)



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



    ## Graph generation functions

    def _generate_nodes(self, n_external, incoming):
        '''generates either incoming nodes or outgoing nodes,
        according to `incoming` flag. Number of external nodes 
        is given by `n_external`.
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
        '''for each external node, randomly samples a
        flight to connect to it. If `forward` is `True`
        then we connect the incoming external nodes
        to outgoing flight nodes. If `forward` is `False`
        then we connect the incoming flights to 
        outgoing external nodes.
        '''
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
            t_escort = dist / PACE

            edge = (external, flight) if forward else (flight, external)

            self.G.add_edge(
                *edge,
                capacity=1, 
                weight=-1, 
                t_escort=t_escort)



    def _generate_forward_connections(self):
        '''randomly samples wheelchair demand between pairs 
        of incoming flights and outgoing flights. If demand
        is positive, i.e. wheelchairs are needed between
        connecting flights, then an edge is added with 
        that demand. Otherwise, no edge is added.
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
            t_escort = dist / PACE

            self.G.add_edge(
                in_flight, 
                out_flight, 
                t_escort=t_escort,
                capacity=wheelchair_demand, 
                weight=-1)



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

            # we may keep iterating over `out_node`
            # since it can be part of multiple connections,
            # so to make sure the departure time is feasible
            # for all it's incoming connections, we take the
            # max over all of them
            t_departure = max(t_departure, t_departure_new)

            if t_departure >= 24:
                # shift flight times to fit in 0-24 time
                delta = t_departure - 24
                t_arrival -= delta
                t_departure -= delta

            self.G.nodes[in_node]['t'] = t_arrival
            self.G.nodes[out_node]['t'] = t_departure



    def _generate_backward_connections(self):
        '''if a wheelchair can be transferred from an
        outgoing node to an incoming node in time, then
        add a backward edge so that the wheelchair can
        be reused for the incoming node.
        '''
        for in_node, out_node in product(self.in_nodes, self.out_nodes):
            t_arrival = self.G.nodes[in_node]['t']
            in_loc = self.G.nodes[in_node]['loc']

            t_departure = self.G.nodes[out_node]['t']
            out_loc = self.G.nodes[out_node]['loc']

            dist = nx.shortest_path_length(self.G_airport, out_loc, in_loc, weight='weight')
            t_escort = dist / PACE

            if t_arrival > t_departure + t_escort:
                self.G.add_edge(out_node, in_node, weight=-1)



    def _add_s_and_t(self):
        '''`s` connects to all incoming flights, and
        `t` connects to all outgoing flights. After
        solving min cost flow on this networks, the flow
        through t->s is the minimum number of wheelchairs
        needed for this day.
        '''
        self.G.add_edges_from([
            ('s', in_node, dict(weight=0)) 
            for in_node in self.in_nodes])

        self.G.add_edges_from([
            (out_node, 't', dict(weight=0)) 
            for out_node in self.out_nodes])
            
        self.G.add_edge('t', 's', weight=0)



    ## Visualization functions

    def _draw_nodes(self):
        def pos_uniform_cluster(nodes, x_center, y_center, dx, dy):
            return {
                node: np.random.uniform(
                    low=[x_center-dx, y_center-dy], 
                    high=[x_center+dx, y_center+dy]
                )
                for node in nodes
            }

        pos = {}

        x = 1
        y = .9
        dx = .25
        dy = .6
        pos |= pos_uniform_cluster(self.in_flight_nodes, -x, y, dx, dy)
        pos |= pos_uniform_cluster(self.out_flight_nodes, x, y, dx, dy)
        pos |= pos_uniform_cluster(self.in_external_nodes, -x, -y, dx, dy)
        pos |= pos_uniform_cluster(self.out_external_nodes, x, -y, dx, dy)

        pos['s'] = np.array([-2, 0])
        pos['t'] = np.array([2, 0])

        node_colors, node_sizes = self._get_node_drawing_attr()
        nx.draw_networkx_nodes(self.G, pos=pos, node_size=node_sizes, node_color=node_colors)

        return pos, node_sizes



    def _get_node_drawing_attr(self):
        node_colors = []
        node_sizes = []
        for node in self.G:
            node_attr = self.G.nodes[node]
            if 'loc' not in node_attr:
                color = np.array([83,81,84]) / 255
                size = 100
            elif node_attr['loc'] == 'WH':
                color = np.array([62,150,80]) / 255
                size = 40
            else:
                color = np.array([107,76,154]) / 255
                size = 100
            node_colors += [color]
            node_sizes += [size]
        return node_colors, node_sizes



    def _draw_edges(self, pos, node_sizes):
        # draw edges not adjacent to s or t
        G = self.G.copy()
        G.remove_edge('t', 's')

        colors, alphas, widths = self._get_edge_drawing_attr(G)      

        _ = nx.draw_networkx_edges(
            G, 
            pos=pos, 
            width=widths, 
            alpha=alphas, 
            node_size=node_sizes, 
            edge_color=colors)

        # draw edges adjacent to s or t
        G = nx.DiGraph()
        G.add_edge('t', 's')
        _ = nx.draw_networkx_edges(
            G, 
            pos=pos, 
            width=.5, 
            connectionstyle='arc3,rad=.9', 
            node_size=node_sizes, 
            style='-.')



    def _get_edge_drawing_attr(self, G):
        colors = []
        alphas = []
        widths = []
        for u, v in G.edges:
            if u in self.in_nodes and v in self.out_nodes:
                color = 'black'
                alpha = .6
                width = .7
            else:
                color = 'black'
                alpha = .25
                width = .25
            colors += [color]
            alphas += [alpha]
            widths += [width]
        return colors, alphas, widths
