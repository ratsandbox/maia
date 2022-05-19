from pytest_mpi_check._decorator import mark_mpi_test
from mpi4py import MPI
import numpy as np

import Generator.PyTree   as G
import Converter.Internal as I
import maia.pytree        as PT
import maia.pytree.maia   as MT

from maia.utils.yaml    import parse_yaml_cgns
from maia.factory.dcube_generator import dcube_generate
from maia import npy_pdm_gnum_dtype as pdm_dtype

from maia.factory import dist_from_part as DFP

@mark_mpi_test(3)
class Test_discover_nodes_from_matching:
  pt = [\
  """
Zone.P0.N0 Zone_t:
  ZBC ZoneBC_t:
    BCA BC_t "wall":
      Family FamilyName_t "myfamily":
  """,
  """
Zone.P1.N0 Zone_t:
  ZGC ZoneGridConnectivity_t:
    match.0 GridConnectivity_t:
    match.1 GridConnectivity_t:
  """,
  """
Zone.P2.N0 Zone_t:
  ZBC ZoneBC_t:
    BCB BC_t "farfield":
      GridLocation GridLocation_t "FaceCenter":
Zone.P2.N1 Zone_t:
  ZBC ZoneBC_t:
    BCA BC_t "wall":
      Family FamilyName_t "myfamily":
  """]
  def test_simple(self, sub_comm):
    part_zones = parse_yaml_cgns.to_nodes(self.pt[sub_comm.Get_rank()])

    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, part_zones, 'ZoneBC_t/BC_t', sub_comm)
    assert (I.getType(I.getNodeFromPath(dist_zone, 'ZBC/BCA')) == "BC_t")
    assert (I.getType(I.getNodeFromPath(dist_zone, 'ZBC/BCB')) == "BC_t")

    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, part_zones, ['ZoneBC_t', 'BC_t'], sub_comm)
    assert (I.getType(I.getNodeFromPath(dist_zone, 'ZBC/BCA')) == "BC_t")
    assert (I.getType(I.getNodeFromPath(dist_zone, 'ZBC/BCB')) == "BC_t")

    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, part_zones, ["ZoneBC_t", 'BC_t'], sub_comm)
    assert (I.getType(I.getNodeFromPath(dist_zone, 'ZBC/BCA')) == "BC_t")
    assert (I.getType(I.getNodeFromPath(dist_zone, 'ZBC/BCB')) == "BC_t")

    dist_zone = I.newZone('Zone')
    queries = ["ZoneBC_t", lambda n : I.getType(n) == "BC_t" and I.getName(n) != "BCA"]
    DFP.discover_nodes_from_matching(dist_zone, part_zones, queries, sub_comm)
    assert (I.getNodeFromPath(dist_zone, 'ZBC/BCA') == None)
    assert (I.getType(I.getNodeFromPath(dist_zone, 'ZBC/BCB')) == "BC_t")

  def test_short(self, sub_comm):
    part_tree = parse_yaml_cgns.to_cgns_tree(self.pt[sub_comm.Get_rank()])
    part_nodes = [I.getNodeFromPath(zone, 'ZBC') for zone in I.getZones(part_tree)\
      if I.getNodeFromPath(zone, 'ZBC') is not None]

    dist_node = I.createNode('SomeName', 'UserDefinedData_t')
    DFP.discover_nodes_from_matching(dist_node, part_nodes, 'BC_t', sub_comm)
    assert I.getNodeFromPath(dist_node, 'BCA') is not None
    assert I.getNodeFromPath(dist_node, 'BCB') is not None

    dist_node = I.createNode('SomeName', 'UserDefinedData_t')
    queries = [lambda n : I.getType(n) == "BC_t" and I.getName(n) != "BCA"]
    DFP.discover_nodes_from_matching(dist_node, part_nodes, queries, sub_comm)
    assert I.getNodeFromPath(dist_node, 'BCA') is None
    assert (I.getType(I.getNodeFromPath(dist_node, 'BCB')) == "BC_t")

  def test_getvalue(self, sub_comm):
    part_tree = parse_yaml_cgns.to_cgns_tree(self.pt[sub_comm.Get_rank()])
    for zbc in I.getNodesFromName(part_tree, 'ZBC'):
      I.setValue(zbc, 'test')

    # get_value as a string
    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), 'ZoneBC_t/BC_t', sub_comm)
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC')) == 'test'
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC/BCA')) == None
    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), 'ZoneBC_t/BC_t', sub_comm, get_value='none')
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC')) == None
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC/BCA')) == None
    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), 'ZoneBC_t/BC_t', sub_comm, get_value='all')
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC')) == 'test'
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC/BCA')) == 'wall'
    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), 'ZoneBC_t/BC_t', sub_comm, get_value='ancestors')
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC')) == 'test'
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC/BCA')) == None
    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), 'ZoneBC_t/BC_t', sub_comm, get_value='leaf')
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC')) == None
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC/BCA')) == 'wall'

    # get_value as a list
    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), 'ZoneBC_t/BC_t', sub_comm, get_value=[False, False])
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC')) == None
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC/BCA')) == None
    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), 'ZoneBC_t/BC_t', sub_comm, get_value=[True, False])
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC')) == 'test'
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC/BCA')) == None

    # get_value and search with predicate as lambda
    dist_zone = I.newZone('Zone')
    queries = ["ZoneBC_t", lambda n : I.getType(n) == "BC_t" and I.getName(n) != "BCA"]
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), queries, sub_comm, get_value='all')
    assert I.getNodeFromPath(dist_zone, 'BCA') is None
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC')) == 'test'
    assert I.getValue(I.getNodeFromPath(dist_zone, 'ZBC/BCB')) == 'farfield'

  def test_with_childs(self, sub_comm):
    part_tree = parse_yaml_cgns.to_cgns_tree(self.pt[sub_comm.Get_rank()])

    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), 'ZoneBC_t/BC_t', sub_comm,
                                child_list=['FamilyName_t', 'GridLocation'])
    assert (I.getValue(I.getNodeFromPath(dist_zone, 'ZBC/BCA/Family')) == "myfamily")
    assert (I.getType(I.getNodeFromPath(dist_zone, 'ZBC/BCA/Family')) == "FamilyName_t")
    assert (I.getValue(I.getNodeFromPath(dist_zone, 'ZBC/BCB/GridLocation')) == "FaceCenter")
    assert (I.getType(I.getNodeFromPath(dist_zone, 'ZBC/BCB/GridLocation')) == "GridLocation_t")

    dist_zone = I.newZone('Zone')
    queries = ["ZoneBC_t", lambda n : I.getType(n) == "BC_t" and I.getName(n) != "BCA"]
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), queries, sub_comm,
                                      child_list=['FamilyName_t', 'GridLocation'])
    assert (I.getValue(I.getNodeFromPath(dist_zone, 'ZBC/BCB/GridLocation')) == "FaceCenter")
    assert (I.getType(I.getNodeFromPath(dist_zone, 'ZBC/BCB/GridLocation')) == "GridLocation_t")

  def test_with_rule(self, sub_comm):
    part_tree = parse_yaml_cgns.to_cgns_tree(self.pt[sub_comm.Get_rank()])

    # Exclude from node name
    dist_zone = I.newZone('Zone')
    queries = ["ZoneBC_t", lambda n : I.getType(n) == "BC_t" and not 'A' in I.getName(n)]
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), queries, sub_comm,
                                      child_list=['FamilyName_t', 'GridLocation'])
    assert I.getNodeFromPath(dist_zone, 'ZBC/BCA') is None
    assert I.getNodeFromPath(dist_zone, 'ZBC/BCB') is not None

    # Exclude from node content
    dist_zone = I.newZone('Zone')
    queries = ["ZoneBC_t", lambda n : I.getType(n) == "BC_t" and I.getNodeFromType1(n, 'FamilyName_t') is not None]
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), queries, sub_comm,
                                      child_list=['FamilyName_t', 'GridLocation'])
    assert I.getNodeFromPath(dist_zone, 'ZBC/BCA') is not None
    assert I.getNodeFromPath(dist_zone, 'ZBC/BCB') is None

  def test_multiple(self, sub_comm):
    gc_path = 'ZoneGridConnectivity_t/GridConnectivity_t'
    part_tree = parse_yaml_cgns.to_cgns_tree(self.pt[sub_comm.Get_rank()])

    dist_zone = I.newZone('Zone')
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), gc_path, sub_comm)
    assert I.getNodeFromPath(dist_zone, 'ZGC/match.0') is not None
    assert I.getNodeFromPath(dist_zone, 'ZGC/match.1') is not None

    dist_zone = I.newZone('Zone')
    queries = ["ZoneGridConnectivity_t", "GridConnectivity_t"]
    DFP.discover_nodes_from_matching(dist_zone, I.getZones(part_tree), queries, sub_comm,\
        merge_rule=lambda path : MT.conv.get_split_prefix(path))
    assert I.getNodeFromPath(dist_zone, 'ZGC/match.0') is None
    assert I.getNodeFromPath(dist_zone, 'ZGC/match.1') is None
    assert I.getNodeFromPath(dist_zone, 'ZGC/match') is not None

  def test_zones(self, sub_comm):
    part_tree = I.newCGNSTree()
    if sub_comm.Get_rank() == 0:
      part_base = I.newCGNSBase('BaseA', parent=part_tree)
      I.newZone('Zone.P0.N0', parent=part_base)
    elif sub_comm.Get_rank() == 1:
      part_base = I.newCGNSBase('BaseB', parent=part_tree)
      I.newZone('Zone.withdot.P1.N0', parent=part_base)
    elif sub_comm.Get_rank() == 2:
      part_base = I.newCGNSBase('BaseA', parent=part_tree)
      I.newZone('Zone.P2.N0', parent=part_base)
      I.newZone('Zone.P2.N1', parent=part_base)

    dist_tree = I.newCGNSTree()
    DFP.discover_nodes_from_matching(dist_tree, [part_tree], 'CGNSBase_t/Zone_t', sub_comm,\
        merge_rule=lambda zpath : MT.conv.get_part_prefix(zpath))

    assert len(I.getZones(dist_tree)) == 2
    assert I.getNodeFromPath(dist_tree, 'BaseA/Zone') is not None
    assert I.getNodeFromPath(dist_tree, 'BaseB/Zone.withdot') is not None


