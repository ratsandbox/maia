import pytest
from pytest_mpi_check._decorator import mark_mpi_test
import numpy      as np

import Converter.Internal as I
import maia.pytree      as PT
import maia.pytree.maia as MT

from maia.utils.yaml import parse_yaml_cgns
from maia import npy_pdm_gnum_dtype as pdm_gnum_dtype
import maia.transfer.part_to_dist.index_exchange as IPTB

from maia import npy_pdm_gnum_dtype as pdm_dtype
dtype = 'I4' if pdm_dtype == np.int32 else 'I8'

@mark_mpi_test(4)
def test_create_part_pl_gnum_unique(sub_comm):
  part_zones = [I.newZone('Zone.P{0}.N0'.format(sub_comm.Get_rank()))]
  if sub_comm.Get_rank() == 0:
    I.newZoneSubRegion("ZSR", pointList=[[2,4,6,8]], gridLocation='Vertex', parent=part_zones[0])
  if sub_comm.Get_rank() == 2:
    part_zones.append(I.newZone('Zone.P2.N1'))
    I.newZoneSubRegion("ZSR", pointList=[[1,3]], gridLocation='Vertex', parent=part_zones[0])
    I.newZoneSubRegion("ZSR", pointList=[[2,4,6]], gridLocation='Vertex', parent=part_zones[1])
  if sub_comm.Get_rank() == 3:
    part_zones = []
  IPTB.create_part_pl_gnum_unique(part_zones, "ZSR", sub_comm)

  for p_zone in part_zones:
    if I.getNodeFromName1(p_zone, "ZSR") is not None:
      assert I.getNodeFromPath(p_zone, "ZSR/:CGNS#GlobalNumbering/Index") is not None 
  if sub_comm.Get_rank() == 0:
    assert (I.getNodeFromName(part_zones[0], 'Index')[1] == [1,2,3,4]).all()
  if sub_comm.Get_rank() == 2:
    assert (I.getNodeFromName(part_zones[1], 'Index')[1] == [7,8,9]).all()
    assert I.getNodeFromName(part_zones[0], 'Index')[1].dtype == pdm_gnum_dtype

@mark_mpi_test(4)
def test_create_part_pl_gnum(sub_comm):
  dist_zone = I.newZone('Zone')
  part_zones = [I.newZone('Zone.P{0}.N0'.format(sub_comm.Get_rank()))]
  distri_ud0 = MT.newGlobalNumbering(parent=part_zones[0])
  if sub_comm.Get_rank() == 0:
    I.newZoneSubRegion("ZSR", pointList=[[1,8,5,2]], gridLocation='Vertex', parent=part_zones[0])
    I.newDataArray('Vertex', np.array([22,18,5,13,9,11,6,4], pdm_dtype), parent=distri_ud0)
  elif sub_comm.Get_rank() == 1:
    I.newDataArray('Vertex', np.array([5,16,9,17,22], pdm_dtype), parent=distri_ud0)
  elif sub_comm.Get_rank() == 2:
    I.newDataArray('Vertex', np.array([13,8,9,6,2], pdm_dtype), parent=distri_ud0)
    part_zones.append(I.newZone('Zone.P2.N1'))
    distri_ud1 = MT.newGlobalNumbering(parent=part_zones[1])
    I.newDataArray('Vertex', np.array([4,9,13,1,7,6], pdm_dtype), parent=distri_ud1)
    I.newZoneSubRegion("ZSR", pointList=[[1,3]], gridLocation='Vertex', parent=part_zones[0])
    I.newZoneSubRegion("ZSR", pointList=[[2,4,6]], gridLocation='Vertex', parent=part_zones[1])
  elif sub_comm.Get_rank() == 3:
    part_zones = []

  IPTB.create_part_pl_gnum(dist_zone, part_zones, "ZSR", sub_comm)

  for p_zone in part_zones:
    if I.getNodeFromName1(p_zone, "ZSR") is not None:
      assert I.getNodeFromPath(p_zone, "ZSR/:CGNS#GlobalNumbering/Index") is not None 
  if sub_comm.Get_rank() == 0:
    assert (I.getNodeFromName(part_zones[0], 'Index')[1] == [7,2,4,6]).all()
    assert I.getNodeFromName(part_zones[0], 'Index')[1].dtype == pdm_gnum_dtype
  if sub_comm.Get_rank() == 2:
    assert (I.getNodeFromName(part_zones[0], 'Index')[1] == [5,4]).all()
    assert (I.getNodeFromName(part_zones[1], 'Index')[1] == [4,1,3]).all()

