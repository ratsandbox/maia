# =======================================================================================
# ---------------------------------------------------------------------------------------
from    mpi4py import MPI
import  numpy as np

import  maia.pytree as PT
import  maia
from    maia.transfer import utils                as TEU
from    maia.factory  import dist_from_part
from    maia.utils    import np_utils, layouts, py_utils

import Pypdm.Pypdm as PDM
# ---------------------------------------------------------------------------------------
# =======================================================================================

# =======================================================================================
# ---------------------------------------------------------------------------------------

def starting_elt(part_zone,location):
  switcher={
            'Vertex'    : 1,
            'EdgeCenter': None,
            'FaceCenter': PT.get_node_from_path(part_zone,'NGonElements/ElementRange' )[1][0],
            'CellCenter': PT.get_node_from_path(part_zone,'NFaceElements/ElementRange')[1][0]
            }
  return switcher.get(location,"Invalid location")
# ---------------------------------------------------------------------------------------
# =======================================================================================



# =======================================================================================
# ---------------------------------------------------------------------------------------
class Extractor:
  def __init__( self,
                part_tree, point_list, location, comm,
                equilibrate=1,
                graph_part_tool="hilbert"):

    self.part_tree        = part_tree
    self.point_list       = point_list
    self.location         = location
    self.equilibrate      = equilibrate
    self.graph_part_tool  = graph_part_tool
    self.exch_tool_box    = list()

    # Get zones by domains
    part_tree_per_dom = dist_from_part.get_parts_per_blocks(part_tree, comm).values()

    # Check : monodomain
    assert(len(part_tree_per_dom)==1)

    # Is there PE node
    if (PT.get_node_from_name(part_tree,'ParentElements') is not None): self.put_pe = True
    else                                                              : self.put_pe = False
    
    # ExtractPart dimension
    select_dim  = { 'Vertex':0 ,'EdgeCenter':1 ,'FaceCenter':2 ,'CellCenter':3}
    assert self.location in select_dim.keys()
    self.dim    = select_dim[self.location]
    assert self.dim in [0,2,3],"[MAIA] Error : dimensions 0 and 1 not yet implemented"
    
    # ExtractPart CGNSTree
    self.extract_part_tree = PT.new_CGNSTree()
    self.extract_part_base = PT.new_CGNSBase('Base', cell_dim=self.dim, phy_dim=3, parent=self.extract_part_tree)

    # Compute extract part of each domain
    for i_domain, part_zones in enumerate(part_tree_per_dom):
      point_list_domain = list()
      for i_part,part_zone in enumerate(part_zones):
        point_list_domain.append( self.point_list[i_domain][i_part]
                                - starting_elt(part_zone,self.location) +1 )
      
      # extract part from point list
      extract_part_zone,etb = extract_part_one_domain(part_zones, point_list_domain, self.dim, comm,
                                                         equilibrate=self.equilibrate,
                                                         graph_part_tool=self.graph_part_tool,
                                                         put_pe=self.put_pe)
      self.exch_tool_box.append(etb)
      PT.add_child(self.extract_part_base, extract_part_zone)
# ---------------------------------------------------------------------------------------
  

# ---------------------------------------------------------------------------------------
  def exchange_fields(self, fs_container, comm) :
    _exchange_field(self.part_tree, self.extract_part_tree, self.exch_tool_box, fs_container, comm)
    return None
# ---------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------
  def save_parent_num(self) :
    # Placement in Extract_part_Tree
    print("Not implemented yet")
    return None
# ---------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------
  def get_extract_part_tree(self) :
    return self.extract_part_tree 
# ---------------------------------------------------------------------------------------
  
# ---------------------------------------------------------------------------------------
# =======================================================================================




