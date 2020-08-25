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

"""Tests CPMG Dynamical Decoupling Pass"""

from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.passes import CPMGPass
from qiskit.test import QiskitTestCase
from qiskit.test.mock import FakeAlmaden

class TestCPMG(QiskitTestCase):
    """Test the CPMG DD pass."""

    def setUp(self):
        self.backend = FakeAlmaden()
        self.dt_in_sec = self.backend.configuration().dt
        self.backend_prop = self.backend.properties()

    def test_cpmg_simple(self):
        """Test that the pass replaces large enough delay blocks with CPMG DD sequences.
        """
        circuit = QuantumCircuit(1)
        circuit.h(0)
        circuit.delay(2500)
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(CPMGPass(self.backend_prop, self.dt_in_sec))
        actual = pass_manager.run(circuit)
        
        expected = QuantumCircuit(1)
        expected.h(0)
        expected.delay(250, 0)
        expected.delay(340, 0)
        expected.y(0)
        expected.delay(680, 0)
        expected.y(0)
        expected.delay(340, 0)
        expected.delay(250, 0)
        expected.h(0)

        self.assertEqual(actual, expected)

    def test_cpmg_multiple(self):
        """Test that the pass replaces large enough delay blocks with multiple CPMG DD sequences.
        """
        circuit = QuantumCircuit(1)
        circuit.h(0)
        circuit.delay(7500)
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(CPMGPass(self.backend_prop, self.dt_in_sec))
        actual = pass_manager.run(circuit)
        
        expected = QuantumCircuit(1)
        expected.h(0)
        expected.delay(750, 0)
        for _ in range(3):
            expected.delay(340, 0)
            expected.y(0)
            expected.delay(680, 0)
            expected.y(0)
            expected.delay(340, 0)
        expected.delay(750, 0)
        expected.h(0)

        self.assertEqual(actual, expected)

    def test_cpmg_not_first(self):
        """Test that the pass replaces large enough delay blocks with CPMG DD sequences except 
        for the first delay block.
        """
        circuit = QuantumCircuit(1)
        circuit.delay(2000)
        circuit.h(0)
        circuit.delay(2500)
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(CPMGPass(self.backend_prop, self.dt_in_sec))
        actual = pass_manager.run(circuit)
        
        expected = QuantumCircuit(1)
        expected.delay(2000, 0)
        expected.h(0)
        expected.delay(250, 0)
        expected.delay(340, 0)
        expected.y(0)
        expected.delay(680, 0)
        expected.y(0)
        expected.delay(340, 0)
        expected.delay(250, 0)
        expected.h(0)

        self.assertEqual(actual, expected)