@mark_mpi_test(4)
@pytest.mark.parametrize("allow_mult", [False, True])
def test_part_pl_to_dist_pl(sub_comm, allow_mult):
  dist_zone = I.newZone('Zone')
  dist_zsr = I.newZoneSubRegion("ZSR", gridLocation='Vertex', parent=dist_zone)
  part_zones = [I.newZone('Zone.P{0}.N0'.format(sub_comm.Get_rank()))]
  distri_ud0 = MT.newGlobalNumbering(parent=part_zones[0])
  if sub_comm.Get_rank() == 0:
    I.newDataArray('Vertex', np.array([22,18,5,13,9,11,6,4], pdm_dtype), parent=distri_ud0)
    zsr = I.newZoneSubRegion("ZSR", pointList=[[1,8,5,2]], gridLocation='Vertex', parent=part_zones[0])
    MT.newGlobalNumbering({'Index' : np.array([7,2,4,6], pdm_dtype)}, zsr)
  elif sub_comm.Get_rank() == 1:
    I.newDataArray('Vertex', np.array([5,16,9,17,22], pdm_dtype), parent=distri_ud0)
  elif sub_comm.Get_rank() == 2:
    I.newDataArray('Vertex', np.array([13,8,9,6,2], pdm_dtype), parent=distri_ud0)
    part_zones.append(I.newZone('Zone.P2.N1'))
    distri_ud1 = MT.newGlobalNumbering(parent=part_zones[1])
    I.newDataArray('Vertex', np.array([4,9,13,1,7,6], pdm_dtype), parent=distri_ud1)
    zsr = I.newZoneSubRegion("ZSR", pointList=[[1,3]], gridLocation='Vertex', parent=part_zones[0])
    MT.newGlobalNumbering({'Index' : np.array([5,4], pdm_dtype)}, zsr)
    zsr = I.newZoneSubRegion("ZSR", pointList=[[2,4,6]], gridLocation='Vertex', parent=part_zones[1])
    MT.newGlobalNumbering({'Index' : np.array([4,1,3], pdm_dtype)}, zsr)
  elif sub_comm.Get_rank() == 3:
    part_zones = []

  IPTB.part_pl_to_dist_pl(dist_zone, part_zones, "ZSR", sub_comm, allow_mult)

  dist_pl     = I.getNodeFromPath(dist_zsr, 'PointList')[1]
  dist_distri = I.getVal(MT.getDistribution(dist_zsr, 'Index'))
  assert dist_distri.dtype == pdm_gnum_dtype

  if sub_comm.Get_rank() == 0:
    assert (dist_distri == [0,2,7]).all()
    assert (dist_pl     == [1,4]  ).all()
  elif sub_comm.Get_rank() == 1:
    assert (dist_distri == [2,4,7]).all()
    assert (dist_pl     == [6,9]  ).all()
  elif sub_comm.Get_rank() == 2:
    assert (dist_distri == [4,6,7]).all()
    assert (dist_pl     == [13,18]).all()
  elif sub_comm.Get_rank() == 3:
    assert (dist_distri == [6,7,7]).all()
    assert (dist_pl     == [22]   ).all()

