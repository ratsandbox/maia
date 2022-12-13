import numpy as np
import maia.pytree        as PT
import maia.pytree.maia   as MT

from   maia.utils.parallel.utils import uniform_distribution

def create_distribution_node(n_elt, comm, name, parent_node):
  """
  setup CGNS node with distribution
  """
  distrib    = uniform_distribution(n_elt, comm)
  MT.newDistribution({name : distrib}, parent=parent_node)

def compute_plist_or_prange_distribution(node, comm):
  """
  Compute the distribution for a given node using its PointList or PointRange child
  If a PointRange node is found, the total lenght is getted from the product
  of the differences for each direction (cgns convention (cgns convention :
  first and last are included).
  If a PointList node is found, the total lenght is getted from the product of
  PointList#Size arrays, which store the size of the PL in each direction.
  """

  pr_n = PT.get_child_from_name(node, 'PointRange')
  pl_n = PT.get_child_from_name(node, 'PointList')

  if(pr_n):
    pr_lenght = PT.PointRange.n_elem(pr_n)
    create_distribution_node(pr_lenght, comm, 'Index', node)

  if(pl_n):
    pls_n   = PT.get_child_from_name(node, 'PointList#Size')
    pl_size = PT.get_value(pls_n)[1]
    create_distribution_node(pl_size, comm, 'Index', node)

def compute_connectivity_distribution(node):
  """
  Once ESO is loaded, update element distribution with ElementConnectivity array
  """
  eso_n  = PT.get_child_from_name(node, 'ElementStartOffset')
  if eso_n is None:
    raise RuntimeError
  size_n = PT.get_child_from_name(node, 'ElementConnectivity#Size')

  beg  = eso_n[1][0]
  end  = eso_n[1][-1]
  size = size_n[1][0]

  distri_n = MT.getDistribution(node)
  dtype = PT.get_child_from_name(distri_n, 'Element')[1].dtype
  PT.new_DataArray("ElementConnectivity", value=np.array([beg,end,size], dtype), parent=distri_n)
  PT.rm_children_from_name(node, 'ElementConnectivity#Size')


def compute_elements_distribution(zone, comm):
  """
  """
  for elt in PT.iter_children_from_label(zone, 'Elements_t'):
    create_distribution_node(PT.Element.Size(elt), comm, 'Element', elt)

def compute_zone_distribution(zone, comm):
  """
  """
  create_distribution_node(PT.Zone.n_vtx(zone) , comm, 'Vertex', zone)
  if PT.Zone.Type(zone) == 'Structured':
    create_distribution_node(PT.Zone.n_face(zone), comm, 'Face', zone)
  create_distribution_node(PT.Zone.n_cell(zone), comm, 'Cell'  , zone)

  compute_elements_distribution(zone, comm)

  for zone_subregion in PT.iter_children_from_label(zone, 'ZoneSubRegion_t'):
    compute_plist_or_prange_distribution(zone_subregion, comm)

  for flow_sol in PT.iter_children_from_label(zone, 'FlowSolution_t'):
    compute_plist_or_prange_distribution(flow_sol, comm)

  for bc in PT.iter_children_from_predicates(zone, 'ZoneBC_t/BC_t'):
    compute_plist_or_prange_distribution(bc, comm)
    for bcds in PT.iter_children_from_label(bc, 'BCDataSet_t'):
      compute_plist_or_prange_distribution(bcds, comm)

  for zone_gc in PT.iter_children_from_label(zone, 'ZoneGridConnectivity_t'):
    for gc in PT.iter_children_from_label(zone_gc, 'GridConnectivity_t'):
      compute_plist_or_prange_distribution(gc, comm)
    for gc in PT.iter_children_from_label(zone_gc, 'GridConnectivity1to1_t'):
      compute_plist_or_prange_distribution(gc, comm)

def add_distribution_info(dist_tree, comm, distribution_policy='uniform'):
  """
  """
  for zone in PT.iter_all_Zone_t(dist_tree):
    compute_zone_distribution(zone, comm)

def clean_distribution_info(dist_tree):
  """
  Remove the node related to distribution info from the dist_tree
  """
  distri_name = ":CGNS#Distribution"
  is_dist = lambda n : PT.get_label(n) in ['Elements_t', 'ZoneSubRegion_t', 'FlowSolution_t']
  is_gc   = lambda n : PT.get_label(n) in ['GridConnectivity_t', 'GridConnectivity1to1_t']
  for zone in PT.iter_all_Zone_t(dist_tree):
    PT.rm_children_from_name(zone, distri_name)
    for node in PT.iter_nodes_from_predicate(zone, is_dist):
      PT.rm_children_from_name(node, distri_name)
    for bc in PT.iter_nodes_from_predicates(zone, 'ZoneBC_t/BC_t'):
      PT.rm_nodes_from_name(bc, distri_name, depth=2)
    for gc in PT.iter_nodes_from_predicates(zone, ['ZoneGridConnectivity_t', is_gc]):
      PT.rm_children_from_name(gc, distri_name)
