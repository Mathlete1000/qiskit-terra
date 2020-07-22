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

from qiskit.circuit.library.standard_gates import XGate, YGate
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.test.mock import FakeAlmaden


class XY4Pass(TransformationPass):

    def __init__(self, backend_properties, dt_in_sec):
        """XY4Pass initializer.

        Args:
            backend_properties (BackendProperties): Properties returned by a
                backend, including information on gate errors, readout errors,
                qubit coherence times, etc.
            dt_in_sec (float): Sample duration [sec] used for the conversion.
        """
        super().__init__()
        self.backend_properties = backend_properties
        self.dt = dt_in_sec


    def run(self, dag):
        """Run the XY4 pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to new DAG.

        Returns:
            DAGCircuit: A new DAG with XY4 DD Sequences inserted in large 
                        enough delays.
        """
        xy4_durations = {}
        tau_c = 1461           # in units of dt

        u3_props = self.backend_properties._gates['u3']
        for qubit, props in u3_props.items():
            if 'gate_length' in props:
                gate_length = props['gate_length'][0]
                # TODO: Needs to check if durations of gates exceed cycle time
                # If so, raise error
                xy4_durations[qubit[0]] = tau_c - round(4 * gate_length / self.dt)

        new_dag = DAGCircuit()

        for qreg in dag.qregs.values():
            new_dag.add_qreg(qreg)
        for creg in dag.cregs.values():
            new_dag.add_creg(creg)
            
        for node in dag.topological_op_nodes():

            if isinstance(node.op, Delay):
                delay_duration = dag.instruction_durations.get(node.op, node.qargs)
                xy4_duration = xy4_durations[node.qargs[0].index]

                if tau_c <= delay_duration:
                    count = int(delay_duration // tau_c)
                    error = xy4_duration - 4 * (xy4_duration // 4)
                    dd_delay = xy4_duration // 4
                    parity = 1 if (delay_duration - count * tau_c + error + dd_delay) % 2 else 0
                    new_delay = int((delay_duration - count * tau_c + error + dd_delay) / 2)

                    new_dag.apply_operation_back(Delay(new_delay - dd_delay), qargs=node.qargs)

                    for _ in range(count):
                        new_dag.apply_operation_back(Delay(dd_delay), qargs=node.qargs)
                        new_dag.apply_operation_back(XGate(), qargs=node.qargs)
                        new_dag.apply_operation_back(Delay(dd_delay), qargs=node.qargs)
                        new_dag.apply_operation_back(YGate(), qargs=node.qargs)
                        new_dag.apply_operation_back(Delay(dd_delay), qargs=node.qargs)
                        new_dag.apply_operation_back(XGate(), qargs=node.qargs)
                        new_dag.apply_operation_back(Delay(dd_delay), qargs=node.qargs)
                        new_dag.apply_operation_back(YGate(), qargs=node.qargs)

                    new_dag.apply_operation_back(Delay(new_delay + parity), qargs=node.qargs)

                else:
                    new_dag.apply_operation_back(Delay(delay_duration), qargs=node.qargs)

            else:
                new_dag.apply_operation_back(node.op, node.qargs, node.cargs, node.condition)

        new_dag.name = dag.name
        new_dag.instruction_durations = dag.instruction_durations

        return new_dag
