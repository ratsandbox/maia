import pytest
import pytest_parallel
import numpy as np

import maia.pytree        as PT
import maia.pytree.maia   as MT

import maia
from maia             import npy_pdm_gnum_dtype as pdm_dtype
from maia.pytree.yaml import parse_yaml_cgns
from maia.factory.dcube_generator import dcube_generate, dcube_struct_generate

from maia.utils import par_utils

from maia.algo.dist import connect_match
from maia.algo.dist import redistribute
dtype = 'I4' if pdm_dtype == np.int32 else 'I8'

@pytest_parallel.mark.parallel([1,3])
@pytest.mark.parametrize("output_loc", ['Vertex', 'FaceCenter'])
def test_simple(output_loc, comm):                               #    __ 
  n_vtx = 3                                                      #   |  |
  dcubes = [dcube_generate(n_vtx, 1., [0,0,0], comm),            #   |__|
            dcube_generate(n_vtx, 1., [0,0,1], comm)]            #   |  |
  zones = [PT.get_all_Zone_t(dcube)[0] for dcube in dcubes]      #   |__|
  tree = PT.new_CGNSTree()
  base = PT.new_CGNSBase(parent=tree)
  for i_zone,zone in enumerate(zones):
    zone[0] = f"zone{i_zone+1}"
    PT.add_child(base, zone)

  zmax = PT.get_node_from_name(zones[0], 'Zmax')
  PT.new_child(zmax, 'FamilyName', 'FamilyName_t', 'matchA')
  zmin = PT.get_node_from_name(zones[1], 'Zmin')
  PT.new_child(zmin, 'FamilyName', 'FamilyName_t', 'matchB')

  connect_match.connect_match_from_family(tree, ('matchA', 'matchB'), comm, location=output_loc)

  assert len(PT.get_nodes_from_label(tree, 'BC_t')) == 10
  assert len(PT.get_nodes_from_label(tree, 'GridConnectivity_t')) == 2

  if output_loc == 'FaceCenter':
    expected_pl = np.array([[4,2,3,1]], pdm_dtype)
    expected_pld = np.array([[12,10,11,9]], pdm_dtype)
  elif output_loc == 'Vertex':
    expected_pl = np.array([[1,2,3,4,5,6,7,8,9]], pdm_dtype)
    expected_pld = np.array([[19,20,21,22,23,24,25,26,27]], pdm_dtype)

  # Redistribute and compare on rank 0 to avoid managing parallelism
  expected_zmin_full = parse_yaml_cgns.to_node(f"""
  Zmin_0 GridConnectivity_t "Base/zone1":
    GridConnectivityType GridConnectivityType_t "Abutting1to1":
    GridLocation GridLocation_t "{output_loc}":
    GridConnectivityDonorName Descriptor_t "Zmax_0":
    FamilyName FamilyName_t "matchB":
    :CGNS#Distribution UserDefinedData_t:
      Index DataArray_t {dtype} [0,{expected_pl.size},{expected_pl.size}]:
  """)
  PT.new_child(expected_zmin_full, 'PointList', 'IndexArray_t', expected_pl)
  PT.new_child(expected_zmin_full, 'PointListDonor', 'IndexArray_t', expected_pld)

  expected_zmax_full = parse_yaml_cgns.to_node(f"""
  Zmax_0 GridConnectivity_t "Base/zone2":
    GridConnectivityType GridConnectivityType_t "Abutting1to1":
    GridLocation GridLocation_t "{output_loc}":
    GridConnectivityDonorName Descriptor_t "Zmin_0":
    FamilyName FamilyName_t "matchA":
    :CGNS#Distribution UserDefinedData_t:
      Index DataArray_t {dtype} [0,{expected_pl.size},{expected_pl.size}]:
  """)
  PT.new_child(expected_zmax_full, 'PointList', 'IndexArray_t', expected_pld)
  PT.new_child(expected_zmax_full, 'PointListDonor', 'IndexArray_t', expected_pl)

  gather_distri = lambda n_elt, comm : par_utils.gathering_distribution(0, n_elt, comm)

  zmin = PT.get_node_from_name(tree, 'Zmin_0')
  zmax = PT.get_node_from_name(tree, 'Zmax_0')
  redistribute.redistribute_pl_node(zmin, gather_distri, comm)
  redistribute.redistribute_pl_node(zmax, gather_distri, comm)

  if comm.Get_rank() == 0:
    assert PT.is_same_tree(zmin, expected_zmin_full)
    assert PT.is_same_tree(zmax, expected_zmax_full)