# =======================================================================================
# ---------------------------------------------------------------------------------------
def exchange_field_one_domain(part_zones, part_zone_ep, exch_tool_box, containers_name, comm) :

  loc_correspondance = {'Vertex'    : 'Vertex',
                        'CellCenter': 'Cell'}

  # Part 1 : EXTRACT_PART
  # Part 2 : VOLUME
  for container_name in containers_name :
    # --- Get all fields names and location ---------------------------------------------
    all_fld_names   = list()
    all_locs        = list()
    all_labels      = list()
    all_ordering    = list()
    all_stride_int  = list()
    all_stride_bool = list()
    all_part_gnum1  = list()
    for part_zone in part_zones:
      container   = PT.request_child_from_name(part_zone, container_name)
      fld_names   = {PT.get_name(n) for n in PT.iter_children_from_label(container, "DataArray_t")}
      py_utils.append_unique(all_fld_names, fld_names)
      py_utils.append_unique(all_locs     , PT.Subset.GridLocation(container))
      py_utils.append_unique(all_labels   , PT.get_label(container))
    if len(part_zones) > 0:
      assert len(all_labels) == len(all_locs) == len(all_fld_names) == 1
      tag = comm.Get_rank()
      loc_and_fields = all_locs[0], list(all_fld_names[0])
    else:
      tag = -1
      loc_and_fields = None
    master = comm.allreduce(tag, op=MPI.MAX) # No check global ?
    gridLocation, flds_in_container_names = comm.bcast(loc_and_fields, master)
    assert(gridLocation in ['Vertex','CellCenter'])
    assert(all_labels[0]in ['FlowSolution_t','ZoneSubRegion_t'])

    
    # --- Get PTP by location -----------------------------------------------------------
    ptp     = exch_tool_box['part_to_part']
    ptp_loc = ptp[gridLocation]
    
    # --- Get parent_elt by location -----------------------------------------------------------
    parent_elt     = exch_tool_box['parent_elt']
    parent_elt_loc = parent_elt[gridLocation]
    

    # Get reordering informations if point_list
    # https://stackoverflow.com/questions/8251541/numpy-for-every-element-in-one-array-find-the-index-in-another-array
    partial_field = False
    for i_part,part_zone in enumerate(part_zones):

      container        = PT.request_child_from_name(part_zone, container_name)
      point_list_node  = PT.get_child_from_label(container,'IndexArray_t')

      if point_list_node is not None :
        partial_field = True # Reverse_iexch will be different
        part_gnum1  = ptp_loc.get_gnum1_come_from()[i_part]['come_from'] # Get partition order
        ref_lnum2   = ptp_loc.get_referenced_lnum2()[i_part] # Get partition order
        point_list  = PT.get_value(point_list_node)[0]
        point_list  = point_list - starting_elt(part_zone, gridLocation) +1 # +1 to fit gnum indexation

        if (point_list.size==0):

          ref_lnum2_idx = np.empty(0,dtype=np.int32)
          stride        = np.zeros(ref_lnum2.shape,dtype=np.int32)
          all_part_gnum1.append(np.empty(0,dtype=np.int32)) # Select only part1_gnum that is in part2 point_list
        else :
          sort_idx    = np.argsort(point_list)                 # Sort order of point_list ()
          order       = np.searchsorted(point_list,ref_lnum2,sorter=sort_idx)
          ref_lnum2_idx = np.take(sort_idx, order, mode="clip")
          
          stride = point_list[ref_lnum2_idx] == ref_lnum2
          all_part_gnum1 .append(part_gnum1[stride]) # Select only part1_gnum that is in part2 point_list

        all_ordering   .append(ref_lnum2_idx)
        all_stride_bool.append(stride)
        all_stride_int .append(stride.astype(np.int32))


    # --- FlowSolution node def by zone -------------------------------------------------
    # Tout en FlowSolution pour le moment parce que le part_to_dist transfère pas les ZSR
    # FS_ep = PT.new_FlowSolution(container_name, loc=gridLocation, parent=part_zone_ep)
    if (all_labels[0]=='FlowSolution_t'):
      FS_ep = PT.new_FlowSolution(container_name, loc=gridLocation, parent=part_zone_ep)
    elif (all_labels[0]=='ZoneSubRegion_t'):
      FS_ep = PT.new_ZoneSubRegion(container_name, loc=gridLocation, parent=part_zone_ep)
    else :
      raise TypeError

    # Echange gnum to retrieve flowsol new point_list
    if point_list_node is not None :
      req_id = ptp_loc.reverse_iexch( PDM._PDM_MPI_COMM_KIND_P2P,
                                      PDM._PDM_PART_TO_PART_DATA_DEF_ORDER_GNUM1_COME_FROM,
                                      all_part_gnum1,
                                      part2_stride=all_stride_int)
      part1_strid, part2_gnum = ptp_loc.reverse_wait(req_id)
      
      if (part2_gnum[0].size==0):
        new_point_list = np.empty(0,dtype=np.int32)
      else :
        sort_idx       = np.argsort(part2_gnum[0])                 # Sort order of point_list ()
        order          = np.searchsorted(part2_gnum[0],parent_elt_loc,sorter=sort_idx)

        parent_elt_idx = np.take(sort_idx, order, mode="clip")

        stride         = part2_gnum[0][parent_elt_idx] == parent_elt_loc
        new_point_list = np.where(stride)[0]

      new_point_list = new_point_list.reshape((1,-1), order='F') # Ordering in shape (1,N) because of CGNS standard
      new_pl_node    = PT.new_PointList(name='PointList', value=new_point_list+starting_elt(part_zone_ep,gridLocation), parent=FS_ep)

      # Boucle sur les partitoins de l'extracttion pout get PL
      # faire l'import
      gnum = PT.get_node_from_path(part_zone_ep,f':CGNS#GlobalNumbering/{loc_correspondance[gridLocation]}')[1]
      list_de_tab = maia.algo.part.compute_gnum_from_parent_gnum(gnum[new_point_list], comm)
      new_gnum = dict()
      new_gnum["Index"] = list_de_tab[0]
      
      # Boucle sur les partitoins de l'extracttion pour placer PL        
      node_cgnspart = maia.pytree.maia.newGlobalNumbering(new_gnum, parent=FS_ep)

    # print('[MAIA] ExtractPart :: partial_field = ', partial_field)
    # --- Field exchange ----------------------------------------------------------------
    for fld_name in flds_in_container_names:
      fld_path = f"{container_name}/{fld_name}"
      
      # Reordering if ZSR container
      if partial_field: 
        
        fld_data = list()
        for i_part,part_zone in enumerate(part_zones):
          fld_part = PT.get_node_from_path(part_zone,fld_path)[1]
          if fld_part != np.empty(0,dtype=fld_part.dtype):
            fld_part = fld_part[all_ordering[i_part]][all_stride_bool[i_part]]
          fld_data.append(fld_part)

        req_id = ptp_loc.reverse_iexch( PDM._PDM_MPI_COMM_KIND_P2P,
                                        PDM._PDM_PART_TO_PART_DATA_DEF_ORDER_GNUM1_COME_FROM,
                                        fld_data,
                                        part2_stride=all_stride_int)
      else :
        fld_data = [PT.get_node_from_path(part_zone,fld_path)[1]
                    for part_zone in part_zones]
        req_id = ptp_loc.reverse_iexch( PDM._PDM_MPI_COMM_KIND_P2P,
                                        PDM._PDM_PART_TO_PART_DATA_DEF_ORDER_PART2,
                                        fld_data,
                                        part2_stride=1)

      part1_strid, part1_data = ptp_loc.reverse_wait(req_id)

      # Interpolation and placement
      i_part = 0
      PT.new_DataArray(fld_name, part1_data[i_part], parent=FS_ep)
