import pytest
from pytest_mpi_check._decorator import mark_mpi_test
from maia.utils import test_utils as TU
import os
import numpy as np

import Converter.Internal as I
import maia.pytree        as PT

import  maia
import cmaia

#@mark_mpi_test([1,4])
@pytest.mark.skipif(not cmaia.cpp20_enabled, reason="Require ENABLE_CPP20 compilation flag")
@mark_mpi_test([1])
def test_ngons_to_elements(sub_comm, write_output):
  # Create NGon mesh
  mesh_file = os.path.join(TU.mesh_dir, 'Uelt_M6Wing.yaml')
  dist_tree = maia.io.file_to_dist_tree(mesh_file, sub_comm)
  # Note: `elements_to_ngons` is supposed to work, because it is tested in another test
  maia.algo.dist.elements_to_ngons(dist_tree, sub_comm)

  maia.algo.dist.ngons_to_elements(dist_tree, sub_comm)

  # > There is two sections...
  assert len(PT.get_nodes_from_label(dist_tree, 'Elements_t')) == 2
  # > One for the Tris, on for the Tets
  tris = I.getNodeFromName(dist_tree, 'TRI_3')
  tets = I.getNodeFromName(dist_tree, 'TETRA_4')
  assert tris is not None
  assert tets is not None

  # > Some non-regression checks
  assert np.all(I.getVal(I.getNodeFromName(tris, 'ElementRange')) == [1,204])
  assert np.all(I.getVal(I.getNodeFromName(tets, 'ElementRange')) == [205,1500])

  if write_output:
    out_dir = TU.create_pytest_output_dir(sub_comm)
    import Converter.PyTree as C
    C.convertPyTree2File(dist_tree, os.path.join(out_dir, 'U_M6Wing_ngon.cgns'))
    # TODO replace by this when in parallel
    #maia.io.dist_tree_to_file(dist_tree, os.path.join(out_dir, 'U_M6Wing_ngon.cgns'), sub_comm)
