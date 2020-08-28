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

"""Tests Concatentated Dynamical Decoupling (CDD) Pass"""

from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.passes import CDDPass
from qiskit.test import QiskitTestCase
from qiskit.test.mock import FakeAlmaden
from numpy import pi

class TestCDD(QiskitTestCase):
    """Test the CDD pass."""

    def setUp(self):
        self.backend = FakeAlmaden()
        self.backend_prop = self.backend.properties()
        self.gate_length = self.backend_prop._gates['u3'][(0,)]['gate_length'][0]

    def test_cdd_1(self):
        """Test that the pass replaces large enough delay blocks with CDD_1 sequences
           except for the first delay block.
        """
        circuit = QuantumCircuit(1)
        circuit.delay(4e-7, unit='s')
        circuit.h(0)
        circuit.delay(4e-7, unit='s')
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(CDDPass(1, self.backend_prop))
        actual = pass_manager.run(circuit)

        leftover_delay = (4e-7 - 4 * self.gate_length - 3 * 10e-9) / 2
        
        expected = QuantumCircuit(1)
        expected.delay(4e-7, unit='s')
        expected.h(0)
        expected.delay(leftover_delay, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(leftover_delay, 0, unit='s')
        expected.h(0)

        self.assertEqual(actual, expected)

    def test_cdd_2(self):
        """Test that the pass replaces large enough delay blocks with CDD_2 sequences.
        """
        circuit = QuantumCircuit(1)
        circuit.h(0)
        circuit.delay(20e-7, 0, unit='s')
        circuit.h(0)
        circuit.delay(1e-7, 0, unit='s')
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(CDDPass(2, self.backend_prop))
        actual = pass_manager.run(circuit)

        leftover_delay = (20e-7 - 20 * self.gate_length - 19 * 10e-9) / 2
        
        expected = QuantumCircuit(1)
        expected.h(0)
        expected.delay(leftover_delay, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, 0, pi, 0)
        expected.delay(10e-9, 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(leftover_delay, 0, unit='s')
        expected.h(0)
        expected.delay(1e-7, 0, unit='s')
        expected.h(0)

        self.assertEqual(actual, expected)
