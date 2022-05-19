import pytest
from pytest_mpi_check._decorator import mark_mpi_test
import numpy as np

import Converter.Internal as I
import maia.pytree.maia   as MT

from maia.factory.dcube_generator import dcube_generate

from maia.algo import transform

@mark_mpi_test(1)
def test_transform_zone(sub_comm):

  def check_vect_field(old_node, new_node, field_name):
    old_data = [I.getNodeFromName(old_node, f"{field_name}{c}")[1] for c in ['X', 'Y', 'Z']]
    new_data = [I.getNodeFromName(new_node, f"{field_name}{c}")[1] for c in ['X', 'Y', 'Z']]
    assert np.allclose(old_data[0], -new_data[0])
    assert np.allclose(old_data[1], -new_data[1])
    assert np.allclose(old_data[2],  new_data[2])
  def check_scal_field(old_node, new_node, field_name):
    old_data = I.getNodeFromName(old_node, field_name)[1]
    new_data = I.getNodeFromName(new_node, field_name)[1]
    assert (old_data == new_data).all()

  dist_tree = dcube_generate(4, 1., [0., -.5, -.5], sub_comm)
  dist_zone = I.getZones(dist_tree)[0]

  # Initialise some fields
  cell_distri = MT.getDistribution(dist_zone, 'Cell')[1]
  n_cell_loc =  cell_distri[1] - cell_distri[0]
  fs = I.newFlowSolution('FlowSolution', gridLocation='CellCenter', parent=dist_zone)
  I.newDataArray('scalar', np.random.random(n_cell_loc), parent=fs)
  I.newDataArray('fieldX', np.random.random(n_cell_loc), parent=fs)
  I.newDataArray('fieldY', np.random.random(n_cell_loc), parent=fs)
  I.newDataArray('fieldZ', np.random.random(n_cell_loc), parent=fs)

  dist_zone_ini = I.copyTree(dist_zone)
  transform.transform_zone(dist_zone, rotation_angle=np.array([0.,0.,np.pi]), apply_to_fields=True)

  check_vect_field(dist_zone_ini, dist_zone, "Coordinate")
  check_vect_field(dist_zone_ini, dist_zone, "field")
  check_scal_field(dist_zone_ini, dist_zone, "scalar")
