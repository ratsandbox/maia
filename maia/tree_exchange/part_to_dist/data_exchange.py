import numpy              as np
import Converter.Internal as I
import Pypdm.Pypdm        as PDM

import maia.sids.sids     as SIDS
from maia.utils.parallel import utils    as par_utils
from maia.tree_exchange  import utils    as te_utils
from maia.utils          import py_utils

def discover_partitioned_fields(dist_zone, part_zones, comm):
  """
  Append in dist zone the skeleton path of field that have been created
  on specific partitioned zones
  """
  # > Local collection of fields not existing in dist zone
  new_sols = {}
  for part_zone in part_zones:
    for p_sol in I.getNodesFromType1(part_zones, "FlowSolution_t") + \
                 I.getNodesFromType1(part_zones, "DiscreteData_t"):
      if I.getNodeFromPath(dist_zone, I.getName(p_sol)) is None:
        assert I.getNodeFromType1(p_sol, 'IndexArray_t') is None
        fields = [I.getName(field) for field in I.getNodesFromType1(p_sol, 'DataArray_t')]
        new_sols[I.getName(p_sol)] = (I.getType(p_sol), SIDS.GridLocation(p_sol), fields)

  # > Gathering and update of dist zone
  discovered_sols = {}
  for new_sol_rank in comm.allgather(new_sols):
    discovered_sols.update(new_sol_rank)
  for discovered_sol, (type, loc, fields) in discovered_sols.items():
    d_sol = I.newFlowSolution(discovered_sol, loc, parent=dist_zone)
    I.setType(d_sol, type) #Trick to be generic between DiscreteData/FlowSol
    for field in fields:
      I.newDataArray(field, parent=d_sol)

def part_to_dist(partial_distri, part_data, ln_to_gn_list, comm):
  """
  Helper function calling PDM.PartToBlock
  """
  pdm_distrib = par_utils.partial_to_full_distribution(partial_distri, comm)

  PTB = PDM.PartToBlock(comm, ln_to_gn_list, pWeight=None, partN=len(ln_to_gn_list),
                        t_distrib=0, t_post=1, t_stride=0, userDistribution=pdm_distrib)

  dist_data = dict()
  PTB.PartToBlock_Exchange(dist_data, part_data)
  return dist_data

def part_sol_to_dist_sol(dist_zone, part_zones, comm):
  """
  Transfert all the data included in FlowSolution_t nodes and DiscreteData_t nodes from partitioned
  zones to the distributed zone. Data created on (one or more) partitions and not present in dist_tree
  is also reported to the distributed zone.
  """

  discover_partitioned_fields(dist_zone, part_zones, comm)

  for d_flow_sol in I.getNodesFromType1(dist_zone, "FlowSolution_t") + \
                    I.getNodesFromType1(dist_zone, "DiscreteData_t"):
    location = SIDS.GridLocation(d_flow_sol)
    has_pl   = I.getNodeFromName1(d_flow_sol, 'PointList') is not None

    if has_pl:
      distribution = te_utils.get_cgns_distribution(d_flow_sol, ':CGNS#Distribution/Index')
      lntogn_path  = I.getName(d_flow_sol) + '/:CGNS#GlobalNumbering/Index'
      lntogn_list  = te_utils.collect_cgns_g_numbering(part_zones, lntogn_path)
    else:
      assert location in ['Vertex', 'CellCenter']
      if location == 'Vertex':
        distribution = te_utils.get_cgns_distribution(dist_zone, ':CGNS#Distribution/Vertex')
        lntogn_list  = te_utils.collect_cgns_g_numbering(part_zones, ':CGNS#GlobalNumbering/Vertex')
      elif location == 'CellCenter':
        distribution = te_utils.get_cgns_distribution(dist_zone, ':CGNS#Distribution/Cell')
        lntogn_list  = te_utils.collect_cgns_g_numbering(part_zones, ':CGNS#GlobalNumbering/Cell')

    #Discover data
    part_data = dict()
    for field in I.getNodesFromType1(d_flow_sol, 'DataArray_t'):
      part_data[I.getName(field)] = list()

    for part_zone in part_zones:
      p_flow_sol = I.getNodesFromName1(part_zone, I.getName(d_flow_sol))
      for field in I.getNodesFromType1(p_flow_sol, 'DataArray_t'):
        flat_data = field[1].ravel(order='A') #Reshape structured arrays for PDM exchange
        part_data[I.getName(field)].append(flat_data)

    # Exchange
    dist_data = part_to_dist(distribution, part_data, lntogn_list, comm)
    for field, array in dist_data.items():
      dist_field = I.getNodeFromName1(d_flow_sol, field)
      I.setValue(dist_field, array)

