# Copyright 2018 The TensorFlow Probability Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Tests for TensorFlow Probability ODE solvers."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import parameterized
import numpy as np
import tensorflow.compat.v2 as tf
import tensorflow_probability as tfp


from tensorflow_probability.python.internal import test_case
from tensorflow.python.framework import test_util  # pylint: disable=g-direct-tensorflow-import
_RTOL = 1e-8
_ATOL = 1e-12


@test_util.run_all_in_graph_and_eager_modes
@parameterized.named_parameters([
    ('bdf', tfp.math.ode.BDF),
    ('dormand_prince', tfp.math.ode.DormandPrince)])
class NonStiffTest(parameterized.TestCase, test_case.TestCase):

  def test_zero_dims(self, solver):
    ode_fn = lambda time, state: -state
    initial_time = 0.
    initial_state = np.float64(1.)
    jacobian = np.float64([[-1.]])
    solver_instance = solver(rtol=_RTOL, atol=_ATOL)
    results = solver_instance.solve(
        ode_fn,
        initial_time,
        initial_state,
        solution_times=tfp.math.ode.ChosenBySolver(1.),
        jacobian_fn=jacobian)
    times, states = self.evaluate([results.times, results.states])
    states_exact = np.exp(-times) * initial_state
    self.assertAllClose(states, states_exact)

  def test_state_with_matrix_shape(self, solver):
    ode_fn = lambda time, state: -state
    initial_time = 0.
    initial_state = np.float64([[1., 2.], [3., 4.]])
    jacobian = np.reshape(
        np.diag(-np.ones([4])),
        np.concatenate([initial_state.shape, initial_state.shape]))
    solver_instance = solver(rtol=_RTOL, atol=_ATOL)
    results = solver_instance.solve(
        ode_fn,
        initial_time,
        initial_state,
        solution_times=tfp.math.ode.ChosenBySolver(1.),
        jacobian_fn=jacobian)
    times, states = self.evaluate([results.times, results.states])
    states_exact = np.exp(-times)[:, np.newaxis, np.newaxis] * initial_state
    self.assertAllClose(states, states_exact)

  def test_ode_fn_is_zero(self, solver):
    initial_time = 0.
    initial_state = np.float64([1., 2., 3.])
    ode_fn = lambda time, state: np.zeros_like(initial_state)
    jacobian = np.zeros((3, 3), dtype=np.float64)
    solver_instance = solver(rtol=_RTOL, atol=_ATOL)
    results = solver_instance.solve(
        ode_fn,
        initial_time,
        initial_state,
        solution_times=tfp.math.ode.ChosenBySolver(1.),
        jacobian_fn=jacobian)
    times, states = self.evaluate([results.times, results.states])
    states_exact = np.ones([times.size, initial_state.size]) * initial_state
    self.assertAllClose(states, states_exact)

  def test_linear(self, solver):
    jacobian_diag_part = np.float64([-0.5, -1.])
    ode_fn = lambda time, state: jacobian_diag_part * state
    initial_time = 0.
    initial_state = np.float64([1., 2.])
    jacobian = np.diag(jacobian_diag_part)
    solver_instance = solver(rtol=_RTOL, atol=_ATOL)
    results = solver_instance.solve(
        ode_fn,
        initial_time,
        initial_state,
        solution_times=tfp.math.ode.ChosenBySolver(1.),
        jacobian_fn=jacobian)
    times, states = self.evaluate([results.times, results.states])
    states_exact = np.exp(jacobian_diag_part[np.newaxis, :] *
                          times[:, np.newaxis]) * initial_state
    self.assertAllClose(states, states_exact)

  def test_linear_jacobian_fn_unspecified(self, solver):
    jacobian_diag_part = np.float64([-0.5, -1.])
    ode_fn = lambda time, state: jacobian_diag_part * state
    initial_time = 0.
    initial_state = np.float64([1., 2.])
    solver_instance = solver(rtol=_RTOL, atol=_ATOL)
    results = solver_instance.solve(
        ode_fn,
        initial_time,
        initial_state,
        solution_times=tfp.math.ode.ChosenBySolver(1.))
    times, states = self.evaluate([results.times, results.states])
    states_exact = np.exp(jacobian_diag_part[np.newaxis, :] *
                          times[:, np.newaxis]) * initial_state
    self.assertAllClose(states, states_exact)

  def test_linear_complex(self, solver):
    jacobian_diag_part = np.complex128([1j - 0.1, 1j])
    ode_fn = lambda time, state: jacobian_diag_part * state
    initial_time = 0.
    initial_state = np.complex128([1., 2.])
    jacobian = np.diag(jacobian_diag_part)
    solver_instance = solver(rtol=_RTOL, atol=_ATOL)
    results = solver_instance.solve(
        ode_fn,
        initial_time,
        initial_state,
        solution_times=tfp.math.ode.ChosenBySolver(1.),
        jacobian_fn=jacobian)
    times, states = self.evaluate([results.times, results.states])
    states_exact = np.exp(jacobian_diag_part[np.newaxis, :] *
                          times[:, np.newaxis]) * initial_state
    self.assertAllClose(states, states_exact)

  def test_linear_dense(self, solver):
    np.random.seed(0)
    initial_time = 0.
    num_odes = 20
    initial_state = np.float64([1.] * num_odes)
    jacobian = np.random.randn(num_odes, num_odes)

    def ode_fn(_, state):
      return tf.squeeze(tf.matmul(jacobian, state[:, tf.newaxis]))

    final_time = 1.
    solver_instance = solver(rtol=_RTOL, atol=_ATOL)
    results = solver_instance.solve(
        ode_fn,
        initial_time,
        initial_state,
        solution_times=[final_time],
        jacobian_fn=jacobian)
    final_state = self.evaluate(results.states[-1])
    # Exact solution is obtained by diagonalizing the Jacobian by
    # `jacobian = V diag(w) V^{-1}` and making the change of variables `Vz = y`.
    eigvals, eigvecs = np.linalg.eig(jacobian)
    initial_state_changed = np.matmul(np.linalg.inv(eigvecs), initial_state)
    final_state_changed_exact = np.exp(
        eigvals * final_time) * initial_state_changed
    final_state_exact = np.matmul(eigvecs, final_state_changed_exact)
    self.assertAllClose(final_state, final_state_exact)

  def test_riccati(self, solver):
    ode_fn = lambda time, state: (state - time)**2 + 1.
    initial_time = 0.
    initial_state = np.float64(0.5)
    jacobian_fn = lambda time, state: 2. * (state - time)
    solver_instance = solver(rtol=_RTOL, atol=_ATOL)
    results = solver_instance.solve(
        ode_fn,
        initial_time,
        initial_state,
        solution_times=tfp.math.ode.ChosenBySolver(1.),
        jacobian_fn=jacobian_fn)
    times, states = self.evaluate([results.times, results.states])
    states_exact = (1. / (1. / initial_state - times) + times)
    self.assertAllClose(states, states_exact)