# ---------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------

def _exchange_field(part_tree, part_tree_ep, ptp,containers_name, comm) :
  """
  Exchange field between part_tree and part_tree_ep
  for exchange vol field 
  """

  # Get zones by domains
  part_tree_per_dom = dist_from_part.get_parts_per_blocks(part_tree, comm).values()

  # Check : monodomain
  assert(len(part_tree_per_dom)==1)
  assert(len(part_tree_per_dom)==len(ptp))

  # Get zone from extractpart
  part_zone_ep = PT.get_all_Zone_t(part_tree_ep)
  assert(len(part_zone_ep)<=1)
  part_zone_ep = part_zone_ep[0]

  # Loop over domains
  for i_domain, part_zones in enumerate(part_tree_per_dom):
    exchange_field_one_domain(part_zones, part_zone_ep, ptp[i_domain], containers_name, comm)

# ---------------------------------------------------------------------------------------
# =======================================================================================





# =======================================================================================
# ---------------------------------------------------------------------------------------
def extract_part_one_domain(part_zones, point_list, dim, comm,
                            equilibrate=1,
                            graph_part_tool="hilbert",
                            put_pe=False):
  """
  TODO : AJOUTER LE CHOIX PARTIONNEMENT
  """
  n_part_in = len(part_zones)
  
  if equilibrate==0 : n_part_out = n_part_in
  else              : n_part_out = 1
  
  # print(n_par)
  pdm_ep = PDM.ExtractPart(dim, # face/cells
                           n_part_in,
                           n_part_out,
                           equilibrate,
                           eval(f"PDM._PDM_SPLIT_DUAL_WITH_{graph_part_tool.upper()}"),
                           True,
                           comm)
  # Loop over domain zone : preparing extract part
  adjusted_point_list = list()
  for i_part, part_zone in enumerate(part_zones):
    # Get NGon + NFac
    cx, cy, cz = PT.Zone.coordinates(part_zone)
    vtx_coords = np_utils.interweave_arrays([cx,cy,cz])
    
    ngon  = PT.Zone.NGonNode(part_zone)
    nface = PT.Zone.NFaceNode(part_zone)

    cell_face_idx = PT.get_child_from_name(nface, "ElementStartOffset" )[1]
    cell_face     = PT.get_child_from_name(nface, "ElementConnectivity")[1]
    face_vtx_idx  = PT.get_child_from_name(ngon,  "ElementStartOffset" )[1]
    face_vtx      = PT.get_child_from_name(ngon,  "ElementConnectivity")[1]

    vtx_ln_to_gn, face_ln_to_gn, cell_ln_to_gn = TEU.get_entities_numbering(part_zone)

    # n_cell = cell_ln_to_gn.shape[0]
    n_cell = cell_ln_to_gn.shape[0]
    n_face = face_ln_to_gn.shape[0]
    n_edge = 0
    n_vtx  = vtx_ln_to_gn .shape[0]

    pdm_ep.part_set(i_part,
                    n_cell,
                    n_face,
                    n_edge,
                    n_vtx,
                    cell_face_idx,
                    cell_face    ,
                    None,
                    None,
                    None,
                    face_vtx_idx ,
                    face_vtx     ,
                    cell_ln_to_gn,
                    face_ln_to_gn,
                    None,
                    vtx_ln_to_gn ,
                    vtx_coords)

    pdm_ep.selected_lnum_set(i_part,point_list[i_part]-1)

  pdm_ep.compute()


  # > Reconstruction du maillage de l'extract part --------------------------------------
  n_extract_cell = pdm_ep.n_entity_get(0, PDM._PDM_MESH_ENTITY_CELL  ) # ; print(f'[{comm.Get_rank()}][MAIA] n_extract_cell = {n_extract_cell}')
  n_extract_face = pdm_ep.n_entity_get(0, PDM._PDM_MESH_ENTITY_FACE  ) # ; print(f'[{comm.Get_rank()}][MAIA] n_extract_face = {n_extract_face}')
  n_extract_edge = pdm_ep.n_entity_get(0, PDM._PDM_MESH_ENTITY_EDGE  ) # ; print(f'[{comm.Get_rank()}][MAIA] n_extract_edge = {n_extract_edge}')
  n_extract_vtx  = pdm_ep.n_entity_get(0, PDM._PDM_MESH_ENTITY_VERTEX) # ; print(f'[{comm.Get_rank()}][MAIA] n_extract_vtx  = {n_extract_vtx }')
  

  extract_vtx_coords = pdm_ep.vtx_coord_get(0)
  
  size_by_dim = {0: [[n_extract_vtx, 0             , 0]], # not yet implemented
                 1:   None                              , # not yet implemented
                 2: [[n_extract_vtx, n_extract_face, 0]],
                 3: [[n_extract_vtx, n_extract_cell, 0]] }


  # --- ExtractPart zone construction ---------------------------------------------------
  extract_part_zone = PT.new_Zone(PT.maia.conv.add_part_suffix('Zone', comm.Get_rank(), 0),
                                  size=size_by_dim[dim],
                                  type='Unstructured')

  # > Grid coordinates
  cx, cy, cz = layouts.interlaced_to_tuple_coords(extract_vtx_coords)
  extract_grid_coord = PT.new_GridCoordinates(parent=extract_part_zone)
  PT.new_DataArray('CoordinateX', cx, parent=extract_grid_coord)
  PT.new_DataArray('CoordinateY', cy, parent=extract_grid_coord)
  PT.new_DataArray('CoordinateZ', cz, parent=extract_grid_coord)

  # > NGON
  if (dim>=2) :
    ep_face_vtx_idx, ep_face_vtx  = pdm_ep.connectivity_get(0, PDM._PDM_CONNECTIVITY_TYPE_FACE_VTX)
    ngon_n = PT.new_NGonElements( 'NGonElements',
                                  erange  = [1, n_extract_face],
                                  ec      = ep_face_vtx,
                                  eso     = ep_face_vtx_idx,
                                  parent  = extract_part_zone)
  # > NFACES
  if (dim==3) :
    ep_cell_face_idx, ep_cell_face = pdm_ep.connectivity_get(0, PDM._PDM_CONNECTIVITY_TYPE_CELL_FACE)
    nface_n = PT.new_NFaceElements('NFaceElements',
                                    erange  = [n_extract_face+1, n_extract_face+n_extract_cell],
                                    ec      = ep_cell_face,
                                    eso     = ep_cell_face_idx,
                                    parent  = extract_part_zone)

    # Compute ParentElement nodes is requested
    if (put_pe):
      maia.algo.nface_to_pe(extract_part_zone, comm)

    
  # > LN_TO_GN nodes
  ep_vtx_ln_to_gn  = None
  ep_face_ln_to_gn = None
  ep_cell_ln_to_gn = None

  ep_vtx_ln_to_gn  = pdm_ep.ln_to_gn_get(0,PDM._PDM_MESH_ENTITY_VERTEX)

  if (dim>=2) : # NGON
    ep_face_ln_to_gn = pdm_ep.ln_to_gn_get(0,PDM._PDM_MESH_ENTITY_FACE)
    PT.maia.newGlobalNumbering({'Element' : ep_face_ln_to_gn}, parent=ngon_n)
    
  if (dim==3) : # NFACE
    ep_cell_ln_to_gn = pdm_ep.ln_to_gn_get(0,PDM._PDM_MESH_ENTITY_CELL)
    PT.maia.newGlobalNumbering({'Element' : ep_cell_ln_to_gn}, parent=nface_n)

  ln_to_gn_by_dim = { 0: {'Cell': ep_vtx_ln_to_gn },
                      1:   None,                                                  # not yet implemented
                      2: {'Vertex': ep_vtx_ln_to_gn , 'Cell': ep_face_ln_to_gn },
                      3: {'Vertex': ep_vtx_ln_to_gn , 'Cell': ep_cell_ln_to_gn } }
  PT.maia.newGlobalNumbering(ln_to_gn_by_dim[dim], parent=extract_part_zone)

  # - Get PTP by vertex and cell
  ptp = dict()
  if equilibrate==1:
    ptp['Vertex']       = pdm_ep.part_to_part_get(PDM._PDM_MESH_ENTITY_VERTEX)
    if (dim>=2) : # NGON
      ptp['FaceCenter'] = pdm_ep.part_to_part_get(PDM._PDM_MESH_ENTITY_FACE)
    if (dim==3) : # NFACE
      ptp['CellCenter'] = pdm_ep.part_to_part_get(PDM._PDM_MESH_ENTITY_CELL)
    
  # - Get parent elt
  parent_elt = dict()
  parent_elt['Vertex']       = pdm_ep.parent_ln_to_gn_get(0,PDM._PDM_MESH_ENTITY_VERTEX)
  if (dim>=2) : # NGON
    parent_elt['FaceCenter'] = pdm_ep.parent_ln_to_gn_get(0,PDM._PDM_MESH_ENTITY_FACE)
  if (dim==3) : # NFACE
    parent_elt['CellCenter'] = pdm_ep.parent_ln_to_gn_get(0,PDM._PDM_MESH_ENTITY_CELL)
  
  exch_tool_box = dict()
  exch_tool_box['part_to_part'] = ptp
  exch_tool_box['parent_elt'  ] = parent_elt


  return extract_part_zone, exch_tool_box
