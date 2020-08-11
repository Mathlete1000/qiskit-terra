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

"""NUDD Pass"""
from qiskit.circuit.library.standard_gates import YGate, CXGate
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.exceptions import TranspilerError

from math import sin, pi

class NUDDPass(TransformationPass):
    """NUDD Pass"""

    def __init__(self, N, backend_properties, dt_in_sec, tau_c=None):
        """NUDDPass initializer.
        Args:
            N (int): Order of the NUDD sequence to implement.
            backend_properties (BackendProperties): Properties returned by a
                backend, including information on gate errors, readout errors,
                qubit coherence times, etc.
            dt_in_sec (float): Sample duration [sec] used for the conversion.
            tau_c (int): Cycle time of the NUDD sequence. Default is 2000 dt if
                not specified.
        """
        super().__init__()
        self.N = N
        self.backend_properties = backend_properties
        self.dt = dt_in_sec
        self.tau_c = 2000 if not tau_c else tau_c

        self.gate_length_totals = {}
        self.tau_steps_dict = {}

        u3_props = self.backend_properties._gates['u3']
        for qubit, props in u3_props.items():
            if 'gate_length' in props:
                gate_length = props['gate_length'][0]
                # TODO: Needs to check if total gate duration exceeds the input tau_c
                # If so, raise error
                self.gate_length_totals[qubit[0]] = int(self.N * round(gate_length / self.dt))

                t_i = [sin(pi * i / (2 * (self.N + 1))) ** 2 \
                                            for i in range(self.N + 2)]

                self.tau_steps_dict[qubit[0]] = [t_i[i] - t_i[i-1] for i in range(1, self.N + 2)]
                # TODO: Maybe check if each tau step is 0, but makes error checking
                # complicated in case of overflow of sum
                # TODO: Also maybe check if sum(tau_steps) > udd_duration due to rounding up
                # too frequently

        self.nudd = {}
        self.doable = True

    def run(self, dag):
        """Run the NUDD pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to new DAG.

        Returns:
            DAGCircuit: A new DAG with NUDD Sequences inserted in large 
                        enough delays.
        """

        def find_udd(qubit, duration):
            sequence = []
            if duration - self.gate_length_totals[qubit] < 0:
                self.doable = False
            tau_steps = [round((duration - self.gate_length_totals[qubit]) * elem) for elem in self.tau_steps_dict[qubit]]
            sequence.append(Delay(tau_steps[0]))
            for tau_step in tau_steps[1:]:
                sequence.append(YGate(qubit).definition.data[0][0])
                sequence.append(Delay(tau_step))
            return sequence

        def add_nudd(qubits, duration):
            sequence = find_udd(qubits[0], duration)
            for gate in sequence:
                if qubits[0] in self.nudd:
                    self.nudd[qubits[0]].append(gate)
                else:
                    self.nudd[qubits[0]] = [gate]

                if isinstance(gate, Delay) and len(qubits) > 1:
                    add_nudd(qubits[1:], gate.duration)
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

        add_nudd(duration_qubits, duration)

        for node in dag.topological_op_nodes():
            predecessors = list(dag.predecessors(node))

            if not isinstance(node.op, Delay) or len(dag.ancestors(node)) <= 1:
                new_dag.apply_operation_back(node.op, node.qargs, node.cargs, node.condition)

            elif isinstance(predecessors[-1].op, CXGate) and self.doable:

                for gate in self.nudd[node.qargs[0].index]:
                    new_dag.apply_operation_back(gate, qargs=node.qargs)

            else:
                new_dag.apply_operation_back(node.op, node.qargs, node.cargs, node.condition)

        return new_dag
