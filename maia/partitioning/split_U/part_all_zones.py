import Converter.Internal as I
import numpy              as np

import Pypdm.Pypdm        as PDM

import maia.sids.sids as SIDS
from .cgns_to_pdm_dmesh       import cgns_dist_zone_to_pdm_dmesh
from .cgns_to_pdm_dmesh_nodal import cgns_dist_zone_to_pdm_dmesh_nodal
from .pdm_part_to_cgns_zone   import pdm_part_to_cgns_zone

def get_matching_joins(d_zones):
  """
  Scan all the grid connectivity nodes of the given zones and return
  an array of size #nb_gc pairing the joins :
  array [3,2,1,0] means that the matching pairs are (0,3) and (1,2).
  The join numbering must be included in dist_tree under nodes Ordinal/OrdinalOpp
  (see add_joins_ordinal.py)
  """
  jns = []
  for zone in d_zones:
    # > Get ZoneGridConnectivity List
    zone_gcs = I.getNodesFromType1(zone, 'ZoneGridConnectivity_t')
    if (zone_gcs != []):
      jns += I.getNodesFromType1(zone_gcs, 'GridConnectivity_t')
      jns += I.getNodesFromType1(zone_gcs, 'GridConnectivity1to1_t')

  # > Declare array
  join_to_opp = np.empty(len(jns), dtype=np.int32)

  # > Fill
  for jn in jns:
    join_id     = I.getNodeFromName1(jn, 'Ordinal')[1]
    join_opp_id = I.getNodeFromName1(jn, 'OrdinalOpp')[1]
    join_to_opp[join_id - 1] = join_opp_id - 1

  return join_to_opp

def zgc_original_pdm_to_cgns(p_zone):
  """
  Already exist in initial configuration
  """
  to_remove = list()
  for zone_gc in I.getNodesFromType1(p_zone, 'ZoneGridConnectivity_t'):
    for gc in I.getNodesFromType1(zone_gc, 'GridConnectivity_t'):
      if I.getNodeFromName1(gc, 'Ordinal') is not None: #Skip part joins
        pl       = I.getNodeFromName1(gc, 'PointList')[1]
        pl_d     = I.getNodeFromName1(gc, 'PointListDonor')[1]
        lngn     = I.getNodeFromPath (gc, ':CGNS#GlobalNumbering/Index')[1]
        donor    = I.getNodeFromName1(gc, 'Donor')[1]
        # opp_proc = I.getNodeFromName1(gc, 'OppRank')[1]
        # opp_part = I.getNodeFromName1(gc, 'OppPart')[1]
        # > List of couples (procs, parts) holding the opposite join
        opposed_parts = np.unique(donor, axis=0)
        for i_sub_jn, opp_part in enumerate(opposed_parts):
          join_n = I.newGridConnectivity(name      = I.getName(gc)+'.{0}'.format(i_sub_jn),
                                         donorName = I.getValue(gc)+'.P{0}.N{1}'.format(*opp_part),
                                         ctype     = 'Abutting1to1',
                                         parent    = zone_gc)

          matching_faces_idx = np.all(donor == opp_part, axis=1)

          # Extract sub arrays. OK to modify because indexing return a copy
          sub_pl   = pl  [:,matching_faces_idx]
          sub_pl_d = pl_d[:,matching_faces_idx]
          sub_lngn = lngn[matching_faces_idx]

          # Sort both pl and pld according to min joinId to ensure that
          # order is the same
          ordinal_cur = I.getNodeFromName1(gc, 'Ordinal')[1][0]
          ordinal_opp = I.getNodeFromName1(gc, 'OrdinalOpp')[1][0]
          ref_pl = sub_pl if ordinal_cur < ordinal_opp else sub_pl_d
          sort_idx = np.argsort(ref_pl[0])
          sub_pl  [0]   = sub_pl  [0][sort_idx]
          sub_pl_d[0]   = sub_pl_d[0][sort_idx]
          sub_lngn      = sub_lngn[sort_idx]

          I.newPointList(name='PointList'     , value=sub_pl      , parent=join_n)
          I.newPointList(name='PointListDonor', value=sub_pl_d    , parent=join_n)
          lntogn_ud = I.createUniqueChild(join_n, ':CGNS#GlobalNumbering', 'UserDefinedData_t')
          I.newDataArray('Index', value=sub_lngn, parent=lntogn_ud)
          #Copy decorative nodes
          for node in I.getChildren(gc):
            if I.getName(node) not in ['PointList', 'PointListDonor', ':CGNS#GlobalNumbering', 'Donor', 'Ordinal', 'OrdinalOpp']:
              I._addChild(join_n, node)

        to_remove.append(gc)
  for node in to_remove:
    I._rmNode(p_zone, node)


def prepare_part_weight(zones, n_part_per_zone, dzone_to_weighted_parts):
  part_weight = np.empty(sum(n_part_per_zone), dtype='float64')
  offset = 0
  for i_zone, zone in enumerate(zones):
    part_weight[offset:offset+n_part_per_zone[i_zone]] = dzone_to_weighted_parts[I.getName(zone)]
    offset += n_part_per_zone[i_zone]
  return part_weight

