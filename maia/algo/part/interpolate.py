from mpi4py import MPI
import numpy as np

import Pypdm.Pypdm as PDM

import Converter.Internal as I
import maia.pytree        as PT
import maia.pytree.maia   as MT

from maia                        import npy_pdm_gnum_dtype as pdm_gnum_dtype
from maia.utils                  import np_utils, layouts
from maia.transfer               import utils as te_utils
from maia.factory.dist_from_part import discover_nodes_from_matching

from maia.algo.part.geometry  import compute_cell_center

from .point_cloud_utils import get_point_cloud

def register_src_part(mesh_loc, i_part, part_zone, keep_alive):
  """
  Get connectivity of a partitioned zone and register it a mesh_location
  pdm object
  """

  gridc_n    = I.getNodeFromName1(part_zone, 'GridCoordinates')
  cx         = I.getNodeFromName1(gridc_n, 'CoordinateX')[1]
  cy         = I.getNodeFromName1(gridc_n, 'CoordinateY')[1]
  cz         = I.getNodeFromName1(gridc_n, 'CoordinateZ')[1]
  vtx_coords = np_utils.interweave_arrays([cx,cy,cz])
  keep_alive.append(vtx_coords)

  ngons  = [e for e in I.getNodesFromType1(part_zone, 'Elements_t') if PT.Element.CGNSName(e) == 'NGON_n']
  nfaces = [e for e in I.getNodesFromType1(part_zone, 'Elements_t') if PT.Element.CGNSName(e) == 'NFACE_n']
  assert len(nfaces) == len(ngons) == 1

  cell_face_idx = I.getNodeFromName1(nfaces[0], "ElementStartOffset")[1]
  cell_face     = I.getNodeFromName1(nfaces[0], "ElementConnectivity")[1]
  face_vtx_idx  = I.getNodeFromName1(ngons[0],  "ElementStartOffset")[1]
  face_vtx      = I.getNodeFromName1(ngons[0],  "ElementConnectivity")[1]

  vtx_ln_to_gn, face_ln_to_gn, cell_ln_to_gn = te_utils.get_entities_numbering(part_zone)

  n_cell = cell_ln_to_gn.shape[0]
  n_face = face_ln_to_gn.shape[0]
  n_vtx  = vtx_ln_to_gn .shape[0]

  center_cell = compute_cell_center(part_zone)
  keep_alive.append(cell_ln_to_gn)

  mesh_loc.part_set(i_part, n_cell, cell_face_idx, cell_face, cell_ln_to_gn,
                            n_face, face_vtx_idx, face_vtx, face_ln_to_gn,
                            n_vtx, vtx_coords, vtx_ln_to_gn)


# --------------------------------------------------------------------------
def create_subset_numbering(subset_l, parent_numbering_l, comm):
  """
  Create a sub (continuous) numbering from a parent numbering list (size = n_part)
  and a list of (local) indices to extract on each part (size = n_part)
  Warning ! Local indices start at 1 and not 0
  Return a dict containing the parent global id of extracted elements for each part
  and the sub global id of extracted elements for each part
  """
  assert len(subset_l) == len(parent_numbering_l)
  n_part = len(parent_numbering_l)

  subset_gnum = {"unlocated_extract_ln_to_gn" : list(),
                 "unlocated_sub_ln_to_gn"     : list()}

  gen_gnum = PDM.GlobalNumbering(3, n_part, 0, 0., comm)

  for i_part in range(n_part):
    extracted_ln_to_gn = layouts.extract_from_indices(parent_numbering_l[i_part], subset_l[i_part], 1, 1)
    gen_gnum.gnum_set_from_parent(i_part, extracted_ln_to_gn.shape[0], extracted_ln_to_gn)
    subset_gnum["unlocated_extract_ln_to_gn"].append(extracted_ln_to_gn)

  gen_gnum.gnum_compute()

  for i_part in range(n_part):
    sub_ln_to_gn = gen_gnum.gnum_get(i_part)
    subset_gnum["unlocated_sub_ln_to_gn"].append(sub_ln_to_gn["gnum"])

  return subset_gnum