@mark_mpi_test(3)
def test_part_elt_to_dist_elt(sub_comm):
  rank = sub_comm.Get_rank()
  size = sub_comm.Get_size()

  dist_zone = I.newZone('Zone')
  if rank == 0:
    yt = """
Zone.P0.N0 Zone_t:
  Quad Elements_t [7,0]:
    ElementRange IndexRange_t [1, 4]:
    ElementConnectivity DataArray_t:
      I4 : [10,15,17,11, 15,16,12,17, 11,17,13,18, 17,12,14,13]
    :CGNS#GlobalNumbering UserDefinedData_t:
      Element DataArray_t {0} [5,6,7,8]:
      Sections DataArray_t {0} [15,16,17,18]:
  :CGNS#GlobalNumbering UserDefinedData_t:
    Vertex DataArray_t {0} [19,20,21,22,23,24,25,26,27,10,13,15,17,18,11,12,14,16]:
    Cell DataArray_t {0} [5,6,7,4]:
  """.format(dtype)
    expected_ec=[2,5,4,1, 5,8,7,4, 10,13,14,11]
  elif rank == 1:
    yt = ""
    expected_ec=[10,11,14,13,11,12,15,14]
  elif rank == 2:
    yt = """
Zone.P2.N0 Zone_t:
  Quad Elements_t [7,0]:
    ElementRange IndexRange_t [12, 14]:
    ElementConnectivity DataArray_t:
      I4 : [4,5,2,1, 5,6,3,2, 10,11,8,7]
    :CGNS#GlobalNumbering UserDefinedData_t:
      Element DataArray_t {0} [1,2,3]:
      Sections DataArray_t {0} [11,12,13]:
  :CGNS#GlobalNumbering UserDefinedData_t:
    Vertex DataArray_t {0} [1,4,7,2,5,8,11,14,16,10,13,17]:
    Cell DataArray_t {0} [1,3]:
  """.format(dtype)
    expected_ec = [13,14,17,16,14,15,18,17]

  expected_elt_distri_full  = np.array([0, 3, 6, 8])

  pT = parse_yaml_cgns.to_cgns_tree(yt)

  IPTB.part_elt_to_dist_elt(dist_zone, I.getZones(pT), 'Quad', sub_comm)

  elt = I.getNodeFromName(dist_zone, 'Quad')
  assert (PT.Element.Range(elt) == [11,18]).all()
  assert (elt[1] == [7,0]).all()
  assert (I.getNodeFromName(elt, 'ElementConnectivity')[1] == expected_ec).all()
  distri_elt  = I.getVal(MT.getDistribution(elt, 'Element'))
  assert distri_elt.dtype == pdm_gnum_dtype
  assert (distri_elt  == expected_elt_distri_full [[rank, rank+1, size]]).all()