@test_util.run_all_in_graph_and_eager_modes
@parameterized.named_parameters([('bdf', tfp.math.ode.BDF)])
class StiffTest(parameterized.TestCase, test_case.TestCase):

  def test_van_der_pol(self, solver):

    def ode_fn(_, state):
      return tf.stack([
          state[1],
          1000. * (1. - state[0]**2) * state[1] - state[0],
      ])

    def jacobian_fn(_, state):
      return tf.stack([
          [0., 1.],
          [-2000. * state[0] * state[1] - 1., 1000. * (1. - state[0]**2)],
      ])

    initial_time = 0.
    initial_state = np.float64([2., 0.])
    solver_instance = solver(rtol=1e-3, atol=1e-6)
    results = solver_instance.solve(
        ode_fn,
        initial_time,
        initial_state,
        solution_times=[3000.],
        jacobian_fn=jacobian_fn)
    self.assertAllClose(
        self.evaluate(results.states[-1, 0]), -1.5, rtol=0., atol=0.05)


@parameterized.named_parameters([
    ('bdf', tfp.math.ode.BDF),
    ('dormand_prince', tfp.math.ode.DormandPrince)])
class GradientTest(parameterized.TestCase, test_case.TestCase):

  def test_linear_dense(self, solver):
    initial_time = 0.
    jacobian = -np.float64([[1., 2., 3.], [4., 5., 6.], [7., 8., 9.]])
    num_odes = jacobian.shape[0]
    initial_state_value = np.float64([1.] * num_odes)
    initial_state = tf.constant(initial_state_value, dtype=tf.float64)

    def ode_fn(_, state):
      return tf.squeeze(tf.matmul(jacobian, state[:, tf.newaxis]))

    intermediate_time = 1.
    final_time = 2.
    solver_instance = solver(rtol=_RTOL, atol=_ATOL)
    with tf.GradientTape() as tape:
      tape.watch(initial_state)
      results = solver_instance.solve(
          ode_fn,
          initial_time,
          initial_state,
          solution_times=[intermediate_time, final_time])
      intermediate_state = results.states[0]
    grad = self.evaluate(tape.gradient(intermediate_state, initial_state))
    matrix_exponential_of_jacobian = np.float64(
        [[+2.3703878775011322, +0.2645063729368097, -0.8413751316275110],
         [-0.0900545996427410, +0.7326649140674798, -0.4446155722222950],
         [-1.5504970767866180, -0.7991765448018465, +0.9521439871829201]])
    grad_exact = np.dot(np.ones([num_odes]), matrix_exponential_of_jacobian)
    self.assertAllClose(grad, grad_exact)

  def test_riccati(self, solver):
    ode_fn = lambda time, state: (state - time)**2 + 1.
    initial_time = 0.
    initial_state_value = 0.5
    initial_state = tf.constant(initial_state_value, dtype=tf.float64)
    final_time = 1.
    jacobian_fn = lambda time, state: 2. * (state - time)
    solver_instance = solver(rtol=_RTOL, atol=_ATOL)
    with tf.GradientTape() as tape:
      tape.watch(initial_state)
      results = solver_instance.solve(
          ode_fn,
          initial_time,
          initial_state,
          solution_times=[final_time],
          jacobian_fn=jacobian_fn)
      final_state = results.states[-1]
    grad = self.evaluate(tape.gradient(final_state, initial_state))
    grad_exact = 1. / (1. - initial_state_value * final_time)**2
    self.assertAllClose(grad, grad_exact, rtol=1e-3, atol=1e-3)


