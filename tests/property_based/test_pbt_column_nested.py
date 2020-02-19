from collections import defaultdict

import pytest
import numpy as np

from conftest import (
    variable_shape_backend_params,
    fixed_shape_backend_params,
    str_variable_shape_backend_params
)

import string
from hypothesis import given, settings, HealthCheck
import hypothesis.strategies as st
from hypothesis.extra import numpy as npst

from hangar import Repository


# ------------------------ Fixture Setup ------------------------------


added_samples_subsamples = defaultdict(set)


@pytest.fixture(params=fixed_shape_backend_params)
def fixed_shape_repo_co_float32_aset_nested(managed_tmpdir, request) -> Repository:
    # needed because fixtures don't reset between each hypothesis run
    # tracks added_samples_subsamples[sample_key] = set(subsample_keys)
    global added_samples_subsamples
    added_samples_subsamples = defaultdict(set)
    repo_obj = Repository(path=managed_tmpdir, exists=False)
    repo_obj.init(user_name='tester', user_email='foo@test.bar', remove_old=True)
    co = repo_obj.checkout(write=True)
    co.columns.create_ndarray_column(name='writtenaset',
                                     shape=(5, 5, 5),
                                     dtype=np.float32,
                                     variable_shape=False,
                                     contains_subsamples=True,
                                     backend=request.param)
    yield co
    co.close()
    repo_obj._env._close_environments()


@pytest.fixture(params=variable_shape_backend_params)
def variable_shape_repo_co_float32_aset_nested(managed_tmpdir, request) -> Repository:
    # needed because fixtures don't reset between each hypothesis run
    # tracks added_samples_subsamples[sample_key] = set(subsample_keys)
    global added_samples_subsamples
    added_samples_subsamples = defaultdict(set)
    repo_obj = Repository(path=managed_tmpdir, exists=False)
    repo_obj.init(user_name='tester', user_email='foo@test.bar', remove_old=True)
    co = repo_obj.checkout(write=True)
    co.columns.create_ndarray_column(name='writtenaset',
                                     shape=(5, 5, 5),
                                     dtype=np.float32,
                                     variable_shape=True,
                                     contains_subsamples=True,
                                     backend=request.param)
    yield co
    co.close()
    repo_obj._env._close_environments()


@pytest.fixture(params=variable_shape_backend_params)
def variable_shape_repo_co_uint8_aset_nested(managed_tmpdir, request) -> Repository:
    # needed because fixtures don't reset between each hypothesis run
    # tracks added_samples_subsamples[sample_key] = set(subsample_keys)
    global added_samples_subsamples
    added_samples_subsamples = defaultdict(set)
    repo_obj = Repository(path=managed_tmpdir, exists=False)
    repo_obj.init(user_name='tester', user_email='foo@test.bar', remove_old=True)
    co = repo_obj.checkout(write=True)
    co.columns.create_ndarray_column(name='writtenaset',
                                     shape=(5, 5, 5),
                                     dtype=np.uint8,
                                     variable_shape=True,
                                     contains_subsamples=True,
                                     backend=request.param)
    yield co
    co.close()
    repo_obj._env._close_environments()


@pytest.fixture(params=str_variable_shape_backend_params)
def variable_shape_repo_co_str_aset_nested(managed_tmpdir, request) -> Repository:
    # needed because fixtures don't reset between each hypothesis run
    # tracks added_samples = set(sample_key)
    global added_samples_subsamples
    added_samples_subsamples = defaultdict(set)
    repo_obj = Repository(path=managed_tmpdir, exists=False)
    repo_obj.init(user_name='tester', user_email='foo@test.bar', remove_old=True)
    co = repo_obj.checkout(write=True)
    co.columns.create_str_column(name='strcolumn',
                                 contains_subsamples=True,
                                 backend=request.param)
    yield co
    co.close()
    repo_obj._env._close_environments()


# -------------------------- Test Generation ---------------------------------

st_valid_names = st.text(
    min_size=1, max_size=16, alphabet=string.ascii_letters + string.digits + '_-.')
st_valid_ints = st.integers(min_value=0, max_value=999_999)
st_valid_keys = st.one_of(st_valid_ints, st_valid_names)


valid_arrays_fixed = npst.arrays(np.float32,
                                 shape=(5, 5, 5),
                                 fill=st.floats(min_value=-10,
                                                max_value=10,
                                                allow_nan=False,
                                                allow_infinity=False,
                                                width=32),
                                 elements=st.floats(min_value=-10,
                                                    max_value=10,
                                                    allow_nan=False,
                                                    allow_infinity=False,
                                                    width=32))