def set_mpart_join_connectivity(multi_part, zones, keep_alive):
  join_to_opp_array = get_matching_joins(zones)
  n_total_joins = join_to_opp_array.shape[0]
  multi_part.multipart_register_joins(n_total_joins, join_to_opp_array)
  keep_alive.append(join_to_opp_array)

def set_mpart_reordering(multipart, reorder_options, keep_alive):
  renum_cell_method = "PDM_PART_RENUM_CELL_" + reorder_options['cell_renum_method']
  renum_face_method = "PDM_PART_RENUM_FACE_" + reorder_options['face_renum_method']
  if "CACHEBLOCKING" in reorder_options['cell_renum_method']:
    cacheblocking_props = np.array([reorder_options['n_cell_per_cache'],
                                    1,
                                    1,
                                    reorder_options['n_face_per_pack'],
                                    reorder_options['graph_part_tool']],
                                    dtype='int32', order='c')
  else:
    cacheblocking_props = None
  multipart.multipart_set_reordering(-1,
                                      renum_cell_method.encode('utf-8'),
                                      renum_face_method.encode('utf-8'),
                                      cacheblocking_props)
  keep_alive.append(cacheblocking_props)

def set_mpart_dmeshes(multi_part, u_zones, comm, keep_alive):
  for i_zone, zone in enumerate(u_zones):
    #Determine NGON or ELMT
    elmt_types = [SIDS.ElementType(elmt) for elmt in I.getNodesFromType1(zone, 'Elements_t')]
    is_ngon = 22 in elmt_types
    if is_ngon:
      dmesh    = cgns_dist_zone_to_pdm_dmesh(zone, comm)
      keep_alive.append(dmesh)
      multi_part.multipart_register_block(i_zone, dmesh)
    else:
      dmesh_nodal = cgns_dist_zone_to_pdm_dmesh_nodal(zone, comm)
      keep_alive.append(dmesh_nodal)
      multi_part.multipart_register_dmesh_nodal(i_zone, dmesh_nodal)

def collect_mpart_partitions(multi_part, d_zones, n_part_per_zone, comm, post_options):
  """
  """
  concat_pdm_data = lambda i_part, i_zone : {**multi_part.multipart_val_get               (i_part, i_zone),
                                             **multi_part.multipart_graph_comm_vtx_val_get(i_part, i_zone),
                                             **multi_part.multipart_ghost_information_get (i_part, i_zone)}

  #part_path_nodes = I.createNode(':Ppart#ZonePaths', 'UserDefinedData_t', parent=part_base)

  all_parts = list()
  for i_zone, d_zone in enumerate(d_zones):
    # > TODO : join
    # add_paths_to_ghost_zone(d_zone, part_path_nodes)

    n_part = n_part_per_zone[i_zone]
    l_dims = [multi_part.multipart_dim_get(i_part, i_zone) for i_part in range(n_part)]
    l_data = [concat_pdm_data(i_part, i_zone)              for i_part in range(n_part)]

    parts = pdm_part_to_cgns_zone(d_zone, l_dims, l_data, comm, post_options)
    all_parts.extend(parts)

  return all_parts

def part_U_zones(u_zones, dzone_to_weighted_parts, comm, part_options):

  # Careful ! Some object must be deleted at the very end of the function,
  # since they are usefull for pdm
  keep_alive = list()

  # Deduce the number of parts for each zone from dzone->weighted_parts dict
  n_part_per_zone = np.array([len(dzone_to_weighted_parts[I.getName(zone)]) for zone in u_zones],
                             dtype=np.int32)
  keep_alive.append(n_part_per_zone)

  # Init multipart object
  part_weight = prepare_part_weight(u_zones, n_part_per_zone, dzone_to_weighted_parts)

  pdm_part_tool     = 1 if part_options['graph_part_tool'] == 'parmetis' else 2
  pdm_weight_method = 2
  multi_part = PDM.MultiPart(len(u_zones), n_part_per_zone, 0, pdm_part_tool, pdm_weight_method, part_weight, comm)

  # Setup
  #set_mpart_join_connectivity(multi_part, u_zones, keep_alive)
  set_mpart_dmeshes(multi_part, u_zones, comm, keep_alive)
  set_mpart_reordering(multi_part, part_options['reordering'], keep_alive)

  #Run and return parts
  multi_part.multipart_run_ppart()

  post_options = {k:part_options[k] for k in ['part_interface_loc', 'save_ghost_data']}
  u_parts = collect_mpart_partitions(multi_part, u_zones, n_part_per_zone, comm, post_options)

  import maia.tree_exchange.dist_to_part.recover_jn as JBTP
  JBTP.recover_jns(get_matching_joins(u_zones), u_zones, u_parts, comm)
  for part in u_parts:
    zgc_original_pdm_to_cgns(part)

  del(multi_part) # Force multi_part object to be deleted before n_part_per_zone array
  del(keep_alive)

  return u_parts


