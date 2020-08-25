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

"""CPMG (Carr–Purcell–Meiboom–Gill) is a DD sequence that consist of pulses 
   rotating around a single axis. In this case, we will consider the y-axis 
   such that we will be using Y gates in the sequence. 
   The sequence is comprised of a quarter of the cycle time of free evolution 
   followed by a Y gate pulse, followed with half of the cycle time of free 
   evolution, followed with a second Y gate pulse, and ending with a quarter 
   of cycle time of free evolution. This DD sequence is useful for when the 
   coupling term between the system and the environment contains components 
   orthogonal to the axis of rotation.
"""

from qiskit.circuit.library.standard_gates import XGate, YGate
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.passes.basis.unroller import Unroller
from qiskit.circuit.quantumregister import QuantumRegister, Qubit

class CPMGPass(TransformationPass):
    """The pass that when called upon, will insert CPMG sequences into a 
    scheduled circuit where large enough Delay operations originally exist.
    """

    def __init__(self, backend_properties, dt_in_sec, tau_c=None):
        """CPMGPass initializer.
        Args:
            backend_properties (BackendProperties): Properties returned by a
                backend, including information on gate errors, readout errors,
                qubit coherence times, etc.
            dt_in_sec (float): Sample duration [sec] used for the conversion.
            tau_c (int): Cycle time of the DD sequence. Default is 2000 dt.
        """
        super().__init__()
        self.backend_properties = backend_properties
        self.dt = dt_in_sec
        self.tau_c = 2000 if not tau_c else tau_c

    def run(self, dag):
        """Run the CPMG pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to new DAG.

        Returns:
            DAGCircuit: A new DAG with CPMG DD Sequences inserted in large enough delays.
        """
        tau_step_totals = {}

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

            tau_step_totals[qubit] = round(self.tau_c - 2 * gate_duration // self.dt)

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
                tau_step_total = tau_step_totals[node.qargs[0].index]

                if self.tau_c > delay_duration or len(dag.ancestors(node)) <= 1:
                    #If a cycle of CPMG can't fit or there isn't at least 1 other operation before.
                    new_dag.apply_operation_back(Delay(delay_duration), qargs=node.qargs)

                else:
                    count = delay_duration // self.tau_c
                    remainder = tau_step_total - 2 * (tau_step_total // 4) - tau_step_total // 2
                    parity = 1 if (delay_duration - count * (self.tau_c - remainder)) % 2 else 0
                    new_delay = (delay_duration - count * (self.tau_c - remainder)) // 2

                    new_dag.apply_operation_back(Delay(new_delay), qargs=node.qargs)

                    for _ in range(count):
                        new_dag.apply_operation_back(Delay(tau_step_total // 4), qargs=node.qargs)
                        for basis_node in self.ygate_unroll.topological_op_nodes():
                            new_dag.apply_operation_back(basis_node.op, qargs=node.qargs)
                        new_dag.apply_operation_back(Delay(tau_step_total // 2), qargs=node.qargs)
                        for basis_node in self.ygate_unroll.topological_op_nodes():
                            new_dag.apply_operation_back(basis_node.op, qargs=node.qargs)
                        new_dag.apply_operation_back(Delay(tau_step_total // 4), qargs=node.qargs)

                    new_dag.apply_operation_back(Delay(new_delay + parity), qargs=node.qargs)

        return new_dag
