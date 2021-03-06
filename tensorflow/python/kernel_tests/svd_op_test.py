# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
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
# ==============================================================================
"""Tests for tensorflow.ops.math_ops.matrix_inverse."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import tensorflow as tf


class SvdOpTest(tf.test.TestCase):

  def testWrongDimensions(self):
    # The input to svd should be 2-dimensional tensor.
    scalar = tf.constant(1.)
    with self.assertRaises(ValueError):
      tf.svd(scalar)
    vector = tf.constant([1., 2.])
    with self.assertRaises(ValueError):
      tf.svd(vector)
    tensor = tf.constant([[[1., 2.], [3., 4.]], [[1., 2.], [3., 4.]]])
    with self.assertRaises(ValueError):
      tf.svd(tensor)
    scalar = tf.constant(1. + 1.0j)
    with self.assertRaises(ValueError):
      tf.svd(scalar)
    vector = tf.constant([1. + 1.0j, 2. + 2.0j])
    with self.assertRaises(ValueError):
      tf.svd(vector)
    tensor = tf.constant([[[1. + 1.0j, 2. + 2.0j], [3. + 3.0j, 4. + 4.0j]],
                          [[1. + 1.0j, 2. + 2.0j], [3. + 3.0j, 4. + 4.0j]]])
    with self.assertRaises(ValueError):
      tf.svd(tensor)

    # The input to batch_svd should be a tensor of at least rank 2.
    scalar = tf.constant(1.)
    with self.assertRaises(ValueError):
      tf.batch_svd(scalar)
    vector = tf.constant([1., 2.])
    with self.assertRaises(ValueError):
      tf.batch_svd(vector)
    scalar = tf.constant(1. + 1.0j)
    with self.assertRaises(ValueError):
      tf.batch_svd(scalar)
    vector = tf.constant([1. + 1.0j, 2. + 2.0j])
    with self.assertRaises(ValueError):
      tf.batch_svd(vector)


def _GetSvdOpTest(dtype_, shape_):

  def CompareSingularValues(self, x, y):
    if dtype_ in (np.float32, np.complex64):
      tol = 5e-5
    else:
      tol = 1e-14
    self.assertAllClose(np.real(x), np.real(y),
                        atol=(np.real(x)[0] + np.real(y)[0]) * tol)
    self.assertAllClose(np.imag(x), np.imag(y),
                        atol=(np.imag(x)[0] + np.imag(y)[0]) * tol)

  def CompareSingularVectors(self, x, y, rank):
    if dtype_ in (np.float32, np.complex64):
      atol = 5e-4
    else:
      atol = 1e-14
    # We only compare the first 'rank' singular vectors since the
    # remainder form an arbitrary orthonormal basis for the
    # (row- or column-) null space, whose exact value depends on
    # implementation details. Notice that since we check that the
    # matrices of singular vectors are unitary elsewhere, we do
    # implicitly test that the trailing vectors of x and y span the
    # same space.
    x = x[..., 0:rank]
    y = y[..., 0:rank]
    # Singular vectors are only unique up to sign (complex phase factor for
    # complex matrices), so we normalize the signs first.
    if dtype_ in (np.float32, np.float64):
      signs = np.sign(np.sum(np.divide(x, y), -2, keepdims=True))
      x *= signs
      self.assertAllClose(x, y, atol=atol)
    else:
      phases = np.divide(np.sum(np.divide(y, x), -2, keepdims=True),
                         np.abs(np.sum(np.divide(y, x), -2, keepdims=True)))
      x *= phases
      self.assertAllClose(np.real(x), np.real(y), atol=atol)
      self.assertAllClose(np.imag(x), np.imag(y), atol=atol)

  def CheckApproximation(self, a, u, s, v, full_matrices):
    if dtype_ in (np.float32, np.complex64):
      tol = 1e-5
    else:
      tol = 1e-14
    # Tests that a ~= u*diag(s)*transpose(v).
    batch_shape = a.shape[:-2]
    m = a.shape[-2]
    n = a.shape[-1]
    diag_s = tf.cast(tf.batch_matrix_diag(s), dtype=dtype_)
    if full_matrices:
      if m > n:
        zeros = tf.zeros(batch_shape + (m - n, n), dtype=dtype_)
        diag_s = tf.concat(a.ndim - 2, [diag_s, zeros])
      elif n > m:
        zeros = tf.zeros(batch_shape + (m, n - m), dtype=dtype_)
        diag_s = tf.concat(a.ndim - 1, [diag_s, zeros])
    a_recon = tf.batch_matmul(tf.cast(u, dtype=dtype_),
                              tf.cast(diag_s, dtype=dtype_))
    a_recon = tf.batch_matmul(a_recon, tf.cast(v, dtype=dtype_), adj_y=True)
    self.assertAllClose(np.real(a_recon.eval()),
                        np.real(a), rtol=tol, atol=tol)
    self.assertAllClose(np.imag(a_recon.eval()),
                        np.imag(a), rtol=tol, atol=tol)

  def CheckUnitary(self, x):
    # Tests that x[...,:,:]^H * x[...,:,:] is close to the identity.
    xx = tf.batch_matmul(x, x, adj_x=True)
    identity = tf.batch_matrix_band_part(tf.ones_like(xx), 0, 0)
    if dtype_ in (np.float32, np.complex64):
      tol = 1e-5
    else:
      tol = 1e-14
    self.assertAllClose(np.real(identity.eval()),
                        np.real(xx.eval()), atol=tol)
    self.assertAllClose(np.imag(identity.eval()),
                        np.imag(xx.eval()), atol=tol)

  def Test(self):
    np.random.seed(1)
    if dtype_ in (np.float32, np.float64):
      x = np.random.uniform(low=-1.0, high=1.0,
                            size=np.prod(shape_)).reshape(shape_).astype(dtype_)
    elif dtype == np.complex64:
      x = np.random.uniform(low=-1.0, high=1.0,
                        size=np.prod(shape_)).reshape(shape_).astype(np.float32)
      + 1j * np.random.uniform(low=-1.0, high=1.0,
                        size=np.prod(shape_)).reshape(shape_).astype(np.float32)
    else:
      x = np.random.uniform(low=-1.0, high=1.0,
                        size=np.prod(shape_)).reshape(shape_).astype(np.float64)
      + 1j * np.random.uniform(low=-1.0, high=1.0,
                        size=np.prod(shape_)).reshape(shape_).astype(np.float64)
    for compute_uv in False, True:
      for full_matrices in False, True:
        with self.test_session():
          if x.ndim == 2:
            if compute_uv:
              tf_s, tf_u, tf_v = tf.svd(tf.constant(x),
                                        compute_uv=compute_uv,
                                        full_matrices=full_matrices)
            else:
              tf_s = tf.svd(tf.constant(x),
                            compute_uv=compute_uv,
                            full_matrices=full_matrices)
          else:
            if compute_uv:
              tf_s, tf_u, tf_v = tf.batch_svd(
                  tf.constant(x),
                  compute_uv=compute_uv,
                  full_matrices=full_matrices)
            else:
              tf_s = tf.batch_svd(
                  tf.constant(x),
                  compute_uv=compute_uv,
                  full_matrices=full_matrices)
          if compute_uv:
            np_u, np_s, np_v = np.linalg.svd(x,
                                             compute_uv=compute_uv,
                                             full_matrices=full_matrices)
          else:
            np_s = np.linalg.svd(x,
                                 compute_uv=compute_uv,
                                 full_matrices=full_matrices)
          CompareSingularValues(self, np_s, tf_s.eval())
          if compute_uv:
            CompareSingularVectors(self, np_u, tf_u.eval(), min(shape_[-2:]))
            CompareSingularVectors(self, np.swapaxes(np_v, -2, -1), tf_v.eval(),
                                   min(shape_[-2:]))
            CheckApproximation(self, x, tf_u, tf_s, tf_v, full_matrices)
            CheckUnitary(self, tf_u)
            CheckUnitary(self, tf_v)

  return Test


if __name__ == '__main__':
  for dtype in np.float32, np.float64, np.complex64, np.complex128:
    for rows in 1, 2, 5, 10, 32, 100:
      for cols in 1, 2, 5, 10, 32, 100:
        for batch_dims in [(), (3,)] + [(3, 2)] * (max(rows, cols) < 10):
          shape = batch_dims + (rows, cols)
          name = '%s_%s' % (dtype.__name__, '_'.join(map(str, shape)))
          setattr(SvdOpTest, 'testSvd_' + name, _GetSvdOpTest(dtype, shape))
  tf.test.main()
