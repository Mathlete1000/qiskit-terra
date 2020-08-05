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
from qiskit.circuit.library.standard_gates import YGate
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass

from math import sin, pi

class NUDDPass(TransformationPass):
    """NUDD Pass"""

    def __init__(self, backend_properties, dt_in_sec, tau_c=None):
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
        # self.N = N
        self.backend_properties = backend_properties
        self.dt = dt_in_sec
        self.tau_c = 2000 if not tau_c else tau_c

    def run(self, dag):
        """Run the NUDD pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to new DAG.

        Returns:
            DAGCircuit: A new DAG with NUDD Sequences inserted in large 
                        enough delays.
        """
        new_dag = DAGCircuit()

        # new_dag.name = dag.name
        # new_dag.instruction_durations = dag.instruction_durations

        return None