@pytest_parallel.mark.parallel(2)
def test_partial_match(comm):                                 #         
  n_vtx = 3                                                   #       __    
  dcubes = [dcube_generate(n_vtx, 1., [0,0,0], comm),         #    __|  |
            dcube_generate(n_vtx, 1., [1,0,.5], comm)]        #   |  |__|
  zones = [PT.get_all_Zone_t(dcube)[0] for dcube in dcubes]   #   |__|
  tree = PT.new_CGNSTree()                                    # 
  base = PT.new_CGNSBase(parent=tree)
  for i_zone,zone in enumerate(zones):
    zone[0] = f"zone{i_zone+1}"
    PT.add_child(base, zone)

  xmax = PT.get_node_from_name(zones[0], 'Xmax')
  PT.new_child(xmax, 'FamilyName', 'FamilyName_t', 'matchA')
  xmin = PT.get_node_from_name(zones[1], 'Xmin')
  PT.new_child(xmin, 'FamilyName', 'FamilyName_t', 'matchB')

  connect_match.connect_match_from_family(tree, ('matchA', 'matchB'), comm)

  assert len(PT.get_nodes_from_label(tree, 'BC_t')) == 12
  assert len(PT.get_nodes_from_label(tree, 'GridConnectivity_t')) == 2

  not_found_xmax = PT.get_node_from_name(zones[0], 'Xmax_X')
  not_found_xmin = PT.get_node_from_name(zones[1], 'Xmin_X')
  found_xmax = PT.get_node_from_name(zones[0], 'Xmax_0')
  found_xmin = PT.get_node_from_name(zones[1], 'Xmin_0')
  if comm.Get_rank() == 0:
    assert PT.get_child_from_name(not_found_xmax, 'PointList')[1][0] == [21]
    assert PT.get_child_from_name(    found_xmax, 'PointList')[1][0] == [23]
    assert PT.get_child_from_name(not_found_xmin, 'PointList')[1][0] == [15]
    assert PT.get_child_from_name(    found_xmin, 'PointList')[1][0] == [13]
  elif comm.Get_rank() == 1:
    assert PT.get_child_from_name(not_found_xmax, 'PointList')[1][0] == [22]
    assert PT.get_child_from_name(    found_xmax, 'PointList')[1][0] == [24]
    assert PT.get_child_from_name(not_found_xmin, 'PointList')[1][0] == [16]
    assert PT.get_child_from_name(    found_xmin, 'PointList')[1][0] == [14]
  maia.io.dist_tree_to_file(tree, 'test.cgns', comm)


@pytest_parallel.mark.parallel(1)
def test_multiple_match(comm):                                      
  # Can not generate ngon with n_vtx != cst so convert it from S -_-
  dcubes = [dcube_struct_generate([5,3,3], [2.,1,1], [0,0,0], comm),  #    __ __
            dcube_struct_generate(3, 1, [0,0,1], comm),               #   |  |  |
            dcube_struct_generate(3, 1, [1,0,1], comm)]               #   |1_|2_|
  zones = [PT.get_all_Zone_t(dcube)[0] for dcube in dcubes]           #   |     |
  tree = PT.new_CGNSTree()                                            #   |__0__|
  base = PT.new_CGNSBase(parent=tree)                                 #
  for i_zone,zone in enumerate(zones):
    zone[0] = f"zone{i_zone+1}"
    PT.add_child(base, zone)
  tree = maia.algo.dist.convert_s_to_ngon(tree, comm)

  zones = PT.get_all_Zone_t(tree)
  zmax = PT.get_node_from_name(zones[0], 'Zmax')
  PT.new_child(zmax, 'FamilyName', 'FamilyName_t', 'matchA')
  for zone in zones[1:]:
    zmin = PT.get_node_from_name(zone, 'Zmin')
    PT.new_child(zmin, 'FamilyName', 'FamilyName_t', 'matchB')

  connect_match.connect_match_from_family(tree, ('matchA', 'matchB'), comm)

  assert len(PT.get_nodes_from_label(tree, 'BC_t')) == 15
  assert len(PT.get_nodes_from_label(tree, 'GridConnectivity_t')) == 4

  assert (PT.get_node_from_predicates(zones[0], ['Zmax_0', 'PointList'])[1][0] == [[62,65,66,61]]).all()
  assert (PT.get_node_from_predicates(zones[0], ['Zmax_1', 'PointList'])[1][0] == [[68,63,64,67]]).all()
  assert (PT.get_node_from_predicates(zones[1], ['Zmin_0', 'PointList'])[1][0] == [[26,27,28,25]]).all()
  assert (PT.get_node_from_predicates(zones[2], ['Zmin_0', 'PointList'])[1][0] == [[28,25,26,27]]).all()