# ---------------------------------------------------------------------------------------
# =======================================================================================



# =======================================================================================
# --- EXTRACT PART FROM ZSR -------------------------------------------------------------

# ---------------------------------------------------------------------------------------
def extract_part_from_zsr(part_tree, zsr_name, comm,
                          # equilibrate=1,
                          # graph_part_tool='hilbert',
                          containers_name=None):
  """Extract the submesh defined by the provided ZoneSubRegion from the input volumic
  partitioned tree.

  Dimension of the ouput mesh is set up accordingly to the GridLocation of the ZoneSubRegion.
  Submesh is returned as an independant partitioned CGNSTree and includes the relevant connectivities.

  In addition, containers specified in ``containers_name`` list are transfered to the extracted tree.

  Important:
    - Input tree must be unstructured and have a ngon connectivity.
    - Partitions must come from a single initial domain on input tree.
  
  See also:
    :func:`create_extractor_from_zsr` takes the same parameters, excepted ``containers_name``,
    and returns an Extractor object which can be used to exchange containers more than once through its
    ``Extractor.exchange_fields(container_name)`` method.

  Args:
    part_tree       (CGNSTree)    : Partitioned tree from which extraction is computed. Only U-NGon
      connectivities are managed.
    zsr_name        (str)         : Name of the ZoneSubRegion_t node
    comm            (MPIComm)     : MPI communicator
    containers_name (list of str) : List of the names of the fields containers to transfer
      on the output extracted tree.
  Returns:
    extracted_tree (CGNSTree)  : Extracted submesh (partitioned)

  Example:
    .. literalinclude:: snippets/test_algo.py
      :start-after: #extract_from_zsr@start
      :end-before:  #extract_from_zsr@end
      :dedent: 2
  """


  extractor = create_extractor_from_zsr(part_tree, zsr_name, comm)

  if containers_name is not None:
    extractor.exchange_fields(containers_name, comm)

  return extractor.get_extract_part_tree()

