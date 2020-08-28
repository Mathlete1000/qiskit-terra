# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""CDD (Concatentated DD) is a DD sequence that takes in account higher 
   orders of error mitigation in attempt to correct higher orders of 
   perturbation from the system-environment interaction term for all 
   components. The structure of the sequence is recursive, and the amount 
   of time for free evolution between pulses is constant. The lowest order 
   for the CDD sequence is N = 1, which simplifies the DD sequence down 
   to the XY4 DD sequence. Due to the recursive nature, the amount of 
   gates needed for CDD increases exponentially with respect to the order.
"""

from qiskit.circuit.library.standard_gates import XGate, YGate
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.passes.basis.unroller import Unroller
from qiskit.circuit.quantumregister import QuantumRegister, Qubit

class CDDPass(TransformationPass):
    """The pass that when called upon, will insert CDD sequences into a 
    scheduled circuit where large enough Delay operations originally exist.
    """

    def __init__(self, N, backend_properties, dt_in_sec, tau_step=10e-9):
        """CDDPass initializer.
        Args:
            N (int): Order of the CDD sequence to implement.
            backend_properties (BackendProperties): Properties returned by a
                backend, including information on gate errors, readout errors,
                qubit coherence times, etc.
            dt_in_sec (float): Sample duration [sec] used for the conversion.
            tau_step (float): Delay time between pulses in the DD sequence. Default
                is 10 ns.
        """
        super().__init__()
        self.N = N
        self.backend_properties = backend_properties
        self.dt = dt_in_sec
        self.tau_step_dt = int(tau_step / self.dt)
        self.tau_cs = {}

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

        basis = backend_properties._gates.keys()
        qubits = len(backend_properties.qubits)

        for qubit in range(qubits):
            xgate_dag = DAGCircuit()
            xgate_qreg = QuantumRegister(qubits, 'q')
            xgate_dag.add_qreg(xgate_qreg)

            xgate_qubit = Qubit(xgate_qreg, qubit)
            xgate_dag.apply_operation_back(XGate(), [xgate_qubit])

            gate_duration = 0
            self.xgate_unroll = Unroller(basis).run(xgate_dag)

            for node in self.xgate_unroll.topological_op_nodes():
                gate_duration += \
                    self.backend_properties._gates[node.op.name][(qubit,)]['gate_length'][0]

            ygate_dag = DAGCircuit()
            ygate_qreg = QuantumRegister(qubits, 'q')
            ygate_dag.add_qreg(ygate_qreg)
            ygate_qubit = Qubit(ygate_qreg, qubit)
            ygate_dag.apply_operation_back(YGate(), [ygate_qubit])

            self.ygate_unroll = Unroller(basis).run(ygate_dag)

            for node in self.ygate_unroll.topological_op_nodes():
                gate_duration += \
                    self.backend_properties._gates[node.op.name][(qubit,)]['gate_length'][0]

            self.tau_cs[qubit] = len(self.cdd_sequence) // 2 * \
                                 (round(2 * self.tau_step_dt + gate_duration / self.dt))


    def run(self, dag):
        """Run the CDD pass on `dag`.
        Args:
            dag (DAGCircuit): DAG to new DAG.
        Returns:
            DAGCircuit: A new DAG with CDD Sequences inserted in large enough delays.
        """
        new_dag = DAGCircuit()

        new_dag.name = dag.name
        new_dag.instruction_durations = dag.instruction_durations

        for qreg in dag.qregs.values():
            new_dag.add_qreg(qreg)
        for creg in dag.cregs.values():
            new_dag.add_creg(creg)

        for node in dag.topological_op_nodes():

            if not isinstance(node.op, Delay):
                new_dag.apply_operation_back(node.op, node.qargs, node.cargs, node.condition)

            else:
                delay_duration = node.op.duration
                tau_c = self.tau_cs[node.qargs[0].index]

                if tau_c > delay_duration or len(dag.ancestors(node)) <= 1:
                    # If a cycle of CDD can't fit or there isn't at least 1 other operation before.
                    new_dag.apply_operation_back(Delay(delay_duration), qargs=node.qargs)

                else:
                    count = delay_duration // tau_c
                    parity = 1 if (delay_duration - count * tau_c + self.tau_step_dt) % 2 \
                               else 0
                    new_delay = (delay_duration - count * tau_c + self.tau_step_dt) // 2

                    if new_delay != 0:
                        new_dag.apply_operation_back(Delay(new_delay), qargs=node.qargs)

                    first = True

                    for _ in range(count):
                        for gate in self.cdd_sequence:
                            if not first:
                                new_dag.apply_operation_back(Delay(self.tau_step_dt), 
                                                                   qargs=node.qargs)
                            first = False
                            if isinstance(gate, XGate):
                                for basis_node in self.xgate_unroll.topological_op_nodes():
                                    new_dag.apply_operation_back(basis_node.op, qargs=node.qargs)
                                continue
                            for basis_node in self.ygate_unroll.topological_op_nodes():
                                new_dag.apply_operation_back(basis_node.op, qargs=node.qargs)

                    if new_delay != 0 or parity != 0:
                        new_dag.apply_operation_back(Delay(new_delay + parity), qargs=node.qargs)

        return new_dag
