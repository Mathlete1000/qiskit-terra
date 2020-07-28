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

"""Tests CDD Pass"""

from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.passes import CDDPass
from qiskit.test import QiskitTestCase
from qiskit.test.mock import FakeAlmaden

class TestCDD(QiskitTestCase):
    """Test the CDD pass."""

    def setUp(self):
        self.backend = FakeAlmaden()
        self.dt_in_sec = self.backend.configuration().dt
        self.backend_prop = self.backend.properties()

    def test_cdd_1(self):
        """Test the CDD_1 pass.

        It should replace large enough delay blocks with CDD_1 sequences.
        except for the first delay block.
        """
        circuit = QuantumCircuit(1)
        circuit.delay(2000, 0)
        circuit.h(0)
        circuit.delay(2000, 0)
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(CDDPass(1, self.backend_prop, self.dt_in_sec))
        actual = pass_manager.run(circuit)
        
        expected = QuantumCircuit(1)
        expected.delay(2000, 0)
        expected.h(0)
        expected.delay(247, 0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(293, 0)
        expected.h(0)

        self.assertEqual(actual, expected)

    def test_cdd_2(self):
        """Test the CDD_2 pass.

        It should replace large enough delay blocks with CDD_2 sequences.
        """
        circuit = QuantumCircuit(1)
        circuit.h(0)
        circuit.delay(7500, 0)
        circuit.h(0)
        circuit.delay(100, 0)
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(CDDPass(2, self.backend_prop, self.dt_in_sec))
        actual = pass_manager.run(circuit)
        
        expected = QuantumCircuit(1)
        expected.h(0)
        expected.delay(77, 0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(123, 0)
        expected.h(0)
        expected.delay(100, 0)
        expected.h(0)

        self.assertEqual(actual, expected)