@mark_mpi_test(3)
def test_recover_dist_tree(sub_comm):
  # > PartTree creation (cumbersome because of old ngon norm)
  # Value test is already performed in subfunction tests
  part_tree = I.newCGNSTree()
  if sub_comm.Get_rank() < 2:
    part_base = I.newCGNSBase(parent=part_tree)
    distri_ud = MT.newGlobalNumbering()
    if sub_comm.Get_rank() == 0:
      # part_zone = G.cartNGon((0,0,0), (.5,.5,.5), (3,3,3))
      part_zone = I.getZones(dcube_generate(3, 1, [0., 0., 0.], MPI.COMM_SELF))[0]
      I._rmNodesByName(part_zone, 'ZoneBC')
      I._rmNodesByName(part_zone, ':CGNS#Distribution')

      vtx_gnum = np.array([1,2,3,6,7,8,11,12,13,16,17,18,21,22,23,26,27,28,31,32,33,36,37,38,41,42,43], pdm_dtype)
      cell_gnum = np.array([1,2,5,6,9,10,13,14], pdm_dtype)
      ngon_gnum = np.array([1,2,3,6,7,8,11,12,13,16,17,18,21,22,25,26,29,30,33,34,37,38,41,42,45,46,49,
                            50,53,54,57,58,61,62,65,66], pdm_dtype)
      zbc = I.newZoneBC(parent=part_zone)
      bc = I.newBC(btype='BCWall', pointList=[[1,4,2,3]], parent=zbc)
      I.newGridLocation('FaceCenter', bc)
      MT.newGlobalNumbering({'Index' : np.array([1,2,3,4], pdm_dtype)}, parent=bc)
    else:
      # part_zone = G.cartNGon((1,0,0), (.5,.5,.5), (3,3,3))
      part_zone = I.getZones(dcube_generate(3, 1, [1., 0., 0.], MPI.COMM_SELF))[0]
      I._rmNodesByName(part_zone, 'ZoneBC')
      I._rmNodesByName(part_zone, ':CGNS#Distribution')
      vtx_gnum =  np.array([3,4,5, 8,9,10,13,14,15,18,19,20,23,24,25,28,29,30,33,34,35,38,39,40,43,44,45], pdm_dtype)
      cell_gnum = np.array([3,4,7,8,11,12,15,16], pdm_dtype)
      ngon_gnum = np.array([3,4,5,8,9,10,13,14,15,18,19,20,23,24,27,28,31,32,35,36,39,40,43,44,
                            47,48,51,52,55,56,59,60,63,64,67,68], pdm_dtype)

    ngon = I.getNodeFromPath(part_zone, 'NGonElements')
    MT.newGlobalNumbering({'Element' : ngon_gnum}, parent=ngon)

    nface_ec = np.empty(8*6, dtype=I.getNodeFromName(ngon, 'ElementConnectivity')[1].dtype)
    nface_count = np.zeros(8, int)
    face_n = PT.sids.Element.Size(ngon)
    for iface, (lCell, rCell) in enumerate(I.getNodeFromName1(ngon, 'ParentElements')[1]):
      nface_ec[6*(lCell-1-face_n) + nface_count[lCell-1-face_n]] = iface + 1
      nface_count[lCell-1-face_n] += 1
      if rCell > 0:
        nface_ec[6*(rCell-1-face_n) + nface_count[rCell-1-face_n]] = iface + 1
        nface_count[rCell-1-face_n] += 1
    nface = I.newElements('NFaceElements', 'NFACE', nface_ec, [36+1, 36+8], parent=part_zone)
    I.newDataArray('ElementStartOffset', np.arange(0, 6*(8+1), 6), nface)
    MT.newGlobalNumbering({'Element' : cell_gnum}, parent=nface)

    I.newDataArray('Vertex', vtx_gnum,  parent=distri_ud)
    I.newDataArray('Cell',   cell_gnum, parent=distri_ud)

    part_zone[0] = "Zone.P{0}.N0".format(sub_comm.Get_rank())
    I._addChild(part_base, part_zone)
    I._addChild(part_zone, distri_ud)

  dist_tree = DFP.recover_dist_tree(part_tree, sub_comm)

  dist_zone = I.getNodeFromName(dist_tree, 'Zone')
  assert (dist_zone[1] == [[45,16,0]]).all()
  assert (I.getNodeFromPath(dist_zone, 'NGonElements/ElementRange')[1] == [1,68]).all()
  assert (I.getNodeFromPath(dist_zone, 'NFaceElements/ElementRange')[1] == [69,84]).all()
  assert (I.getValue(I.getNodeFromPath(dist_zone, 'ZoneBC/BC')) == "BCWall")