@given(key=st_valid_keys, subkey=st_valid_keys, val=valid_arrays_fixed)
@settings(max_examples=200, deadline=200.0, suppress_health_check=[HealthCheck.too_slow])
def test_arrayset_fixed_key_values_nested(key, subkey, val, fixed_shape_repo_co_float32_aset_nested):
    global added_samples_subsamples

    added_samples_subsamples[key].add(subkey)

    co = fixed_shape_repo_co_float32_aset_nested
    col = co.columns['writtenaset']
    assert col.schema_type == 'fixed_shape'
    assert col.contains_subsamples is True
    col[key] = {subkey: val}
    out = col[key][subkey]

    assert len(col) == len(added_samples_subsamples)
    assert len(col[key]) == len(added_samples_subsamples[key])
    assert out.dtype == val.dtype
    assert out.shape == val.shape
    assert np.allclose(out, val)


valid_shapes_var = npst.array_shapes(min_dims=3, max_dims=3, min_side=1, max_side=5)
valid_arrays_var_float32 = npst.arrays(np.float32,
                                       shape=valid_shapes_var,
                                       fill=st.floats(min_value=-10,
                                                      max_value=10,
                                                      allow_nan=False,
                                                      allow_infinity=False,
                                                      width=32),
                                       elements=st.floats(min_value=-10,
                                                          max_value=10,
                                                          allow_nan=False,
                                                          allow_infinity=False,
                                                          width=32))


@given(key=st_valid_keys, subkey=st_valid_keys, val=valid_arrays_var_float32)
@settings(max_examples=200, deadline=200.0, suppress_health_check=[HealthCheck.too_slow])
def test_arrayset_variable_shape_float32_nested(key, val, subkey, variable_shape_repo_co_float32_aset_nested):
    global added_samples_subsamples

    co = variable_shape_repo_co_float32_aset_nested
    col = co.columns['writtenaset']
    assert col.schema_type == 'variable_shape'
    assert col.contains_subsamples is True
    col[key] = {subkey: val}
    out = col[key][subkey]
    added_samples_subsamples[key].add(subkey)

    assert len(col) == len(added_samples_subsamples)
    assert len(col[key]) == len(added_samples_subsamples[key])
    assert out.dtype == val.dtype
    assert out.shape == val.shape
    assert np.allclose(out, val)


valid_arrays_var_uint8 = npst.arrays(np.uint8,
                                     shape=valid_shapes_var,
                                     elements=st.integers(min_value=0, max_value=255),
                                     fill=st.integers(min_value=0, max_value=255))


@given(key=st_valid_keys, subkey=st_valid_keys, val=valid_arrays_var_uint8)
@settings(max_examples=200, deadline=200.0, suppress_health_check=[HealthCheck.too_slow])
def test_arrayset_variable_shape_uint8_nested(key, val, subkey, variable_shape_repo_co_uint8_aset_nested):
    global added_samples_subsamples

    co = variable_shape_repo_co_uint8_aset_nested
    col = co.columns['writtenaset']
    assert col.schema_type == 'variable_shape'
    assert col.contains_subsamples is True
    col[key] = {subkey: val}
    out = col[key][subkey]
    added_samples_subsamples[key].add(subkey)

    assert len(col) == len(added_samples_subsamples)
    assert len(col[key]) == len(added_samples_subsamples[key])
    assert out.dtype == val.dtype
    assert out.shape == val.shape
    assert np.allclose(out, val)



ascii_characters = st.characters(min_codepoint=0, max_codepoint=127)
ascii_text_stratagy = st.text(alphabet=ascii_characters, min_size=0, max_size=500)


@given(key=st_valid_keys, subkey=st_valid_keys, val=ascii_text_stratagy)
@settings(max_examples=400, deadline=100.0, suppress_health_check=[HealthCheck.too_slow])
def test_str_column_variable_shape_nested(key, subkey, val, variable_shape_repo_co_str_aset_nested):
    global added_samples_subsamples

    co = variable_shape_repo_co_str_aset_nested
    col = co.columns['strcolumn']
    assert col.schema_type == 'variable_shape'
    assert col.contains_subsamples is True

    col[key] = {subkey: val}
    out = col[key][subkey]
    added_samples_subsamples[key].add(subkey)

    assert len(col) == len(added_samples_subsamples)
    assert len(col[key]) == len(added_samples_subsamples[key])
    assert out == val