@mark_mpi_test(3)
def test_part_ngon_to_dist_ngon(sub_comm):
  rank = sub_comm.Get_rank()
  size = sub_comm.Get_size()

  dist_zone = I.newZone('Zone')
  if rank == 0:
    yt = """
Zone.P0.N0 Zone_t:
  Ngon Elements_t [22,0]:
    ElementRange IndexRange_t [1, 20]:
    ElementConnectivity DataArray_t:
      I4 : [10,15,17,11, 15,16,12,17, 11,17,13,18, 17,12,14,13, 1,4,5,2,
            2,5,6,3, 4,7,8,5, 5,8,9,6, 10,11,4,1, 11,18,7,4,
            2,5,17,15, 5,8,13,17, 3,6,12,16, 6,9,14,12, 1,2,15,10,
            2,3,16,15, 11,17,5,4, 17,12,6,5, 18,13,8,7, 13,14,9,8]
    ElementStartOffset DataArray_t:
      I4 : [0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60,64,68,72,76,80]
    ParentElements DataArray_t:
      I4 : [[21,0],  [22,0],  [23,0], [24,0], [21,0], [22,0], [23,0],  [24,0],  [21,0], [23,0],
            [21,22], [23,24], [22,0], [24,0], [21,0], [22,0], [21,23], [22,24], [23,0], [24,0]]
    :CGNS#GlobalNumbering UserDefinedData_t:
      Element DataArray_t:
        {0} : [5,6,7,8,9,10,11,12,15,16,19,20,23,24,26,28,30,32,34,36]
  :CGNS#GlobalNumbering UserDefinedData_t:
    Vertex DataArray_t {0} [19,20,21,22,23,24,25,26,27,10,13,15,17,18,11,12,14,16]:
    Cell DataArray_t {0} [5,6,7,8]:
  """.format(dtype)
    expected_ec=[2,5,4,1,3,6,5,2,5,8,7,4,6,9,8,5,10,13,14,11,11,14,15,12,
                 13,16,17,14,14,17,18,15,19,22,23,20,20,23,24,21,22,25,26,23,23,26,27,24]
    expected_pe = np.array([[37,0], [38,0], [39,0], [40,0], [37,41], [38,42],
                            [39,43], [40,44], [41,0], [42,0], [43,0], [44,0]])
  elif rank == 1:
    yt = ""
    expected_pe = np.array([[37,0], [39,0], [41,0], [43,0], [37,38], [39,40],
                            [41,42], [43,44], [38,0], [40,0], [42,0], [44,0]])
    expected_ec=[1,4,13,10,4,7,16,13,10,13,22,19,13,16,25,22,11,14,5,2,14,17,8,5,
                 20,23,14,11,23,26,17,14,12,15,6,3,15,18,9,6,21,24,15,12,24,27,18,15]
  elif rank == 2:
    yt = """
Zone.P2.N0 Zone_t:
  Ngon Elements_t [22,0]:
    ElementRange IndexRange_t [12, 23]:
    ElementConnectivity DataArray_t:
      I4 : [4,5,2,1, 5,6,3,2, 10,11,8,7, 11,9,12,8, 1,2,11,10, 2,3,9,11,
            7,8,5,4, 8,12,6,5, 10,7,4,1, 2,5,8,11, 3,6,12,9]
    ElementStartOffset DataArray_t:
      I4 : [0,4,8,12,16,20,24,28,32,36,40,44]
    ParentElements DataArray_t:
      I4 : [[1,0], [2,0], [1,0], [2,0], [1,0], [2,0], [1,0], [2,0], [1,0], [1,2], [2,0]]
    :CGNS#GlobalNumbering UserDefinedData_t:
      Element DataArray_t {0} [1,3,5,7,13,14,17,18,25,29,33]:
  :CGNS#GlobalNumbering UserDefinedData_t:
    Vertex DataArray_t {0} [1,4,7,2,5,8,11,14,16,10,13,17]:
    Cell DataArray_t {0} [1,3]:
Zone.P2.N1 Zone_t:
  Ngon Elements_t [22,0]:
    ElementRange IndexRange_t [12, 23]:
    ElementConnectivity DataArray_t:
      I4 : [1,2,5,4, 2,3,6,5, 7,9,10,8, 9,11,12,10, 7,4,5,9, 9,5,6,11,
            8,10,2,1, 10,12,3,2, 7,8,1,4, 5,2,10,9, 6,3,12,11]
    ElementStartOffset DataArray_t:
      I4 : [0,4,8,12,16,20,24,28,32,36,40,44]
    ParentElements DataArray_t:
      I4 : [[1,0], [2,0], [1,0], [2,0], [1,0], [2,0], [1,0], [2,0], [1,0], [1,2], [2,0]]
    :CGNS#GlobalNumbering UserDefinedData_t:
      Element DataArray_t {0} [2,4,6,8,17,18,21,22,27,31,35]:
  :CGNS#GlobalNumbering UserDefinedData_t:
    Vertex DataArray_t {0} [3,6,9,2,5,8,11,12,14,15,17,18]:
    Cell DataArray_t {0} [2,4]:
  """.format(dtype)
    expected_pe = np.array([[37,0], [41,0], [38,0], [42,0], [37,39], [41,43],
                            [38,40], [42,44], [39,0], [43,0], [40,0], [44,0]])
    expected_ec=[10,11,2,1,19,20,11,10,11,12,3,2,20,21,12,11,4,5,14,13,13,14,23,22,
                 5,6,15,14,14,15,24,23,7,8,17,16,16,17,26,25,8,9,18,17,17,18,27,26]
  expected_eso = np.array([0,4,8,12,16,20,24,28,32,36,40,44,48]) + 48*sub_comm.Get_rank()
  expected_elt_distri_full  = np.array([0, 12, 24, 36])
  expected_eltc_distri_full = np.array([0, 48, 96, 144])

  pT = parse_yaml_cgns.to_cgns_tree(yt)

  IPTB.part_ngon_to_dist_ngon(dist_zone, I.getZones(pT), 'Ngon', sub_comm)

  ngon = I.getNodeFromName(dist_zone, 'Ngon')
  assert ngon is not None
  assert (I.getNodeFromName(ngon, 'ElementStartOffset')[1] == expected_eso).all()
  assert (I.getNodeFromName(ngon, 'ParentElements')[1] == expected_pe).all()
  assert (I.getNodeFromName(ngon, 'ElementConnectivity')[1] == expected_ec).all()
  distri_elt  = I.getVal(MT.getDistribution(ngon, 'Element'))
  distri_eltc = I.getVal(MT.getDistribution(ngon, 'ElementConnectivity'))
  assert distri_elt.dtype == distri_eltc.dtype == pdm_gnum_dtype
  assert (distri_elt  == expected_elt_distri_full [[rank, rank+1, size]]).all()
  assert (distri_eltc == expected_eltc_distri_full[[rank, rank+1, size]]).all()