# --------------------------------------------------------------------------
def create_interpolator(src_parts_per_dom,
                        tgt_parts_per_dom,
                        comm,
                        location = 'CellCenter',
                        strategy = 'LocationAndClosest',
                        loc_tolerance = 1E-6,
                        order = 0):
  """
  """
  n_dom_src = len(src_parts_per_dom)
  n_dom_tgt = len(tgt_parts_per_dom)

  assert n_dom_src == n_dom_tgt == 1
  assert strategy in ['LocationAndClosest', 'Location', 'Closest']

  n_part_src = len(src_parts_per_dom[0])
  n_part_tgt = len(tgt_parts_per_dom[0])

  keep_alive = list()
  one_or_two = 0 #This one will be one or two depending of chosen strategy

  # Those one will be usefull in every strategy -> compute it only once
  all_tgt_coords = [list() for dom in range(n_dom_tgt)]
  all_tgt_lngn   = [list() for dom in range(n_dom_tgt)]
  for i_domain, tgt_part_zones in enumerate(tgt_parts_per_dom):
    for i_part, tgt_part in enumerate(tgt_part_zones):
      coords, ln_to_gn = get_point_cloud(tgt_part, location)
      all_tgt_coords[i_domain].append(coords)
      all_tgt_lngn  [i_domain].append(ln_to_gn)

  #Phase 1 -- localisation
  from . import localize as LOC
  from . import closest_points as CLO
  if strategy != 'Closest':
    one_or_two += 1
    location_out, location_out_inv = LOC._localize_points(src_parts_per_dom, tgt_parts_per_dom, \
        location, comm, True, loc_tolerance)

    all_unlocated = [data['unlocated_ids'] for data in location_out[0]]
    all_located_inv = location_out_inv[0]
    n_unlocated = sum([t.size for t in all_unlocated])
    n_tot_unlocated = comm.allreduce(n_unlocated, op=MPI.SUM)
    if(comm.Get_rank() == 0):
      print(" n_tot_unlocated = ", n_tot_unlocated )


  all_closest_inv = list()
  if strategy == 'Closest' or (strategy == 'LocationAndClosest' and n_tot_unlocated > 0):
    one_or_two += 1

    # > Setup source for closest point
    src_clouds = []
    for i_domain, src_part_zones in enumerate(src_parts_per_dom):
      for i_part, src_part in enumerate(src_part_zones):
        src_clouds.append(get_point_cloud(src_part, 'CellCenter'))

    # > Setup target for closest point
    tgt_clouds = []
    if strategy == 'Closest':
      for i_domain, tgt_part_zones in enumerate(tgt_parts_per_dom):
        for i_part, tgt_part in enumerate(tgt_part_zones):
          tgt_clouds.append(get_point_cloud(tgt_part, location))
    else:
      # > If we previously did a mesh location, we only treat unlocated points : create a sub global numbering
      from .import point_cloud_utils as PCU
      for i_domain, tgt_part_zones in enumerate(tgt_parts_per_dom):
        for i_part, tgt_part in enumerate(tgt_part_zones):
          indices = all_unlocated[i_part] #One domain so OK
          tgt_cloud = get_point_cloud(tgt_part, location)
          sub_cloud = PCU.extract_sub_cloud(*tgt_cloud, indices)
          tgt_clouds.append(sub_cloud)
      all_extracted_lngn = [sub_cloud[1] for sub_cloud in tgt_clouds]
      all_sub_lngn = PCU.create_sub_numbering(all_extracted_lngn, comm) #This one is collective
      tgt_clouds = [(tgt_cloud[0], sub_lngn) for tgt_cloud, sub_lngn in zip(tgt_clouds, all_sub_lngn)]

    all_closest, all_closest_inv = CLO._closest_points(src_clouds, tgt_clouds, comm, reverse=True)

    #If we worked on sub gnum, we must go back to original numbering
    if strategy != 'Closest':
      gnum_to_transform = [results["tgt_in_src"] for results in all_closest_inv]
      PDM.transform_to_parent_gnum(gnum_to_transform, all_sub_lngn, all_extracted_lngn, comm)


  # > Now create Interpolation object
  # We use one_or_two to register or two src part if both location and closest point where enabled
  interpolator = PDM.InterpolateFromMeshLocation(n_point_cloud=1, comm=comm)
  interpolator.mesh_global_data_set(one_or_two*n_part_src) #  For now only on domain is supported
  interpolator.n_part_cloud_set(0, n_part_tgt) # Pour l'instant 1 cloud et 1 partition

  for i_domain, tgt_part_zones in enumerate(tgt_parts_per_dom): #For now only one domain
    for i_part, tgt_part in enumerate(tgt_part_zones):
      #We can resuse part data, which is already computed
      coords   = all_tgt_coords[i_domain][i_part]
      ln_to_gn = all_tgt_lngn[i_domain][i_part]
      interpolator.cloud_set(0, i_part, ln_to_gn.shape[0], coords, ln_to_gn)

  for i_part, res_loc in enumerate(all_located_inv):
    interpolator.points_in_elt_set(one_or_two*i_part, 0, **res_loc)
  for i_part, res_clo in enumerate(all_closest_inv):
    interpolator.points_in_elt_set(one_or_two*i_part+(one_or_two-1), 0, res_clo["tgt_in_src_idx"], res_clo["tgt_in_src"],
        None, None, None, None, None, None)

  # interpolator.compute()
  return interpolator, one_or_two

