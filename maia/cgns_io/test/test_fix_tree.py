import pytest
import numpy as np
import Converter.Internal as I
from maia.utils   import parse_yaml_cgns
from maia import npy_pdm_gnum_dtype as pdm_dtype

from maia.cgns_io import fix_tree

def test_fix_point_ranges():
  yt = """
Base0 CGNSBase_t [3,3]:
  ZoneA Zone_t:
    ZGC ZoneGridConnectivity_t:
      matchAB GridConnectivity1to1_t "ZoneB":
        PointRange IndexRange_t [[17,17],[3,9],[1,5]]:
        PointRangeDonor IndexRange_t [[7,1],[9,9],[1,5]]:
        Transform "int[IndexDimension]" [-2,-1,-3]:
  ZoneB Zone_t:
    ZGC ZoneGridConnectivity_t:
      matchBA GridConnectivity1to1_t "Base0/ZoneA":
        PointRange IndexRange_t [[7,1],[9,9],[1,5]]:
        PointRangeDonor IndexRange_t [[17,17],[3,9],[1,5]]:
        Transform "int[IndexDimension]" [-2,-1,-3]:
"""
  size_tree = parse_yaml_cgns.to_cgns_tree(yt)
  fix_tree.fix_point_ranges(size_tree)
  gcA = I.getNodeFromName(size_tree, 'matchAB')
  gcB = I.getNodeFromName(size_tree, 'matchBA')
  assert (I.getNodeFromName1(gcA, 'PointRange')[1]      == [[17,17], [3,9], [1,5]]).all()
  assert (I.getNodeFromName1(gcA, 'PointRangeDonor')[1] == [[ 7, 1], [9,9], [5,1]]).all()
  assert (I.getNodeFromName1(gcB, 'PointRange')[1]      == [[ 7, 1], [9,9], [5,1]]).all()
  assert (I.getNodeFromName1(gcB, 'PointRangeDonor')[1] == [[17,17], [3,9], [1,5]]).all()

#def test_load_grid_connectivity_property():
  #Besoin de charger depuis un fichier, comment tester ?

def test_enforce_pdm_dtype():
  wrong_pdm_type = np.int64 if pdm_dtype == np.int32 else np.int32
  wrong_type = 'I8' if pdm_dtype == np.int32 else 'I4'
  yt = f"""
  Base CGNSBase_t [3,3]:
    Zone Zone_t {wrong_type} [[11,10,0]]:
      NGon Elements_t [22,0]:
        ElementRange IndexRange_t [1, 3]:
        ElementConnectivity DataArray_t {wrong_type} [1,2,3,4]:
        ElementStartOffset DataArray_t {wrong_type} [0,1,2]:
      ZGC ZoneGridConnectivity_t:
        match GridConnectivity_t "ZoneB":
          PointList IndexArray_t {wrong_type} [[11,12,13]]:
          PointListDonor IndexArray_t {wrong_type} [[1,2,3]]:
  """
  tree = parse_yaml_cgns.to_cgns_tree(yt)
  assert I.getNodeFromName(tree, 'PointList')[1].dtype == wrong_pdm_type
  assert I.getNodeFromName(tree, 'ElementConnectivity')[1].dtype == wrong_pdm_type
  assert I.getNodeFromName(tree, 'ElementStartOffset')[1].dtype == wrong_pdm_type
  assert I.getNodeFromName(tree, 'ElementRange')[1].dtype == np.int32 #Always int32
  fix_tree._enforce_pdm_dtype(tree)
  assert I.getNodeFromName(tree, 'PointList')[1].dtype == pdm_dtype
  assert I.getNodeFromName(tree, 'ElementConnectivity')[1].dtype == pdm_dtype
  assert I.getNodeFromName(tree, 'ElementStartOffset')[1].dtype == pdm_dtype
  assert I.getNodeFromName(tree, 'ElementRange')[1].dtype == np.int32 #Always int32