@mark_mpi_test(3)
def test_part_nface_to_dist_nface(sub_comm):
  rank = sub_comm.Get_rank()
  size = sub_comm.Get_size()

  dist_zone = I.newZone('Zone')
  if rank == 0:
    yt = """
Zone.P0.N0 Zone_t:
  Ngon Elements_t [22,0]:
    :CGNS#GlobalNumbering UserDefinedData_t:
      Element DataArray_t:
        {0} : [5,6,7,8,9,10,11,12,15,16,19,20,23,24,26,28,30,32,34,36]
  NFace Elements_t [23,0]:
    ElementConnectivity DataArray_t:
      I4 : [1,5,9,11,15,17,2,6,-11,13,16,18,3,7,10,12,-17,19,4,8,-12,14,-18,20]
    ElementStartOffset DataArray_t [0,6,12,18,24]:
    :CGNS#GlobalNumbering UserDefinedData_t:
      Element DataArray_t {0} [5,6,7,8]:
  :CGNS#GlobalNumbering UserDefinedData_t:
    Vertex DataArray_t {0} [19,20,21,22,23,24,25,26,27,10,13,15,17,18,11,12,14,16]:
    Cell DataArray_t {0} [5,6,7,8]:
  """.format(dtype)
    expected_ec  = [1,5,13,17,25,29,2,6,17,21,27,31,3,7,14,18,29,33]
    expected_eso = [0,6,12,18]
  elif rank == 1:
    yt = ""
    expected_ec  = [4,8,18,22,31,35,5,9,15,19,26,30,6,10,19,23,28,32]
    expected_eso = [18,24,30,36]
  elif rank == 2:
    yt = """
Zone.P2.N0 Zone_t:
  Ngon Elements_t [22,0]:
    :CGNS#GlobalNumbering UserDefinedData_t:
      Element DataArray_t {0} [1,3,5,7,13,14,17,18,25,29,33]:
  NFace Elements_t [23,0]:
    ElementConnectivity DataArray_t I4 [1,3,5,7,9,10,2,4,6,8,-10,11]:
    ElementStartOffset DataArray_t [0,6,12]:
    :CGNS#GlobalNumbering UserDefinedData_t:
      Element DataArray_t {0} [1,3]:
  :CGNS#GlobalNumbering UserDefinedData_t:
    Vertex DataArray_t {0} [1,4,7,2,5,8,11,14,16,10,13,17]:
    Cell DataArray_t {0} [1,3]:
Zone.P2.N1 Zone_t:
  Ngon Elements_t [22,0]:
    :CGNS#GlobalNumbering UserDefinedData_t:
      Element DataArray_t {0} [2,4,6,8,17,18,21,22,27,31,35]:
  NFace Elements_t [23,0]:
    ElementConnectivity DataArray_t I4 [1,3,5,7,9,10,2,4,6,8,-10,11]:
    ElementStartOffset DataArray_t [0,6,12]:
    :CGNS#GlobalNumbering UserDefinedData_t:
      Element DataArray_t {0} [2,4]:
  :CGNS#GlobalNumbering UserDefinedData_t:
    Vertex DataArray_t {0} [3,6,9,2,5,8,11,12,14,15,17,18]:
    Cell DataArray_t {0} [2,4]:
  """.format(dtype)
    expected_ec  = [7,11,16,20,30,34,8,12,20,24,32,36]
    expected_eso = [36,42,48]

  expected_elt_distri_full  = np.array([0,3,6,8])
  expected_eltc_distri_full = np.array([0,18,36,48])

  pT = parse_yaml_cgns.to_cgns_tree(yt)

  IPTB.part_nface_to_dist_nface(dist_zone, I.getZones(pT), 'NFace', 'Ngon', sub_comm)

  nface = I.getNodeFromName(dist_zone, 'NFace')
  assert nface is not None
  assert (I.getNodeFromName(nface, 'ElementStartOffset')[1] == expected_eso).all()
  assert (I.getNodeFromName(nface, 'ElementConnectivity')[1] == expected_ec).all()
  distri_elt  = I.getVal(MT.getDistribution(nface, 'Element'))
  distri_eltc = I.getVal(MT.getDistribution(nface, 'ElementConnectivity'))
  assert distri_elt.dtype == distri_eltc.dtype == pdm_gnum_dtype
  assert (distri_elt  == expected_elt_distri_full [[rank, rank+1, size]]).all()
  assert (distri_eltc == expected_eltc_distri_full[[rank, rank+1, size]]).all()
