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

"""UDD Pass"""
from qiskit.circuit.library.standard_gates import XGate, YGate
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass

from math import sin, pi

class UDDPass(TransformationPass):
    """UDD Pass"""

    def __init__(self, N, backend_properties, dt_in_sec, tau_c=None):
        """UDDPass initializer.
        Args:
            N (int): Order of the UDD sequence to implement.
            backend_properties (BackendProperties): Properties returned by a
                backend, including information on gate errors, readout errors,
                qubit coherence times, etc.
            dt_in_sec (float): Sample duration [sec] used for the conversion.
            tau_c (int): Cycle time of the UDD sequence. Default is 2000 dt if
                not specified.
        """
        super().__init__()
        self.N = N
        self.backend_properties = backend_properties
        self.dt = dt_in_sec
        self.tau_c = 2000 if not tau_c else tau_c

    def run(self, dag):
        """Run the UDD pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to new DAG.

        Returns:
            DAGCircuit: A new DAG with UDD Sequences inserted in large 
                        enough delays.
        """
        tau_step_totals = {}
        tau_steps_dict = {}

        u3_props = self.backend_properties._gates['u3']
        for qubit, props in u3_props.items():
            if 'gate_length' in props:
                gate_length = props['gate_length'][0]
                # TODO: Needs to check if total gate duration exceeds the input tau_c
                # If so, raise error
                tau_step_totals[qubit[0]] = self.tau_c - int(self.N * round(gate_length / self.dt))

                t_i = [int(round(tau_step_totals[qubit[0]] * \
                                (sin(pi * i / (2 * (self.N + 1)))) ** 2)) \
                                for i in range(self.N + 2)]

                tau_steps_dict[qubit[0]] = [t_i[i] - t_i[i-1] for i in range(1, self.N + 2)]
                # TODO: Maybe check if each tau step is 0, but makes error checking
                # complicated in case of overflow of sum
                # TODO: Also maybe check if sum(tau_steps) > udd_duration due to rounding up
                # too frequently

        new_dag = DAGCircuit()

        for qreg in dag.qregs.values():
            new_dag.add_qreg(qreg)
        for creg in dag.cregs.values():
            new_dag.add_creg(creg)
            
        for node in dag.topological_op_nodes():

            if isinstance(node.op, Delay):
                delay_duration = node.op.duration
                udd_duration = tau_step_totals[node.qargs[0].index]

                if self.tau_c <= delay_duration:
                    tau_steps = tau_steps_dict[node.qargs[0].index]
                    count = int(delay_duration // self.tau_c)
                    remainder = udd_duration - sum(tau_steps)
                    parity = 1 if (delay_duration - count * self.tau_c + count * remainder) % 2 \
                               else 0
                    new_delay = int((delay_duration - count * self.tau_c + count * remainder) / 2)

                    new_dag.apply_operation_back(Delay(new_delay), qargs=node.qargs)

                    for _ in range(count):
                        new_dag.apply_operation_back(Delay(tau_steps[0]), qargs=node.qargs)
                        for tau_step in tau_steps[1:]:
                            new_dag.apply_operation_back(YGate(), qargs=node.qargs)
                            new_dag.apply_operation_back(Delay(tau_step), qargs=node.qargs)


                    new_dag.apply_operation_back(Delay(new_delay + parity), qargs=node.qargs)

                else:
                    new_dag.apply_operation_back(Delay(delay_duration), qargs=node.qargs)

            else:
                new_dag.apply_operation_back(node.op, node.qargs, node.cargs, node.condition)

        return new_dag
