# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""NCDD Pass"""
from qiskit.circuit.library.standard_gates import XGate, YGate, CXGate
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.exceptions import TranspilerError

from math import sin, pi

class NCDDPass(TransformationPass):
    """NCDD Pass"""

    def __init__(self, N, backend_properties, dt_in_sec):
        """NCDDPass initializer.
        Args:
            N (int): Order of the NCDD sequence to implement.
            backend_properties (BackendProperties): Properties returned by a
                backend, including information on gate errors, readout errors,
                qubit coherence times, etc.
            dt_in_sec (float): Sample duration [sec] used for the conversion.
        """
        super().__init__()
        self.N = N
        self.backend_properties = backend_properties
        self.dt = dt_in_sec
        self.gate_length_totals = {}

        def build_sequence(N: int):
            """
            Recursively builds a list of gates to represent the CDD sequence
            for the given order N (int).
            """
            if N == 1:
                return [XGate(), YGate(), XGate(), YGate()]
            return [XGate()] + build_sequence(N-1) + [YGate()] + build_sequence(N-1) + \
                   [XGate()] + build_sequence(N-1) + [YGate()] + build_sequence(N-1)

        self.cdd_sequence = build_sequence(self.N)

        u3_props = self.backend_properties._gates['u3']
        for qubit, props in u3_props.items():
            if 'gate_length' in props:
                gate_length = props['gate_length'][0]
                # TODO: Needs to check if total gate duration exceeds the input tau_c
                # If so, raise error
                self.gate_length_totals[qubit[0]] = len(self.cdd_sequence) * round(gate_length / self.dt)

        self.ncdd = {}
        self.doable = True

    def run(self, dag):
        """Run the NCDD pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to new DAG.

        Returns:
            DAGCircuit: A new DAG with NCDD Sequences inserted in large 
                        enough delays.
        """
        def find_cdd(qubit: int, duration: int):
            sequence = []
            if duration - self.gate_length_totals[qubit] < 0:
                self.doable = False
            tau_step = (duration - self.gate_length_totals[qubit]) // len(self.cdd_sequence)
            sequence.append(Delay(tau_step))
            for gate in self.cdd_sequence:
                sequence.append(gate.definition.data[0][0])
                sequence.append(Delay(tau_step))
            return sequence

        def add_ncdd(qubits: List[int], duration: int):
            sequence = find_cdd(qubits[0], duration)
            for gate in sequence:
                if qubits[0] in self.ncdd:
                    self.ncdd[qubits[0]].append(gate)
                else:
                    self.ncdd[qubits[0]] = [gate]

                if isinstance(gate, Delay) and len(qubits) > 1:
                    add_ncdd(qubits[1:], gate.duration)
            return None

        new_dag = DAGCircuit()

        new_dag.name = dag.name
        new_dag.instruction_durations = dag.instruction_durations

        for qreg in dag.qregs.values():
            new_dag.add_qreg(qreg)
        for creg in dag.cregs.values():
            new_dag.add_creg(creg)

        durations = []
        duration_qubits = []

        for node in dag.topological_op_nodes():

            predecessors = list(dag.predecessors(node))
            successors = list(dag.successors(node))

            if isinstance(node.op, Delay) and len(dag.ancestors(node)) > 1:
                if isinstance(predecessors[-1].op, CXGate):
                    if isinstance(successors[0].op, Delay):
                        duration = node.op.duration + successors[0].op.duration
                    else:
                        duration = node.op.duration

                    durations.append(duration)
                    duration_qubits.append(node.qargs[0].index)

        duration = min(durations)

        add_ncdd(duration_qubits, duration)

        for node in dag.topological_op_nodes():
            predecessors = list(dag.predecessors(node))

            if not isinstance(node.op, Delay) or len(dag.ancestors(node)) <= 1:
                new_dag.apply_operation_back(node.op, node.qargs, node.cargs, node.condition)

            elif isinstance(predecessors[-1].op, CXGate) and self.doable:

                for gate in self.ncdd[node.qargs[0].index]:
                    new_dag.apply_operation_back(gate, qargs=node.qargs)

            else:
                new_dag.apply_operation_back(node.op, node.qargs, node.cargs, node.condition)

        return new_dag
