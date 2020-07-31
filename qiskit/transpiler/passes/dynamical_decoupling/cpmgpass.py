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

"""CPMG DD Pass"""
from qiskit.circuit.library.standard_gates import XGate, YGate
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass

class CPMGPass(TransformationPass):
    """CPMG DD Pass"""

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
            DAGCircuit: A new DAG with CPMG DD Sequences inserted in large 
                        enough delays.
        """
        tau_step_totals = {}

        u3_props = self.backend_properties._gates['u3']
        for qubit, props in u3_props.items():
            if 'gate_length' in props:
                gate_length = props['gate_length'][0]
                # TODO: Needs to check if total gate duration exceeds the input t_c
                # If so, raise error
                tau_step_totals[qubit[0]] = round(self.tau_c - 2 * gate_length // self.dt)

        new_dag = DAGCircuit()

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
                    new_dag.apply_operation_back(Delay(delay_duration), qargs=node.qargs)

                else:
                    count = delay_duration // self.tau_c
                    remainder = tau_step_total - 2 * (tau_step_total // 4) - tau_step_total // 2
                    parity = 1 if (delay_duration - count * (self.tau_c - remainder)) % 2 else 0
                    new_delay = (delay_duration - count * (self.tau_c - remainder)) // 2

                    new_dag.apply_operation_back(Delay(new_delay), qargs=node.qargs)

                    for _ in range(count):
                        new_dag.apply_operation_back(Delay(tau_step_total // 4), qargs=node.qargs)
                        new_dag.apply_operation_back(YGate(), qargs=node.qargs)
                        new_dag.apply_operation_back(Delay(tau_step_total // 2), qargs=node.qargs)
                        new_dag.apply_operation_back(YGate(), qargs=node.qargs)
                        new_dag.apply_operation_back(Delay(tau_step_total // 4), qargs=node.qargs)

                    new_dag.apply_operation_back(Delay(new_delay + parity), qargs=node.qargs)

        return new_dag
