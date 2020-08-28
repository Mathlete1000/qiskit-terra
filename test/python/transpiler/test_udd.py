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

"""Tests Uhrig Dynamical Decoupling (UDD) Pass"""

from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.passes import UDDPass
from qiskit.test import QiskitTestCase
from qiskit.test.mock import FakeAlmaden
from numpy import pi

class TestUDD(QiskitTestCase):
    """Test the UDD pass."""

    def setUp(self):
        self.backend = FakeAlmaden()
        self.dt_in_sec = self.backend.configuration().dt
        self.backend_prop = self.backend.properties()

    def test_udd_2(self):
        """Test that the pass replaces large enough delay blocks with UDD_2 sequences.
        """
        circuit = QuantumCircuit(1)
        circuit.h(0)
        circuit.delay(2500, 0)
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(UDDPass(2, self.backend_prop, self.dt_in_sec))
        actual = pass_manager.run(circuit)
        
        expected = QuantumCircuit(1)
        expected.h(0)
        expected.delay(250, 0)
        expected.delay(340, 0)
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(680, 0)
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(340, 0)
        expected.delay(250, 0)
        expected.h(0)

        self.assertEqual(actual, expected)

    def test_udd_3(self):
        """Test that the pass replaces large enough delay blocks with UDD_3 sequences.
        """
        circuit = QuantumCircuit(1)
        circuit.delay(2000, 0)
        circuit.h(0)
        circuit.delay(3500, 0)
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(UDDPass(3, self.backend_prop, self.dt_in_sec))
        actual = pass_manager.run(circuit)
        
        expected = QuantumCircuit(1)
        expected.delay(2000, 0)
        expected.h(0)
        expected.delay(250, 0)
        expected.delay(299, 0)
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(721, 0)
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(721, 0)
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(299, 0)
        expected.delay(250, 0)
        expected.h(0)

        self.assertEqual(actual, expected)

    def test_udd_4(self):
        """Test that the pass replaces large enough delay blocks with UDD_4 sequences.
        """
        circuit = QuantumCircuit(1)
        circuit.h(0)
        circuit.delay(100, 0)
        circuit.x(0)
        circuit.delay(4500, 0)
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(UDDPass(4, self.backend_prop, self.dt_in_sec))
        actual = pass_manager.run(circuit)
        
        expected = QuantumCircuit(1)
        expected.h(0)
        expected.delay(100, 0)
        expected.x(0)
        expected.delay(250, 0)
        expected.delay(260, 0)
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(680, 0)
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(840, 0)
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(680, 0)
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(260, 0)
        expected.delay(250, 0)
        expected.h(0)

        self.assertEqual(actual, expected)