def interpolate_fields(interpolator, n_field_per_part, src_parts_per_dom, tgt_parts_per_dom, container_name, output_loc):
  """
  Use interpolator to echange a container and put solution in target tree
  """
  assert len(src_parts_per_dom) == len(tgt_parts_per_dom) == 1

  #Check that solutions are known on each source partition
  fields_per_part = list()
  for i_domain, src_parts in enumerate(src_parts_per_dom):
    for src_part in src_parts:
      container = I.getNodeFromPath(src_part, container_name)
      assert PT.Subset.GridLocation(container) == 'CellCenter' #Only cell center sol supported for now
      fields_name = sorted([I.getName(array) for array in I.getNodesFromType1(container, 'DataArray_t')])
    fields_per_part.append(fields_name)
  assert fields_per_part.count(fields_per_part[0]) == len(fields_per_part)

  #Cleanup target partitions
  for i_domain, tgt_parts in enumerate(tgt_parts_per_dom):
    for i_part, tgt_part in enumerate(tgt_parts):
      I._rmNodesByName(tgt_part, container_name)
      fs = I.createUniqueChild(tgt_part, container_name, 'FlowSolution_t')
      I.newGridLocation(output_loc, fs)

  # Collect source data and interpolate
  for field_name in fields_per_part[0]:
    field_path = container_name + '/' + field_name
    list_part_data_in = list()
    for i_domain, src_parts in enumerate(src_parts_per_dom):
      for src_part in src_parts:
        src_data = I.getNodeFromPath(src_part, field_path)[1]
        for i in range(n_field_per_part):
          list_part_data_in.append(src_data)

    results_interp = interpolator.exch(0, list_part_data_in)
    for i_domain, tgt_parts in enumerate(tgt_parts_per_dom):
      for i_part, tgt_part in enumerate(tgt_parts):
        fs = I.getNodeFromPath(tgt_part, container_name)
        if PT.Zone.Type(tgt_part) == 'Unstructured':
          I.createUniqueChild(fs, field_name, 'DataArray_t', results_interp[i_part])
        else:
          shape = PT.Zone.CellSize(tgt_part) if output_loc == 'CellCenter' else PT.Zone.VertexSize(tgt_part)
          I.createUniqueChild(fs, field_name, 'DataArray_t', results_interp[i_part].reshape(shape, order='F'))


def interpolate_from_parts_per_dom(src_parts_per_dom, tgt_parts_per_dom, comm, containers_name, location, **options):
  """
  Low level interface for interpolation
  Input are a list of partitioned zones for each src domain, and a list of partitioned zone for each tgt
  domain. Lists mush be cohérent across procs, ie we must have an empty entry if a proc does not know a domain.

  containers_name is the list of FlowSolution containers to be interpolated
  location is the output location (CellCenter or Vertex); input location must be CellCenter
  **options are passed to interpolator creationg function, see create_interpolator
  """
  interpolator, one_or_two = create_interpolator(src_parts_per_dom, tgt_parts_per_dom, comm, location, **options)
  for container_name in containers_name:
    interpolate_fields(interpolator, one_or_two, src_parts_per_dom, tgt_parts_per_dom, container_name, location)

