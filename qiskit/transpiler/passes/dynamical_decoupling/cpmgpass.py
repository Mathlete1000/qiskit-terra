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

class CPMGPass(TransformationPass):

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
        """Run the CPMG pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to new DAG.

        Returns:
            DAGCircuit: A new DAG with CPMG DD Sequences inserted in large 
                        enough delays.
        """
        t_c = 2000      # In units of dt
        first = True
        cpmg_durations = {}

        u3_props = self.backend_properties._gates['u3']
        for qubit, props in u3_props.items():
            if 'gate_length' in props:
                gate_length = props['gate_length'][0]
                # TODO: Needs to check if total gate duration exceeds the input t_c
                # If so, raise error
                cpmg_durations[qubit[0]] = round(t_c - 2 * gate_length // self.dt)

        new_dag = DAGCircuit()

        for qreg in dag.qregs.values():
            new_dag.add_qreg(qreg)
        for creg in dag.cregs.values():
            new_dag.add_creg(creg)

            
        for node in dag.topological_op_nodes():

            if isinstance(node.op, Delay):
                delay_duration = dag.instruction_durations.get(node.op, node.qargs)
                cpmg_duration = cpmg_durations[node.qargs[0].index]
                print(cpmg_duration)

                if t_c <= delay_duration:
                    count = int(delay_duration // t_c)
                    error = cpmg_duration - 2 * (cpmg_duration//4) - cpmg_duration // 2             # Leftover from modulo errors
                    parity = 1 if (delay_duration - count * t_c + count * error) % 2 else 0
                    new_delay = int((delay_duration - count * t_c + count * error) / 2)

                    new_dag.apply_operation_back(Delay(new_delay), qargs=node.qargs)

                    for _ in range(count):
                        new_dag.apply_operation_back(Delay(cpmg_duration // 4), qargs=node.qargs)
                        new_dag.apply_operation_back(YGate(), qargs=node.qargs)
                        new_dag.apply_operation_back(Delay(cpmg_duration // 2), qargs=node.qargs)
                        new_dag.apply_operation_back(YGate(), qargs=node.qargs)
                        new_dag.apply_operation_back(Delay(cpmg_duration // 4), qargs=node.qargs)

                    new_dag.apply_operation_back(Delay(new_delay + parity), qargs=node.qargs)
                    first = True

                else:
                    new_dag.apply_operation_back(Delay(delay_duration), qargs=node.qargs)

            else:
                new_dag.apply_operation_back(node.op, node.qargs, node.cargs, node.condition)

        return new_dag