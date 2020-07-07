# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=missing-function-docstring

"""Test scheduled circuit (quantum circuit with duration)."""
# import unittest

from qiskit import QuantumCircuit, transpile, execute, QiskitError
from qiskit.circuit import Parameter
from qiskit.test.mock.backends import FakeParis
from qiskit.transpiler.exceptions import TranspilerError

from qiskit.test.base import QiskitTestCase


class TestScheduledCircuit(QiskitTestCase):
    """Test scheduled circuit (quantum circuit with duration)."""
    def setUp(self):
        self.backend = FakeParis()

    def test_cannot_execute_delay_circuit_when_schedule_circuit_off(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.delay(500, 1)
        qc.cx(0, 1)
        with self.assertRaises(QiskitError):
            execute(qc, backend=self.backend, schedule_circuit=False)

    def test_transpile_t1_circuit(self):
        qc = QuantumCircuit(1)
        qc.x(0)  # 320
        qc.delay(1000, 0)
        qc.measure_all()  # 19200
        scheduled = transpile(qc, backend=self.backend, scheduling_method='alap')
        self.assertEqual(scheduled.duration, 20520)

    def test_transpile_delay_circuit_with_backend(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.delay(500, 1)
        qc.cx(0, 1)
        scheduled = transpile(qc, backend=self.backend, scheduling_method='alap')
        self.assertEqual(scheduled.duration, 1908)

    def test_transpile_delays_circuit_without_backend(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.delay(500, 1)
        qc.cx(0, 1)
        scheduled = transpile(qc,
                              scheduling_method='alap',
                              basis_gates=['h', 'cx'],
                              instruction_durations=[('h', 0, 200), ('cx', [0, 1], 700)]
                              )
        self.assertEqual(scheduled.duration, 1200)

    def test_raise_error_if_transpile_circuit_with_delay_without_scheduling_method(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.delay(500, 1)
        qc.cx(0, 1)
        with self.assertRaises(TranspilerError):
            transpile(qc)

    def test_raise_error_if_transpile_with_scheduling_method_but_without_backend(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.delay(500, 1)
        qc.cx(0, 1)
        with self.assertRaises(TranspilerError):
            transpile(qc, scheduling_method="alap")

    def test_invalidate_schedule_circuit_if_new_instruction_is_appended(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.delay(500, 1)
        qc.cx(0, 1)
        scheduled = transpile(qc,
                              backend=self.backend,
                              scheduling_method='alap')
        # append a gate to a scheduled circuit
        scheduled.h(0)
        self.assertEqual(scheduled.duration, None)

    def test_accept_bound_parameter_for_duration_of_delay(self):
        param_duration = Parameter("T")
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.delay(param_duration, 0)
        qc.h(0)
        qc = qc.bind_parameters({param_duration: 500})
        scheduled = transpile(qc, scheduling_method='alap',
                              basis_gates=['u2'], instruction_durations=[('u2', 0, 200)])
        self.assertEqual(scheduled.duration, 900)

    def test_reject_unbound_parameter_for_duration_of_delay(self):
        param_duration = Parameter("T")
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.delay(param_duration, 0)
        qc.h(0)
        # not bind parameter
        with self.assertRaises(TranspilerError):
            transpile(qc, scheduling_method='alap',
                      basis_gates=['u2'], instruction_durations=[('u2', 0, 200)])

    def test_instruction_durations_option_in_transpile(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.delay(500, 1)
        qc.cx(0, 1)
        # overwrite backend's durations
        scheduled = transpile(qc,
                              backend=self.backend,
                              scheduling_method='alap',
                              instruction_durations=[('cx', [0, 1], 1000)]
                              )
        self.assertEqual(scheduled.duration, 1500)
        # accept None for qubits
        scheduled = transpile(qc,
                              basis_gates=['h', 'cx', 'delay'],
                              scheduling_method='alap',
                              instruction_durations=[('h', 0, 200),
                                                     ('cx', None, 900)]
                              )
        self.assertEqual(scheduled.duration, 1400)
        # prioritize specified qubits over None
        scheduled = transpile(qc,
                              basis_gates=['h', 'cx', 'delay'],
                              scheduling_method='alap',
                              instruction_durations=[('h', 0, 200),
                                                     ('cx', None, 900),
                                                     ('cx', [0, 1], 800)]
                              )
        self.assertEqual(scheduled.duration, 1300)