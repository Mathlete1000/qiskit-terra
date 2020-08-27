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

"""XY4 is a DD sequence that consist of pulses rotating around two axes. 
   The XY4 was created to correct the pulse correcting errors from the CPMG 
   due to the fact that CPMG can only mitigate a subspace of coupling errors. 
   The XY4 is the most basic sequence that takes into account all three 
   components of the system-environment interaction term. The sequence is 
   comprised of an X gate followed by a Y gate, X gate, and Y gate with a 
   fixed delay after each pulse.
"""

from qiskit.circuit.library.standard_gates import XGate, YGate
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.passes.basis.unroller import Unroller
from qiskit.circuit.quantumregister import QuantumRegister, Qubit

class XY4Pass(TransformationPass):
    """The pass that when called upon, will insert XY4 sequences into a 
    scheduled circuit where large enough Delay operations originally exist.
    """

    def __init__(self, backend_properties, tau_step=10e-9):
        """XY4Pass initializer.

        Args:
            backend_properties (BackendProperties): Properties returned by a
                backend, including information on gate errors, readout errors,
                qubit coherence times, etc.
            dt_in_sec (float): Sample duration [sec] used for the conversion.
            tau_step (float): Delay time between pulses in the DD sequence. Default
                is 10 ns.
        """
        super().__init__()
        self.backend_properties = backend_properties
        self.tau_step_dt = tau_step
        self.tau_cs = {}

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

            self.tau_cs[qubit] = 4 * self.tau_step_dt + 2 * gate_duration


    def run(self, dag):
        """Run the XY4 pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to new DAG.

        Returns:
            DAGCircuit: A new DAG with XY4 DD Sequences inserted in large enough delays.
        """
        new_dag = DAGCircuit()

        new_dag.name = dag.name

        for qreg in dag.qregs.values():
            new_dag.add_qreg(qreg)
        for creg in dag.cregs.values():
            new_dag.add_creg(creg)

        for node in dag.topological_op_nodes():

            if not isinstance(node.op, Delay):
                new_dag.apply_operation_back(node.op, node.qargs, node.cargs, node.condition)
                continue

            delay_duration = node.op.duration
            tau_c = self.tau_cs[node.qargs[0].index]

            if tau_c > delay_duration or len(dag.ancestors(node)) <= 1:
                # If a cycle of XY4 can't fit or there isn't at least 1 other operation before.
                new_dag.apply_operation_back(Delay(delay_duration, unit='s'), qargs=node.qargs)
                continue

            count = int(delay_duration // tau_c)
            new_delay = (delay_duration - count * tau_c + self.tau_step_dt) / 2

            new_dag.apply_operation_back(Delay(new_delay, unit='s'), qargs=node.qargs)

            first = True

            for _ in range(count):
                if not first:
                    new_dag.apply_operation_back(Delay(self.tau_step_dt, unit='s'), 
                                                       qargs=node.qargs)
                for basis_node in self.xgate_unroll.topological_op_nodes():
                    new_dag.apply_operation_back(basis_node.op, qargs=node.qargs)
                new_dag.apply_operation_back(Delay(self.tau_step_dt, unit='s'), qargs=node.qargs)
                for basis_node in self.ygate_unroll.topological_op_nodes():
                    new_dag.apply_operation_back(basis_node.op, qargs=node.qargs)
                new_dag.apply_operation_back(Delay(self.tau_step_dt, unit='s'), qargs=node.qargs)
                for basis_node in self.xgate_unroll.topological_op_nodes():
                    new_dag.apply_operation_back(basis_node.op, qargs=node.qargs)
                new_dag.apply_operation_back(Delay(self.tau_step_dt, unit='s'), qargs=node.qargs)
                for basis_node in self.ygate_unroll.topological_op_nodes():
                    new_dag.apply_operation_back(basis_node.op, qargs=node.qargs)
                first = False

            new_dag.apply_operation_back(Delay(new_delay, unit='s'), qargs=node.qargs)

        return new_dag
