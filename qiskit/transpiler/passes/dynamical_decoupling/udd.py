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

"""UDD (Uhrig DD) is a DD sequence that takes in account higher orders of 
   error mitigation in attempt to correct higher orders of perturbation from 
   the system-environment interaction term. The sequence sends a number of Y 
   gates equal to the order N specified and the time between pairs of Y 
   gates is proportional to the squared sine function. The base case is when 
   N = 2, which the UDD simplifies to the CPMG DD sequence.
"""

from qiskit.circuit.library.standard_gates import YGate
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.passes.basis.unroller import Unroller
from qiskit.circuit.quantumregister import QuantumRegister, Qubit

from math import sin, pi

class UDDPass(TransformationPass):
    """The pass that when called upon, will insert UDD sequences into a 
    scheduled circuit where large enough Delay operations originally exist.
    """

    def __init__(self, N, backend_properties, dt_in_sec, tau_c=None):
        """UDDPass initializer.
        Args:
            N (int): Order of the UDD sequence to implement.
            backend_properties (BackendProperties): Properties returned by a
                backend, including information on gate errors, readout errors,
                qubit coherence times, etc.
            dt_in_sec (float): Sample duration [sec] used for the conversion.
            tau_c (int): Cycle time of the UDD sequence. Default is 1000 * N dt 
                if not specified, where N is the order specified.
        """
        super().__init__()
        self.N = N
        self.backend_properties = backend_properties
        self.dt = dt_in_sec
        self.tau_c = 1000 * self.N if not tau_c else tau_c

    def run(self, dag):
        """Run the UDD pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to new DAG.

        Returns:
            DAGCircuit: A new DAG with UDD Sequences inserted in large enough delays.
        """
        tau_step_totals = {}
        tau_steps_dict = {}

        basis = self.backend_properties._gates.keys()
        qubits = len(self.backend_properties.qubits)

        for qubit in range(qubits):
            gate_duration = 0

            ygate_dag = DAGCircuit()
            ygate_qreg = QuantumRegister(qubits, 'q')
            ygate_dag.add_qreg(ygate_qreg)
            ygate_qubit = Qubit(ygate_qreg, qubit)
            ygate_dag.apply_operation_back(YGate(), [ygate_qubit])

            ygate_unroll = Unroller(basis).run(ygate_dag)

            for node in ygate_unroll.topological_op_nodes():
                gate_duration += \
                        self.backend_properties._gates[node.op.name][(qubit,)]['gate_length'][0]

            tau_step_totals[qubit] = round(self.tau_c - self.N * gate_duration // self.dt)

            t_i = [int(round(tau_step_totals[qubit] * \
                            (sin(pi * i / (2 * (self.N + 1)))) ** 2)) \
                            for i in range(self.N + 2)]

            tau_steps_dict[qubit] = [t_i[i] - t_i[i-1] for i in range(1, self.N + 2)]

            # TODO: Maybe check if each tau step is 0, but makes error checking
            # complicated in case of overflow of sum
            # TODO: Also maybe check if sum(tau_steps) > udd_duration due to rounding up
            # too frequently

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
                udd_duration = tau_step_totals[node.qargs[0].index]

                if self.tau_c > delay_duration or len(dag.ancestors(node)) <= 1:
                    # If a cycle of UDD can't fit or there isn't at least 1 other operation before.
                    new_dag.apply_operation_back(Delay(delay_duration), qargs=node.qargs)

                else:
                    tau_steps = tau_steps_dict[node.qargs[0].index]
                    count = delay_duration // self.tau_c
                    remainder = udd_duration - sum(tau_steps)
                    parity = 1 if (delay_duration - count * self.tau_c + count * remainder) % 2 \
                               else 0
                    new_delay = int((delay_duration - count * self.tau_c + count * remainder) / 2)

                    if new_delay != 0:
                        new_dag.apply_operation_back(Delay(new_delay), qargs=node.qargs)

                    for _ in range(count):
                        new_dag.apply_operation_back(Delay(tau_steps[0]), qargs=node.qargs)
                        for tau_step in tau_steps[1:]:
                            for basis_node in ygate_unroll.topological_op_nodes():
                                new_dag.apply_operation_back(basis_node.op, qargs=node.qargs)
                            new_dag.apply_operation_back(Delay(tau_step), qargs=node.qargs)

                    if new_delay != 0 or parity != 0:
                        new_dag.apply_operation_back(Delay(new_delay + parity), qargs=node.qargs)

        return new_dag
