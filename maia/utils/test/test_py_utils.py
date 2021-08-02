import pytest
import Converter.Internal as I
import numpy as np
import maia.utils.py_utils as py_utils
from   maia.utils        import parse_yaml_cgns

def test_camel_to_snake():
  assert py_utils.camel_to_snake("already_snake") == "already_snake"
  assert py_utils.camel_to_snake("stringInCamelCase") == "string_in_camel_case"
  assert py_utils.camel_to_snake("StringInCamelCase") == "string_in_camel_case"
  assert py_utils.camel_to_snake("stringINCamelCase", keep_upper=True) == "string_IN_camel_case"

def test_list_or_only_elt():
  assert py_utils.list_or_only_elt([42]) == 42
  input = [1,2,3, "nous irons au bois"]
  assert py_utils.list_or_only_elt(input) is input

def test_interweave_arrays():
  first  = np.array([1,2,3], dtype=np.int32)
  second = np.array([11,22,33], dtype=np.int32)
  third  = np.array([111,222,333], dtype=np.int32)
  assert (py_utils.interweave_arrays([first]) == [1,2,3]).all()
  assert (py_utils.interweave_arrays([second, third]) == \
      [11,111,22,222,33,333]).all()
  assert (py_utils.interweave_arrays([first, second, third]) == \
      [1,11,111,2,22,222,3,33,333]).all()

def test_single_dim_pr_to_pl():
  no_dist = py_utils.single_dim_pr_to_pl(np.array([[20, 25]]))
  assert no_dist.dtype == np.array([[20,25]]).dtype
  assert (no_dist == np.arange(20, 25+1)).all()
  assert no_dist.ndim == 2 and no_dist.shape[0] == 1
  dist = py_utils.single_dim_pr_to_pl(np.array([[20, 25]], dtype=np.int32), np.array([10,15,20]))
  assert dist.dtype == np.int32
  assert (dist == np.arange(10+20, 15+20)).all()
  assert dist.ndim == 2 and dist.shape[0] == 1
  with pytest.raises(AssertionError):
    py_utils.single_dim_pr_to_pl(np.array([[20, 25], [1,1]]))

def test_sizes_to_indices():
  assert(py_utils.sizes_to_indices([]) == np.zeros(1))
  assert(py_utils.sizes_to_indices([5,3,5,10]) == np.array([0,5,8,13,23])).all()
  assert(py_utils.sizes_to_indices([5,0,0,10]) == np.array([0,5,5,5,15])).all()
  assert py_utils.sizes_to_indices([5,0,0,10], np.int32).dtype == np.int32
  assert py_utils.sizes_to_indices([5,0,0,10], np.int64).dtype == np.int64

def test_multi_arange():
  assert (py_utils.multi_arange([1,3,4,6], [1,5,7,6]) == [3,4,4,5,6]).all()
  assert (py_utils.multi_arange([1,5,10,20], [3,10,12,25]) == \
      [1,2,5,6,7,8,9,10,11,20,21,22,23,24]).all()

def test_concatenate_point_list():
  pl1 = np.array([[2, 4, 6, 8]])
  pl2 = np.array([[10, 20, 30, 40, 50, 60]])
  pl3 = np.array([[100]])
  plvoid = np.empty((1,0))

  #No pl at all in the mesh
  none_idx, none = py_utils.concatenate_point_list([])
  assert none_idx == [0]
  assert isinstance(none, np.ndarray)
  assert none.shape == (0,)

  #A pl, but with no data
  empty_idx, empty = py_utils.concatenate_point_list([plvoid])
  assert (none_idx == [0,0]).all()
  assert isinstance(empty, np.ndarray)
  assert empty.shape == (0,)

  # A pl with data
  one_idx, one = py_utils.concatenate_point_list([pl1])
  assert (one_idx == [0,4]).all()
  assert (one     == pl1[0]).all()

  # Several pl
  merged_idx, merged = py_utils.concatenate_point_list([pl1, pl2, pl3])
  assert (merged_idx == [0, pl1.size, pl1.size+pl2.size, pl1.size+pl2.size+pl3.size]).all()
  assert (merged[0:pl1.size]                 == pl1[0]).all()
  assert (merged[pl1.size:pl1.size+pl2.size] == pl2[0]).all()
  assert (merged[pl1.size+pl2.size:]         == pl3[0]).all()
  # Several pl, some with no data
  merged_idx, merged = py_utils.concatenate_point_list([pl1, plvoid, pl2])
  assert (merged_idx == [0, 4, 4, 10]).all()
  assert (merged[0:4 ] == pl1[0]).all()
  assert (merged[4:10] == pl2[0]).all()

def test_any_in_range():
  assert py_utils.any_in_range([3,4,1,6,12,3], 2, 20, strict=False)
  assert not py_utils.any_in_range([3,4,2,6,12,3], 15, 20, strict=False)
  assert py_utils.any_in_range([3,4,1,6,12,3], 12, 20, strict=False)
  assert not py_utils.any_in_range([3,4,1,6,12,3], 12, 20, strict=True)

def test_all_in_range():
  assert py_utils.all_in_range([3,4,5,6,12,3], 2, 20, strict=False)
  assert not py_utils.all_in_range([18,4,2,17,16,3], 15, 20, strict=False)
  assert not py_utils.all_in_range([3,4,1,6,12,3], 3, 20, strict=True)