# ---------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------
def create_extractor_from_zsr(part_tree, zsr_path, comm
                              # equilibrate=1,
                              # graph_part_tool='hilbert'
                              ):
  """Same as extract_part_from_zsr, but return the extractor object."""
  # Get zones by domains
  part_tree_per_dom = dist_from_part.get_parts_per_blocks(part_tree, comm)

  # Get point_list for each partitioned zone and group it by domain
  point_list = list()
  location = ''
  for domain, part_zones in part_tree_per_dom.items():
    point_list_domain = list()
    for part_zone in part_zones:
      zsr_node     = PT.get_node_from_path(part_zone, zsr_path)
      if zsr_node is not None:
        #Follow BC or GC link
        related_node = PT.getSubregionExtent(zsr_node, part_zone)
        zsr_node     = PT.get_node_from_path(part_zone, related_node)
        point_list_domain.append(PT.get_child_from_name(zsr_node, "PointList")[1][0])
        location = PT.Subset.GridLocation(zsr_node)
      else: # ZSR does not exists on this partition
        point_list_domain.append(np.empty(0, np.int32))
    point_list.append(point_list_domain)
  
  # Get location if proc has no zsr
  location = comm.allreduce(location, op=MPI.MAX)

  return Extractor(part_tree, point_list, location, comm
                   # equilibrate=equilibrate,
                   # graph_part_tool=graph_part_tool
                   )
# ---------------------------------------------------------------------------------------

# --- END EXTRACT PART FROM ZSR ---------------------------------------------------------
# =======================================================================================







# =======================================================================================
# ---------------------------------------------------------------------------------------
# # ---------------------------------------------------------------------------------------
# def extract_part_from_bnd():
#   return extract_part_tree

# def create_extractor_from_bnd():
#   # get point list
#   return Extractor
# # ---------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------
# =======================================================================================

