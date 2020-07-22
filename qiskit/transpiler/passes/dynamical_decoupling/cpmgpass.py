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
        new_dag = DAGCircuit()

        return new_dag