def interpolate_from_dom_names(src_tree, src_doms, tgt_tree, tgt_doms, comm, containers_name, location, **options):
  """
  Helper function calling interpolate_from_parts_per_dom from the src and tgt part_trees +
  a list of src domain names and target domains names.
  Names must be in the formalism "DistBaseName/DistZoneName"

  See interpolate_from_parts_per_dom for documentation
  """
  assert len(src_doms) == len(tgt_doms) == 1
  src_parts_per_dom = list()
  tgt_parts_per_dom = list()
  for src_dom in src_doms:
    src_parts_per_dom.append(te_utils.get_partitioned_zones(src_tree, src_dom))
  for tgt_dom in tgt_doms:
    tgt_parts_per_dom.append(te_utils.get_partitioned_zones(tgt_tree, tgt_dom))

  interpolate_from_parts_per_dom(src_parts_per_dom, tgt_parts_per_dom, comm, containers_name, location, **options)

def interpolate_from_part_trees(src_tree, tgt_tree, comm, containers_name, location, **options):
  """Interpolate fields between two partitionned trees.

  For now, interpolation is limited to lowest order: target points take the value of the
  closest point (or their englobing cell, depending of choosed options) in the source mesh.
  Interpolation strategy can be controled thought the options kwargs:

  - ``strategy`` (default = 'LocationAndClosest') -- control interpolation method

    - 'Closest' : Target points take the value of the closest source cell center.
    - 'Location' : Target points take the value of the cell in which they are located.
      Unlocated points have take a ``NaN`` value.
    - 'LocationAndClosest' : Use 'Location' method and then 'ClosestPoint' method
      for the unlocated points.

  - ``loc_tolerance`` (default = 1E-6) -- Geometric tolerance for Location method.

  Important:
    - Source fields must be located at CellCenter.
    - Source tree must be unstructured and have a ngon connectivity.
    - Partitions must come from a single initial domain on both source and target tree.

  Args:
    src_tree (CGNSTree): Source tree, partitionned. Only U-NGon connectivities are managed.
    tgt_tree (CGNSTree): Target tree, partitionned. Structured or U-NGon connectivities are managed.
    comm       (MPIComm): MPI communicator
    containers_name (list of str) : List of the names of the source FlowSolution_t nodes to transfer.
    location ({'CellCenter', 'Vertex'}) : Expected target location of the fields.
    **options: Options related to interpolation strategy

  Example:
      .. literalinclude:: snippets/test_algo.py
        :start-after: #interpolate_from_part_trees@start
        :end-before: #interpolate_from_part_trees@end
        :dedent: 2
  """

  dist_src_doms = I.newCGNSTree()
  discover_nodes_from_matching(dist_src_doms, [src_tree], 'CGNSBase_t/Zone_t', comm,
                                    merge_rule=lambda zpath : MT.conv.get_part_prefix(zpath))
  src_parts_per_dom = list()
  for zone_path in PT.predicates_to_paths(dist_src_doms, 'CGNSBase_t/Zone_t'):
    src_parts_per_dom.append(te_utils.get_partitioned_zones(src_tree, zone_path))

  dist_tgt_doms = I.newCGNSTree()
  discover_nodes_from_matching(dist_tgt_doms, [tgt_tree], 'CGNSBase_t/Zone_t', comm,
                                    merge_rule=lambda zpath : MT.conv.get_part_prefix(zpath))

  tgt_parts_per_dom = list()
  for zone_path in PT.predicates_to_paths(dist_tgt_doms, 'CGNSBase_t/Zone_t'):
    tgt_parts_per_dom.append(te_utils.get_partitioned_zones(tgt_tree, zone_path))

  interpolate_from_parts_per_dom(src_parts_per_dom, tgt_parts_per_dom, comm, containers_name, location, **options)

