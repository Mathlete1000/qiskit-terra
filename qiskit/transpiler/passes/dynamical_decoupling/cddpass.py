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

"""CDD Pass"""
from qiskit.circuit.library.standard_gates import XGate, YGate
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass

class CDDPass(TransformationPass):
    """CDD Pass"""

    def __init__(self, N, backend_properties, dt_in_sec, tau_c=None, tau_step=10):
        """CDDPass initializer.
        Args:
            N (int): Order of the CDD sequence to implement.
            backend_properties (BackendProperties): Properties returned by a
                backend, including information on gate errors, readout errors,
                qubit coherence times, etc.
            dt_in_sec (float): Sample duration [sec] used for the conversion.
            tau_c (int): Cycle time of the DD sequence. Default is the sum of gate
                durations of DD sequences with 10 ns delays in between.
            tau_step (float): Delay time between pulses in the DD sequence. Default
                is 10 ns.
        """
        super().__init__()
        self.N = N
        self.backend_properties = backend_properties
        self.dt = dt_in_sec
        self.tau_step = tau_step
        self.tau_cs = {}
        self.tau_step_totals = {}
        self.tau_c = tau_c

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
                # TODO: Needs to check if durations of gates exceed cycle time
                # If so, raise error
                if tau_c is None:
                    self.tau_cs[qubit[0]] = len(self.cdd_sequence) * \
                                        (round(tau_step * 1e-9 / self.dt + gate_length / self.dt))
                    self.tau_step_totals[qubit[0]] = self.tau_cs[qubit[0]] - \
                                            round(len(self.cdd_sequence) * gate_length / self.dt)
                else:
                    self.tau_step_totals[qubit[0]] = tau_c - \
                                            round(len(self.cdd_sequence) * gate_length / self.dt)

    def run(self, dag):
        """Run the CDD pass on `dag`.
        Args:
            dag (DAGCircuit): DAG to new DAG.
        Returns:
            DAGCircuit: A new DAG with CDD Sequences inserted in large 
                        enough delays.
        """
        new_dag = DAGCircuit()

        for qreg in dag.qregs.values():
            new_dag.add_qreg(qreg)
        for creg in dag.cregs.values():
            new_dag.add_creg(creg)

        for node in dag.topological_op_nodes():

            if isinstance(node.op, Delay):
                delay_duration = node.op.duration
                self.tau_step_total = self.tau_step_totals[node.qargs[0].index]
                tau_c = self.tau_cs[node.qargs[0].index] if self.tau_c is None else self.tau_c

                if tau_c <= delay_duration:
                    count = delay_duration // tau_c
                    tau_step = self.tau_step_total // len(self.cdd_sequence)
                    remainder = self.tau_step_total % len(self.cdd_sequence)
                    parity = 1 if (delay_duration - count * (tau_c - remainder) + tau_step) % 2 \
                               else 0
                    new_delay = (delay_duration - count * (tau_c - remainder) + tau_step) // 2

                    new_dag.apply_operation_back(Delay(new_delay - tau_step), qargs=node.qargs)

                    for _ in range(count):
                        for gate in self.cdd_sequence:
                            new_dag.apply_operation_back(Delay(tau_step), qargs=node.qargs)
                            new_dag.apply_operation_back(gate, qargs=node.qargs)

                    new_dag.apply_operation_back(Delay(new_delay + parity), qargs=node.qargs)

                else:
                    new_dag.apply_operation_back(Delay(delay_duration), qargs=node.qargs)

            else:
                new_dag.apply_operation_back(node.op, node.qargs, node.cargs, node.condition)

        new_dag.name = dag.name
        new_dag.instruction_durations = dag.instruction_durations

        return new_dag