@test_util.run_all_in_graph_and_eager_modes
@parameterized.named_parameters([
    ('bdf', tfp.math.ode.BDF),
    ('dormand_prince', tfp.math.ode.DormandPrince)])
class GeneralTest(parameterized.TestCase, test_case.TestCase):

  def test_bad_initial_state_dtype(self, solver):
    ode_fn = lambda time, state: -state
    initial_time = 0.
    initial_state = np.int32(1)
    with self.assertRaisesRegexp(
        TypeError, ('`initial_state` must have a floating point or complex '
                    'floating point dtype')):
      solver(validate_args=True).solve(
          ode_fn, initial_time, initial_state, solution_times=[1.])

  def test_diagnostics(self, solver):
    ode_fn = lambda time, state: -state
    initial_time = 0.
    initial_state = np.float64(1.)
    results = solver(validate_args=True).solve(
        ode_fn, initial_time, initial_state, solution_times=[1.])
    (
        num_ode_fn_evaluations,
        num_jacobian_evaluations,
        num_matrix_factorizations,
        status,
    ) = self.evaluate([
        results.diagnostics.num_ode_fn_evaluations,
        results.diagnostics.num_jacobian_evaluations,
        results.diagnostics.num_matrix_factorizations,
        results.diagnostics.status,
    ])
    self.assertEqual(status, 0)
    self.assertGreater(num_ode_fn_evaluations, 0)
    self.assertGreaterEqual(num_jacobian_evaluations, 0)
    self.assertGreaterEqual(num_matrix_factorizations, 0)

  def test_previous_solver_internal_state(self, solver):
    jacobian_diag_part = np.float64([-0.5, -1.])
    ode_fn = lambda time, state: jacobian_diag_part * state
    initial_time = 0.
    initial_state = np.float64([1., 2.])
    intermediate_time = 1.
    final_time = 2.
    solver_instance = solver(rtol=_RTOL, atol=_ATOL, validate_args=True)
    previous_results = solver_instance.solve(
        ode_fn,
        initial_time,
        initial_state,
        solution_times=tfp.math.ode.ChosenBySolver(intermediate_time))
    results = solver_instance.solve(
        ode_fn,
        intermediate_time,
        previous_results.states[-1],
        solution_times=tfp.math.ode.ChosenBySolver(final_time),
        previous_solver_internal_state=previous_results.solver_internal_state)
    times, states = self.evaluate([results.times, results.states])
    states_exact = np.exp(jacobian_diag_part[np.newaxis, :] *
                          times[:, np.newaxis]) * initial_state
    self.assertAllClose(states, states_exact)


if __name__ == '__main__':
  tf.test.main()