def part_subregion_to_dist_subregion(dist_zone, part_zones, comm):
  """
  Transfert all the data included in ZoneSubRegion_t nodes from the partitioned
  zones to the distributed zone.
  Zone subregions must exist on distzone
  """
  for d_zsr in I.getNodesFromType1(dist_zone, "ZoneSubRegion_t"):
    # Search matching region
    matching_region_path = SIDS.get_subregion_extent(d_zsr, dist_zone)
    matching_region = I.getNodeFromPath(dist_zone, matching_region_path)
    assert matching_region is not None

    #Get distribution and lngn
    distribution = te_utils.get_cgns_distribution(matching_region, ':CGNS#Distribution/Index')
    lngn_list    = te_utils.collect_cgns_g_numbering(part_zones, matching_region_path + \
        '/:CGNS#GlobalNumbering/Index')

    #Discover data
    part_data = dict()
    for field in I.getNodesFromType1(d_zsr, 'DataArray_t'):
      part_data[I.getName(field)] = list()

    for part_zone in part_zones:
      p_zsr = I.getNodeFromPath(part_zone, I.getName(d_zsr))
      if p_zsr is not None:
        for field in I.getNodesFromType1(p_zsr, 'DataArray_t'):
          flat_data = field[1].ravel(order='A') #Reshape structured arrays for PDM exchange
          part_data[I.getName(field)].append(flat_data)

    # Exchange
    dist_data = part_to_dist(distribution, part_data, lngn_list, comm)
    for field, array in dist_data.items():
      dist_field = I.getNodeFromName1(d_zsr, field)
      I.setValue(dist_field, array)

def part_dataset_to_dist_dataset(dist_zone, part_zones, comm):
  """
  Transfert all the data included in BCDataSet_t/BCData_t nodes from partitioned
  zones to the distributed zone.
  Such nodes must exist on the dist zone.
  """
  for d_zbc in I.getNodesFromType1(dist_zone, "ZoneBC_t"):
    for d_bc in I.getNodesFromType1(d_zbc, "BC_t"):
      bc_path   = I.getName(d_zbc) + '/' + I.getName(d_bc)
      #Get BC distribution and lngn
      distribution_bc = te_utils.get_cgns_distribution(d_bc, ':CGNS#Distribution/Index')
      lngn_list_bc    = te_utils.collect_cgns_g_numbering(part_zones, bc_path + '/:CGNS#GlobalNumbering/Index')
      for d_dataset in I.getNodesFromType1(d_bc, 'BCDataSet_t'):
        #If dataset has its own PointList, we must override bc distribution and lngn
        if I.getNodeFromPath(d_dataset, ':CGNS#Distribution/Index') is not None:
          distribution = te_utils.get_cgns_distribution(d_dataset, ':CGNS#Distribution/Index')
          ds_path      = bc_path + '/' + I.getName(d_dataset)
          lngn_list    = te_utils.collect_cgns_g_numbering(part_zones, ds_path + '/:CGNS#GlobalNumbering/Index')
        else: #Fallback to bc distribution
          distribution = distribution_bc
          lngn_list    = lngn_list_bc


        #Discover data
        part_data = dict()
        for bc_data, field in py_utils.getNodesWithParentsFromTypePath(d_dataset, 'BCData_t/DataArray_t'):
          part_data[I.getName(bc_data) + '/' + I.getName(field)] = list()

        for part_zone in part_zones:
          p_dataset = I.getNodeFromPath(part_zone, bc_path + '/' + I.getName(d_dataset))
          if p_dataset is not None:
            for bc_data, field in py_utils.getNodesWithParentsFromTypePath(p_dataset, 'BCData_t/DataArray_t'):
              flat_data = field[1].ravel(order='A') #Reshape structured arrays for PDM exchange
              part_data[I.getName(bc_data) + '/' + I.getName(field)].append(flat_data)

        #Exchange
        dist_data = part_to_dist(distribution, part_data, lngn_list, comm)
        for field, array in dist_data.items():
          dist_field = I.getNodeFromPath(d_dataset, field)
          I.setValue(dist_field, array)
