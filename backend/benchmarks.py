"""
benchmarks.py
─────────────
Named structural benchmark models served by GET /api/benchmarks/{name}.
Each entry has a "description" and a "payload" (SolveRequest-compatible dict).
"""

BENCHMARKS = {

    "tetrahedron": {
        "description": "Simple 6-bar tetrahedron (4 nodes). Good for solver smoke-test.",
        "payload": {
            "nodes": [
                {"id": 1, "x": 0.0, "y": 0.0, "z": 0.0, "rx": True,  "ry": True,  "rz": True},
                {"id": 2, "x": 3.0, "y": 0.0, "z": 0.0, "rx": False, "ry": True,  "rz": True},
                {"id": 3, "x": 1.5, "y": 3.0, "z": 0.0, "rx": False, "ry": False, "rz": True},
                {"id": 4, "x": 1.5, "y": 1.5, "z": 4.0, "rx": False, "ry": False, "rz": False},
            ],
            "members": [
                {"id": 1, "node_i": 1, "node_j": 2, "area": 0.01, "E": 2e11},
                {"id": 2, "node_i": 2, "node_j": 3, "area": 0.01, "E": 2e11},
                {"id": 3, "node_i": 3, "node_j": 1, "area": 0.01, "E": 2e11},
                {"id": 4, "node_i": 1, "node_j": 4, "area": 0.01, "E": 2e11},
                {"id": 5, "node_i": 2, "node_j": 4, "area": 0.01, "E": 2e11},
                {"id": 6, "node_i": 3, "node_j": 4, "area": 0.01, "E": 2e11},
            ],
            "loads": [
                {"node_id": 4, "fx": 0.0, "fy": 50000.0, "fz": -100000.0, "load_case": "DL"},
            ],
            "combos": [
                {"name": "Standard (1.0 DL)", "factors": {"DL": 1.0}},
                {"name": "Ultimate (1.5 DL)", "factors": {"DL": 1.5}},
            ],
            "analysis_type": "linear",
            "load_steps": 10,
        },
    },

    "25bar": {
        "description": "25-bar benchmark space truss. Classic optimisation test case.",
        "payload": {
            "nodes": [
                {"id": 1,  "x": -1.0, "y": 0.0,  "z": 5.0,  "rx": False, "ry": False, "rz": False},
                {"id": 2,  "x":  1.0, "y": 0.0,  "z": 5.0,  "rx": False, "ry": False, "rz": False},
                {"id": 3,  "x": -1.0, "y": 1.0,  "z": 2.5,  "rx": False, "ry": False, "rz": False},
                {"id": 4,  "x":  1.0, "y": 1.0,  "z": 2.5,  "rx": False, "ry": False, "rz": False},
                {"id": 5,  "x":  1.0, "y": -1.0, "z": 2.5,  "rx": False, "ry": False, "rz": False},
                {"id": 6,  "x": -1.0, "y": -1.0, "z": 2.5,  "rx": False, "ry": False, "rz": False},
                {"id": 7,  "x": -2.5, "y": 2.5,  "z": 0.0,  "rx": True,  "ry": True,  "rz": True},
                {"id": 8,  "x":  2.5, "y": 2.5,  "z": 0.0,  "rx": True,  "ry": True,  "rz": True},
                {"id": 9,  "x":  2.5, "y": -2.5, "z": 0.0,  "rx": True,  "ry": True,  "rz": True},
                {"id": 10, "x": -2.5, "y": -2.5, "z": 0.0,  "rx": True,  "ry": True,  "rz": True},
            ],
            "members": [
                {"id": 1,  "node_i": 1, "node_j": 2,  "area": 0.005, "E": 2e11},
                {"id": 2,  "node_i": 1, "node_j": 4,  "area": 0.005, "E": 2e11},
                {"id": 3,  "node_i": 2, "node_j": 3,  "area": 0.005, "E": 2e11},
                {"id": 4,  "node_i": 1, "node_j": 5,  "area": 0.005, "E": 2e11},
                {"id": 5,  "node_i": 2, "node_j": 6,  "area": 0.005, "E": 2e11},
                {"id": 6,  "node_i": 1, "node_j": 3,  "area": 0.005, "E": 2e11},
                {"id": 7,  "node_i": 2, "node_j": 4,  "area": 0.005, "E": 2e11},
                {"id": 8,  "node_i": 2, "node_j": 5,  "area": 0.005, "E": 2e11},
                {"id": 9,  "node_i": 1, "node_j": 6,  "area": 0.005, "E": 2e11},
                {"id": 10, "node_i": 3, "node_j": 6,  "area": 0.005, "E": 2e11},
                {"id": 11, "node_i": 4, "node_j": 5,  "area": 0.005, "E": 2e11},
                {"id": 12, "node_i": 3, "node_j": 4,  "area": 0.005, "E": 2e11},
                {"id": 13, "node_i": 5, "node_j": 6,  "area": 0.005, "E": 2e11},
                {"id": 14, "node_i": 3, "node_j": 10, "area": 0.005, "E": 2e11},
                {"id": 15, "node_i": 6, "node_j": 7,  "area": 0.005, "E": 2e11},
                {"id": 16, "node_i": 4, "node_j": 9,  "area": 0.005, "E": 2e11},
                {"id": 17, "node_i": 5, "node_j": 8,  "area": 0.005, "E": 2e11},
                {"id": 18, "node_i": 3, "node_j": 8,  "area": 0.005, "E": 2e11},
                {"id": 19, "node_i": 4, "node_j": 7,  "area": 0.005, "E": 2e11},
                {"id": 20, "node_i": 6, "node_j": 9,  "area": 0.005, "E": 2e11},
                {"id": 21, "node_i": 5, "node_j": 10, "area": 0.005, "E": 2e11},
                {"id": 22, "node_i": 3, "node_j": 7,  "area": 0.005, "E": 2e11},
                {"id": 23, "node_i": 4, "node_j": 8,  "area": 0.005, "E": 2e11},
                {"id": 24, "node_i": 5, "node_j": 9,  "area": 0.005, "E": 2e11},
                {"id": 25, "node_i": 6, "node_j": 10, "area": 0.005, "E": 2e11},
            ],
            "loads": [
                {"node_id": 1, "fx": 10000, "fy": 50000,  "fz": -50000, "load_case": "DL"},
                {"node_id": 2, "fx": 0,     "fy": 50000,  "fz": -50000, "load_case": "DL"},
                {"node_id": 3, "fx": 10000, "fy": 0,      "fz": 0,      "load_case": "WL"},
                {"node_id": 6, "fx": 10000, "fy": 0,      "fz": 0,      "load_case": "WL"},
            ],
            "combos": [
                {"name": "Gravity (1.5DL)",           "factors": {"DL": 1.5, "WL": 0.0}},
                {"name": "Extreme (1.2DL + 1.2WL)",   "factors": {"DL": 1.2, "WL": 1.2}},
            ],
            "analysis_type": "linear",
            "load_steps": 10,
        },
    },

    "72bar": {
        "description": "72-bar space tower (20 nodes, 4 tiers). Standard benchmark for IS 800 optimisation.",
        "payload": {
            "nodes": (lambda: (
                lambda nodes:
                    nodes
            )([
                {"id": 1,  "x": -1.5, "y":  1.5, "z": 0.0, "rx": True,  "ry": True,  "rz": True},
                {"id": 2,  "x":  1.5, "y":  1.5, "z": 0.0, "rx": True,  "ry": True,  "rz": True},
                {"id": 3,  "x":  1.5, "y": -1.5, "z": 0.0, "rx": True,  "ry": True,  "rz": True},
                {"id": 4,  "x": -1.5, "y": -1.5, "z": 0.0, "rx": True,  "ry": True,  "rz": True},
                {"id": 5,  "x": -1.5, "y":  1.5, "z": 1.5, "rx": False, "ry": False, "rz": False},
                {"id": 6,  "x":  1.5, "y":  1.5, "z": 1.5, "rx": False, "ry": False, "rz": False},
                {"id": 7,  "x":  1.5, "y": -1.5, "z": 1.5, "rx": False, "ry": False, "rz": False},
                {"id": 8,  "x": -1.5, "y": -1.5, "z": 1.5, "rx": False, "ry": False, "rz": False},
                {"id": 9,  "x": -1.5, "y":  1.5, "z": 3.0, "rx": False, "ry": False, "rz": False},
                {"id": 10, "x":  1.5, "y":  1.5, "z": 3.0, "rx": False, "ry": False, "rz": False},
                {"id": 11, "x":  1.5, "y": -1.5, "z": 3.0, "rx": False, "ry": False, "rz": False},
                {"id": 12, "x": -1.5, "y": -1.5, "z": 3.0, "rx": False, "ry": False, "rz": False},
                {"id": 13, "x": -1.5, "y":  1.5, "z": 4.5, "rx": False, "ry": False, "rz": False},
                {"id": 14, "x":  1.5, "y":  1.5, "z": 4.5, "rx": False, "ry": False, "rz": False},
                {"id": 15, "x":  1.5, "y": -1.5, "z": 4.5, "rx": False, "ry": False, "rz": False},
                {"id": 16, "x": -1.5, "y": -1.5, "z": 4.5, "rx": False, "ry": False, "rz": False},
                {"id": 17, "x": -1.5, "y":  1.5, "z": 6.0, "rx": False, "ry": False, "rz": False},
                {"id": 18, "x":  1.5, "y":  1.5, "z": 6.0, "rx": False, "ry": False, "rz": False},
                {"id": 19, "x":  1.5, "y": -1.5, "z": 6.0, "rx": False, "ry": False, "rz": False},
                {"id": 20, "x": -1.5, "y": -1.5, "z": 6.0, "rx": False, "ry": False, "rz": False},
            ]))(),
            "members": [
                # Tier 1
                {"id":  1,"node_i":1,"node_j":5,"area":0.005,"E":2e11},{"id":2,"node_i":2,"node_j":6,"area":0.005,"E":2e11},
                {"id":  3,"node_i":3,"node_j":7,"area":0.005,"E":2e11},{"id":4,"node_i":4,"node_j":8,"area":0.005,"E":2e11},
                {"id":  5,"node_i":5,"node_j":6,"area":0.005,"E":2e11},{"id":6,"node_i":6,"node_j":7,"area":0.005,"E":2e11},
                {"id":  7,"node_i":7,"node_j":8,"area":0.005,"E":2e11},{"id":8,"node_i":8,"node_j":5,"area":0.005,"E":2e11},
                {"id":  9,"node_i":1,"node_j":6,"area":0.005,"E":2e11},{"id":10,"node_i":2,"node_j":5,"area":0.005,"E":2e11},
                {"id": 11,"node_i":2,"node_j":7,"area":0.005,"E":2e11},{"id":12,"node_i":3,"node_j":6,"area":0.005,"E":2e11},
                {"id": 13,"node_i":3,"node_j":8,"area":0.005,"E":2e11},{"id":14,"node_i":4,"node_j":7,"area":0.005,"E":2e11},
                {"id": 15,"node_i":4,"node_j":5,"area":0.005,"E":2e11},{"id":16,"node_i":1,"node_j":8,"area":0.005,"E":2e11},
                {"id": 17,"node_i":5,"node_j":7,"area":0.005,"E":2e11},{"id":18,"node_i":6,"node_j":8,"area":0.005,"E":2e11},
                # Tier 2
                {"id": 19,"node_i":5,"node_j":9, "area":0.005,"E":2e11},{"id":20,"node_i":6,"node_j":10,"area":0.005,"E":2e11},
                {"id": 21,"node_i":7,"node_j":11,"area":0.005,"E":2e11},{"id":22,"node_i":8,"node_j":12,"area":0.005,"E":2e11},
                {"id": 23,"node_i":9,"node_j":10,"area":0.005,"E":2e11},{"id":24,"node_i":10,"node_j":11,"area":0.005,"E":2e11},
                {"id": 25,"node_i":11,"node_j":12,"area":0.005,"E":2e11},{"id":26,"node_i":12,"node_j":9,"area":0.005,"E":2e11},
                {"id": 27,"node_i":5,"node_j":10,"area":0.005,"E":2e11},{"id":28,"node_i":6,"node_j":9,"area":0.005,"E":2e11},
                {"id": 29,"node_i":6,"node_j":11,"area":0.005,"E":2e11},{"id":30,"node_i":7,"node_j":10,"area":0.005,"E":2e11},
                {"id": 31,"node_i":7,"node_j":12,"area":0.005,"E":2e11},{"id":32,"node_i":8,"node_j":11,"area":0.005,"E":2e11},
                {"id": 33,"node_i":8,"node_j":9, "area":0.005,"E":2e11},{"id":34,"node_i":5,"node_j":12,"area":0.005,"E":2e11},
                {"id": 35,"node_i":9,"node_j":11,"area":0.005,"E":2e11},{"id":36,"node_i":10,"node_j":12,"area":0.005,"E":2e11},
                # Tier 3
                {"id": 37,"node_i":9, "node_j":13,"area":0.005,"E":2e11},{"id":38,"node_i":10,"node_j":14,"area":0.005,"E":2e11},
                {"id": 39,"node_i":11,"node_j":15,"area":0.005,"E":2e11},{"id":40,"node_i":12,"node_j":16,"area":0.005,"E":2e11},
                {"id": 41,"node_i":13,"node_j":14,"area":0.005,"E":2e11},{"id":42,"node_i":14,"node_j":15,"area":0.005,"E":2e11},
                {"id": 43,"node_i":15,"node_j":16,"area":0.005,"E":2e11},{"id":44,"node_i":16,"node_j":13,"area":0.005,"E":2e11},
                {"id": 45,"node_i":9, "node_j":14,"area":0.005,"E":2e11},{"id":46,"node_i":10,"node_j":13,"area":0.005,"E":2e11},
                {"id": 47,"node_i":10,"node_j":15,"area":0.005,"E":2e11},{"id":48,"node_i":11,"node_j":14,"area":0.005,"E":2e11},
                {"id": 49,"node_i":11,"node_j":16,"area":0.005,"E":2e11},{"id":50,"node_i":12,"node_j":15,"area":0.005,"E":2e11},
                {"id": 51,"node_i":12,"node_j":13,"area":0.005,"E":2e11},{"id":52,"node_i":9,"node_j":16,"area":0.005,"E":2e11},
                {"id": 53,"node_i":13,"node_j":15,"area":0.005,"E":2e11},{"id":54,"node_i":14,"node_j":16,"area":0.005,"E":2e11},
                # Tier 4
                {"id": 55,"node_i":13,"node_j":17,"area":0.005,"E":2e11},{"id":56,"node_i":14,"node_j":18,"area":0.005,"E":2e11},
                {"id": 57,"node_i":15,"node_j":19,"area":0.005,"E":2e11},{"id":58,"node_i":16,"node_j":20,"area":0.005,"E":2e11},
                {"id": 59,"node_i":17,"node_j":18,"area":0.005,"E":2e11},{"id":60,"node_i":18,"node_j":19,"area":0.005,"E":2e11},
                {"id": 61,"node_i":19,"node_j":20,"area":0.005,"E":2e11},{"id":62,"node_i":20,"node_j":17,"area":0.005,"E":2e11},
                {"id": 63,"node_i":13,"node_j":18,"area":0.005,"E":2e11},{"id":64,"node_i":14,"node_j":17,"area":0.005,"E":2e11},
                {"id": 65,"node_i":14,"node_j":19,"area":0.005,"E":2e11},{"id":66,"node_i":15,"node_j":18,"area":0.005,"E":2e11},
                {"id": 67,"node_i":15,"node_j":20,"area":0.005,"E":2e11},{"id":68,"node_i":16,"node_j":19,"area":0.005,"E":2e11},
                {"id": 69,"node_i":16,"node_j":17,"area":0.005,"E":2e11},{"id":70,"node_i":13,"node_j":20,"area":0.005,"E":2e11},
                {"id": 71,"node_i":17,"node_j":19,"area":0.005,"E":2e11},{"id":72,"node_i":18,"node_j":20,"area":0.005,"E":2e11},
            ],
            "loads": [
                {"node_id": 17, "fx": 0, "fy": 0, "fz": -25000, "load_case": "DL"},
                {"node_id": 18, "fx": 0, "fy": 0, "fz": -25000, "load_case": "DL"},
                {"node_id": 19, "fx": 0, "fy": 0, "fz": -25000, "load_case": "DL"},
                {"node_id": 20, "fx": 0, "fy": 0, "fz": -25000, "load_case": "DL"},
                {"node_id": 17, "fx": 50000, "fy": 50000, "fz": 0, "load_case": "WL"},
            ],
            "combos": [
                {"name": "Gravity Only (1.0DL)",              "factors": {"DL": 1.0, "WL": 0.0}},
                {"name": "Extreme Wind+Gravity (1.5DL+1.5WL)","factors": {"DL": 1.5, "WL": 1.5}},
            ],
            "analysis_type": "linear",
            "load_steps": 10,
        },
    },
}
