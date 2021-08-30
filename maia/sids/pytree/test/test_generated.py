import pytest
import numpy as np
import fnmatch
import os

import Converter.Internal as I
from maia.sids.cgns_keywords import Label as CGL
from maia.sids import pytree as PT

from maia.utils        import parse_yaml_cgns

dir_path = os.path.dirname(os.path.realpath(__file__))

def test_getNodeFromName():
  with open(os.path.join(dir_path, "minimal_bc_tree.yaml"), 'r') as yt:
    tree = parse_yaml_cgns.to_cgns_tree(yt)

  # Camel case
  # ==========
  assert PT.getNodeFromName(tree, "ZoneI") == I.getNodeFromName(tree, "ZoneI")
  assert I.getNodeFromName(tree, "ZoneB") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromName(tree, "ZoneB")

  base = I.getBases(tree)[0]
  assert PT.getNodeFromName1(base, "ZoneI") == I.getNodeFromName1(base, "ZoneI")
  assert I.getNodeFromName1(base, "ZoneB") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromName1(base, "ZoneB")

  assert PT.getNodeFromName2(tree, "ZoneI") == I.getNodeFromName2(tree, "ZoneI")
  assert I.getNodeFromName2(tree, "ZoneB") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromName2(tree, "ZoneB")

  assert PT.getNodeFromName3(tree, "ZBCA") == I.getNodeFromName3(tree, "ZBCA")
  assert I.getNodeFromName3(tree, "ZZZZZ") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromName3(tree, "ZZZZZ")

  # Snake case
  # ==========
  node = PT.get_node_from_name(tree, "ZoneI")
  assert I.getName(node) == "ZoneI"
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name(tree, "ZoneB")

  base = I.getBases(tree)[0]
  node = PT.get_node_from_name1(base, "ZoneI")
  assert I.getName(node) == "ZoneI"
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name1(base, "ZoneB")

  node = PT.get_node_from_name2(tree, "ZoneI")
  assert I.getName(node) == "ZoneI"
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name2(tree, "ZoneB")

  node = PT.get_node_from_name3(tree, "ZBCA")
  assert I.getName(node) == "ZBCA"
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name3(tree, "ZZZZZ")

def test_getNodeFromLabel():
  with open(os.path.join(dir_path, "minimal_bc_tree.yaml"), 'r') as yt:
    tree = parse_yaml_cgns.to_cgns_tree(yt)

  # Camel case
  # ==========
  assert PT.getNodeFromLabel(tree, "Zone_t") == I.getNodeFromType(tree, "Zone_t")
  assert I.getNodeFromType(tree, "Family_t") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromLabel(tree, "Family_t")

  base = I.getBases(tree)[0]
  assert PT.getNodeFromLabel1(base, "Zone_t") == I.getNodeFromType1(base, "Zone_t")
  assert I.getNodeFromType1(base, "Family_t") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromLabel1(base, "Family_t")

  assert PT.getNodeFromLabel2(tree, "Zone_t") == I.getNodeFromType2(tree, "Zone_t")
  assert I.getNodeFromType2(tree, "Family_t") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromLabel2(tree, "Family_t")

  assert PT.getNodeFromLabel3(tree, "ZoneBC_t") == I.getNodeFromType3(tree, "ZoneBC_t")
  assert I.getNodeFromType3(tree, "ZoneGridConnectivity_t") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromLabel3(tree, "ZoneGridConnectivity_t")

  # Snake case
  # ==========
  node = PT.get_node_from_label(tree, "Zone_t")
  assert I.getType(node) == "Zone_t"
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_label(tree, "Family_t")

  base = I.getBases(tree)[0]
  node = PT.get_node_from_label1(base, "Zone_t")
  assert I.getType(node) == "Zone_t"
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_label1(base, "Family_t")

  node = PT.get_node_from_label2(tree, "Zone_t")
  assert I.getType(node) == "Zone_t"
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_label2(tree, "Family_t")

  node = PT.get_node_from_label3(tree, "ZoneBC_t")
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_label3(tree, "ZoneGridConnectivity_t")

def test_getNodeFromNameAndLabel():
  with open(os.path.join(dir_path, "minimal_bc_tree.yaml"), 'r') as yt:
    tree = parse_yaml_cgns.to_cgns_tree(yt)

  # Camel case
  # ==========
  assert I.getNodeFromNameAndType(tree, "ZoneI", "Zone_t") == PT.requestNodeFromNameAndLabel(tree, "ZoneI", "Zone_t")
  assert PT.getNodeFromNameAndLabel(tree, "ZoneI", "Zone_t") == I.getNodeFromNameAndType(tree, "ZoneI", "Zone_t")
  assert I.getNodeFromNameAndType(tree, "ZoneB", "Zone_t")   == None
  assert I.getNodeFromNameAndType(tree, "ZoneI", "Family_t") == None
  assert PT.requestNodeFromNameAndLabel(tree, "ZoneB", "Zone_t")   == None
  assert PT.requestNodeFromNameAndLabel(tree, "ZoneI", "Family_t") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromNameAndLabel(tree, "ZoneB", "Zone_t")
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromNameAndLabel(tree, "ZoneI", "Family_t")

  base = I.getBases(tree)[0]
  assert I.getNodeFromNameAndType(base, "ZoneI", "Zone_t") == PT.requestNodeFromNameAndLabel1(base, "ZoneI", "Zone_t")
  assert PT.getNodeFromNameAndLabel1(base, "ZoneI", "Zone_t") == PT.requestNodeFromNameAndLabel1(base, "ZoneI", "Zone_t")
  assert I.getNodeFromNameAndType(base, "ZoneB", "Zone_t")   == None
  assert I.getNodeFromNameAndType(base, "ZoneI", "Family_t") == None
  assert PT.requestNodeFromNameAndLabel1(base, "ZoneB", "Zone_t")   == None
  assert PT.requestNodeFromNameAndLabel1(base, "ZoneI", "Family_t") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromNameAndLabel1(base, "ZoneB", "Zone_t")
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromNameAndLabel1(base, "ZoneI", "Family_t")

  assert I.getNodeFromNameAndType(tree, "ZoneI", "Zone_t") == PT.requestNodeFromNameAndLabel2(tree, "ZoneI", "Zone_t")
  assert PT.getNodeFromNameAndLabel2(tree, "ZoneI", "Zone_t") == PT.requestNodeFromNameAndLabel2(tree, "ZoneI", "Zone_t")
  assert I.getNodeFromNameAndType(tree, "ZoneB", "Zone_t")   == None
  assert I.getNodeFromNameAndType(tree, "ZoneI", "Family_t") == None
  assert PT.requestNodeFromNameAndLabel2(tree, "ZoneB", "Zone_t")   == None
  assert PT.requestNodeFromNameAndLabel2(tree, "ZoneI", "Family_t") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromNameAndLabel2(tree, "ZoneB", "Zone_t")
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromNameAndLabel2(tree, "ZoneI", "Family_t")

  assert I.getNodeFromNameAndType(tree, "ZBCA", "ZoneBC_t") == PT.requestNodeFromNameAndLabel3(tree, "ZBCA", "ZoneBC_t")
  assert PT.getNodeFromNameAndLabel3(tree, "ZBCA", "ZoneBC_t") == PT.requestNodeFromNameAndLabel3(tree, "ZBCA", "ZoneBC_t")
  assert I.getNodeFromNameAndType(tree, "ZZZZZ", "ZoneBC_t")              == None
  assert I.getNodeFromNameAndType(tree, "ZBCA", "ZoneGridConnectivity_t") == None
  assert PT.requestNodeFromNameAndLabel3(tree, "ZZZZZ", "ZoneBC_t")              == None
  assert PT.requestNodeFromNameAndLabel3(tree, "ZBCA", "ZoneGridConnectivity_t") == None
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromNameAndLabel3(tree, "ZZZZZ", "ZoneBC_t")
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.getNodeFromNameAndLabel3(tree, "ZBCA", "ZoneGridConnectivity_t")

  # Snake case
  # ==========
  node = PT.request_node_from_name_and_label(tree, "ZoneI", "Zone_t")
  assert I.getName(node) == "ZoneI" and I.getType(node) == "Zone_t"
  assert PT.request_node_from_name_and_label(tree, "ZoneB", "Zone_t")   == None
  assert PT.request_node_from_name_and_label(tree, "ZoneI", "Family_t") == None
  node = PT.get_node_from_name_and_label(tree, "ZoneI", "Zone_t")
  assert I.getName(node) == "ZoneI" and I.getType(node) == "Zone_t"
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name_and_label(tree, "ZoneB", "Zone_t")
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name_and_label(tree, "ZoneI", "Family_t")

  base = PT.getNodeFromLabel(tree, 'CGNSBase_t') # get the first base
  node = PT.request_node_from_name_and_label1(base, "ZoneI", "Zone_t")
  assert I.getName(node) == "ZoneI" and I.getType(node) == "Zone_t"
  assert PT.request_node_from_name_and_label1(base, "ZoneB", "Zone_t")   == None
  assert PT.request_node_from_name_and_label1(base, "ZoneI", "Family_t") == None
  node = PT.get_node_from_name_and_label1(base, "ZoneI", "Zone_t")
  assert I.getName(node) == "ZoneI" and I.getType(node) == "Zone_t"
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name_and_label1(base, "ZoneB", "Zone_t")
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name_and_label1(base, "ZoneI", "Family_t")

  node = PT.request_node_from_name_and_label2(tree, "ZoneI", "Zone_t")
  assert I.getName(node) == "ZoneI" and I.getType(node) == "Zone_t"
  assert PT.request_node_from_name_and_label2(tree, "ZoneB", "Zone_t")   == None
  assert PT.request_node_from_name_and_label2(tree, "ZoneI", "Family_t") == None
  node = PT.get_node_from_name_and_label2(tree, "ZoneI", "Zone_t")
  assert I.getName(node) == "ZoneI" and I.getType(node) == "Zone_t"
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name_and_label2(tree, "ZoneB", "Zone_t")
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name_and_label2(tree, "ZoneI", "Family_t")

  node = PT.request_node_from_name_and_label3(tree, "ZBCA", "ZoneBC_t")
  assert I.getName(node) == "ZBCA" and I.getType(node) == "ZoneBC_t"
  assert PT.request_node_from_name_and_label3(tree, "ZZZZZ", "ZoneBC_t")              == None
  assert PT.request_node_from_name_and_label3(tree, "ZBCA", "ZoneGridConnectivity_t") == None
  node = PT.get_node_from_name_and_label3(tree, "ZBCA", "ZoneBC_t")
  assert I.getName(node) == "ZBCA" and I.getType(node) == "ZoneBC_t"
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name_and_label3(tree, "ZZZZZ", "ZoneBC_t")
  with pytest.raises(PT.CGNSNodeFromPredicateNotFoundError):
    PT.get_node_from_name_and_label3(tree, "ZBCA", "ZoneGridConnectivity_t")

def test_getNodeFromPredicate():
  is_base    = lambda n: I.getName(n) == 'Base'    and I.getType(n) == 'CGNSBase_t'
  is_zonei   = lambda n: I.getName(n) == 'ZoneI'   and I.getType(n) == 'Zone_t'
  is_nface   = lambda n: I.getName(n) == 'NFace'   and I.getType(n) == 'Elements_t'
  is_ngon    = lambda n: I.getName(n) == 'Ngon'    and I.getType(n) == 'Elements_t'
  is_zbca    = lambda n: I.getName(n) == 'ZBCA'    and I.getType(n) == 'ZoneBC_t'
  is_bc1     = lambda n: I.getName(n) == 'bc1'     and I.getType(n) == 'BC_t'
  is_index_i = lambda n: I.getName(n) == 'Index_i' and I.getType(n) == 'IndexArray_t'

  with open(os.path.join(dir_path, "minimal_bc_tree.yaml"), 'r') as yt:
    tree = parse_yaml_cgns.to_cgns_tree(yt)

  # requestNodeFrom...
  # ******************

  # requestNodeFromPredicate
  # ========================
  # Camel case
  # ----------
  assert is_base  ( PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "Base")                )
  assert is_zonei ( PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "ZoneI", search="bfs") )
  assert is_zonei ( PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "ZoneI", search="dfs") )
  assert is_base  ( PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "Base")                )
  assert is_zonei ( PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "ZoneI", search="bfs") )
  assert is_zonei ( PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "ZoneI", search="dfs") )

  # Snake case
  # ----------
  assert PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "ZoneI", search="dfs", depth=1) is None
  assert is_zonei(PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "ZoneI", search="dfs", depth=2))
  assert is_zonei(PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "ZoneI", search="dfs", depth=3))

  assert is_base    ( PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "Base", search="dfs", depth=1)    )
  assert is_zonei   ( PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "ZoneI", search="dfs", depth=2)   )
  assert is_ngon    ( PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "Ngon", search="dfs", depth=3)    )
  assert is_bc1     ( PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "bc1", search="dfs", depth=4)     )
  assert is_index_i ( PT.requestNodeFromPredicate(tree, lambda n: I.getName(n) == "Index_i", search="dfs", depth=5) )

  # requestNodeFrom{Name, Label, ...}
  # =================================
  # Camel case
  # ----------
  assert is_nface( PT.requestNodeFromName(tree, "NFace")                                                         )
  assert is_nface( PT.requestNodeFromValue(tree, np.array([23,0], order='F'))                                    )
  assert is_ngon(  PT.requestNodeFromLabel(tree, "Elements_t")                                                   )
  assert is_nface( PT.requestNodeFromNameAndValue(tree, "NFace", np.array([23,0], order='F'))                    )
  assert is_nface( PT.requestNodeFromNameAndLabel(tree, "NFace", "Elements_t")                                   )
  assert is_nface( PT.requestNodeFromValueAndLabel(tree, np.array([23,0], order='F'), "Elements_t")              )
  assert is_nface( PT.requestNodeFromNameValueAndLabel(tree, "NFace", np.array([23,0], order='F'), "Elements_t") )
  assert PT.requestNodeFromName(tree, "TOTO")                                                               is None
  assert PT.requestNodeFromValue(tree, np.array([1230,0], order='F'))                                       is None
  assert PT.requestNodeFromLabel(tree, "ZoneSubRegion_t")                                                   is None
  assert PT.requestNodeFromNameAndValue(tree, "TOTO", np.array([23,0], order='F'))                          is None
  assert PT.requestNodeFromNameAndValue(tree, "NFace", np.array([1230,0], order='F'))                       is None
  assert PT.requestNodeFromNameAndLabel(tree, "TOTO", "Elements_t")                                         is None
  assert PT.requestNodeFromNameAndLabel(tree, "NFace", "ZoneSubRegion_t")                                   is None
  assert PT.requestNodeFromValueAndLabel(tree, np.array([1230,0], order='F'), "Elements_t")                 is None
  assert PT.requestNodeFromValueAndLabel(tree, np.array([23,0], order='F'), "ZoneSubRegion_t")              is None
  assert PT.requestNodeFromNameValueAndLabel(tree, "TOTO", np.array([23,0], order='F'), "Elements_t")       is None
  assert PT.requestNodeFromNameValueAndLabel(tree, "NFace", np.array([1230,0], order='F'), "Elements_t")    is None
  assert PT.requestNodeFromNameValueAndLabel(tree, "NFace", np.array([23,0], order='F'), "ZoneSubRegion_t") is None

  # Snake case
  # ----------
  assert PT.request_node_from_name(tree, "TOTO")                                                                  is None
  assert PT.request_node_from_value(tree, np.array([1230,0], order='F'))                                          is None
  assert PT.request_node_from_label(tree, "ZoneSubRegion_t")                                                      is None
  assert PT.request_node_from_name_and_value(tree, "TOTO", np.array([23,0], order='F'))                           is None
  assert PT.request_node_from_name_and_value(tree, "NFace", np.array([1230,0], order='F'))                        is None
  assert PT.request_node_from_name_and_label(tree, "TOTO", "Elements_t")                                          is None
  assert PT.request_node_from_name_and_label(tree, "NFace", "ZoneSubRegion_t")                                    is None
  assert PT.request_node_from_value_and_label(tree, np.array([1230,0], order='F'), "Elements_t")                  is None
  assert PT.request_node_from_value_and_label(tree, np.array([23,0], order='F'), "ZoneSubRegion_t")               is None
  assert PT.request_node_from_name_value_and_label(tree, "TOTO", np.array([23,0], order='F'), "Elements_t")       is None
  assert PT.request_node_from_name_value_and_label(tree, "NFace", np.array([1230,0], order='F'), "Elements_t")    is None
  assert PT.request_node_from_name_value_and_label(tree, "NFace", np.array([23,0], order='F'), "ZoneSubRegion_t") is None

  # requestNodeFromPredicate{depth} and dfs
  # =======================================
  # Camel case
  assert PT.requestNodeFromPredicate1(tree, lambda n: I.getName(n) == "ZoneI", search="dfs") is None
  assert is_zonei(PT.requestNodeFromPredicate2(tree, lambda n: I.getName(n) == "ZoneI", search="dfs"))
  assert is_zonei(PT.requestNodeFromPredicate3(tree, lambda n: I.getName(n) == "ZoneI", search="dfs"))

  # Snake case
  assert PT.request_node_from_predicate1(tree, lambda n: I.getName(n) == "ZoneI", search="dfs") is None
  assert is_zonei(PT.request_node_from_predicate2(tree, lambda n: I.getName(n) == "ZoneI", search="dfs"))
  assert is_zonei(PT.request_node_from_predicate3(tree, lambda n: I.getName(n) == "ZoneI", search="dfs"))

  # requestNodeFrom{Name, Label, ...}{depth}
  # ========================================
  # Camel case
  # ----------
  assert PT.requestNodeFromName(tree, "ZoneI", search="dfs", depth=1) is None
  assert is_zonei(PT.requestNodeFromName(tree, "ZoneI", search="dfs", depth=2))
  assert is_zonei(PT.requestNodeFromName(tree, "ZoneI", search="dfs", depth=3))

  assert PT.requestNodeFromName1(tree, "ZoneI") is None
  assert is_zonei(PT.requestNodeFromName2(tree, "ZoneI"))
  assert is_zonei(PT.requestNodeFromName3(tree, "ZoneI"))

  assert is_base    (PT.requestNodeFromName1(tree, "Base")   )
  assert is_zonei   (PT.requestNodeFromName2(tree, "ZoneI")  )
  assert is_ngon    (PT.requestNodeFromName3(tree, "Ngon")   )
  assert is_bc1     (PT.requestNodeFromName4(tree, "bc1")    )
  assert is_index_i (PT.requestNodeFromName5(tree, "Index_i"))

  assert is_base  (PT.requestNodeFromLabel1(tree, "CGNSBase_t"))
  assert is_zonei (PT.requestNodeFromLabel2(tree, "Zone_t")    )
  assert is_ngon  (PT.requestNodeFromLabel3(tree, "Elements_t"))
  assert is_bc1   (PT.requestNodeFromLabel4(tree, "BC_t")      )

  # Snake case
  # ----------
  assert PT.request_node_from_name(tree, "ZoneI", search="dfs", depth=1) is None
  assert is_zonei( PT.request_node_from_name(tree, "ZoneI", search="dfs", depth=2) )
  assert is_zonei( PT.request_node_from_name(tree, "ZoneI", search="dfs", depth=3) )

  assert PT.request_node_from_name1(tree, "ZoneI") is None
  assert is_zonei( PT.request_node_from_name2(tree, "ZoneI") )
  assert is_zonei( PT.request_node_from_name3(tree, "ZoneI") )

  assert is_base    (PT.request_node_from_name1(tree, "Base")   )
  assert is_zonei   (PT.request_node_from_name2(tree, "ZoneI")  )
  assert is_ngon    (PT.request_node_from_name3(tree, "Ngon")   )
  assert is_bc1     (PT.request_node_from_name4(tree, "bc1")    )
  assert is_index_i (PT.request_node_from_name5(tree, "Index_i"))

  assert is_index_i ( PT.requestNodeFromLabel5(tree, "IndexArray_t")    )
  assert is_base    ( PT.request_node_from_label1(tree, "CGNSBase_t")   )
  assert is_zonei   ( PT.request_node_from_label2(tree, "Zone_t")       )
  assert is_ngon    ( PT.request_node_from_label3(tree, "Elements_t")   )
  assert is_bc1     ( PT.request_node_from_label4(tree, "BC_t")         )
  assert is_index_i ( PT.request_node_from_label5(tree, "IndexArray_t") )

  # getNodeFrom...
  # **************

  # getNodeFromPredicate
  # ====================
  # Camel case
  # ----------
  assert is_base  ( PT.getNodeFromPredicate(tree, lambda n: I.getName(n) == "Base")                   )
  assert is_zonei ( PT.getNodeFromPredicate(tree, lambda n: I.getName(n) == "ZoneI", search="dfs")    )
  assert is_base  ( PT.get_node_from_predicate(tree, lambda n: I.getName(n) == "Base")                )
  assert is_zonei ( PT.get_node_from_predicate(tree, lambda n: I.getName(n) == "ZoneI", search="dfs") )

  # Snake case
  # ----------
  assert is_nface ( PT.getNodeFromName(tree, "NFace")                                                               )
  assert is_nface ( PT.getNodeFromValue(tree, np.array([23,0], order='F'))                                          )
  assert is_ngon  ( PT.getNodeFromLabel(tree, "Elements_t")                                                         )
  assert is_nface ( PT.getNodeFromNameAndValue(tree, "NFace", np.array([23,0], order='F'))                          )
  assert is_nface ( PT.getNodeFromNameAndLabel(tree, "NFace", "Elements_t")                                         )
  assert is_nface ( PT.getNodeFromValueAndLabel(tree, np.array([23,0], dtype='int64',order='F'), "Elements_t")      )
  assert is_nface ( PT.getNodeFromNameValueAndLabel(tree, "NFace", np.array([23,0], order='F'), "Elements_t")       )
  assert is_nface ( PT.get_node_from_name(tree, "NFace")                                                            )
  assert is_nface ( PT.get_node_from_value(tree, np.array([23,0], order='F'))                                       )
  assert is_ngon  ( PT.get_node_from_label(tree, "Elements_t")                                                      )
  assert is_nface ( PT.get_node_from_name_and_value(tree, "NFace", np.array([23,0], order='F'))                     )
  assert is_nface ( PT.get_node_from_name_and_label(tree, "NFace", "Elements_t")                                    )
  assert is_nface ( PT.get_node_from_value_and_label(tree, np.array([23,0], dtype='int64',order='F'), "Elements_t") )
  assert is_nface ( PT.get_node_from_name_value_and_label(tree, "NFace", np.array([23,0], order='F'), "Elements_t") )

def test_getNodesFromPredicate1():
  with open(os.path.join(dir_path, "minimal_bc_tree.yaml"), 'r') as yt:
    tree = parse_yaml_cgns.to_cgns_tree(yt)

  # Camel case
  # ----------
  # Test from Name
  base = I.getBases(tree)[0]
  nodes_from_name1 = ["ZoneI"]
  assert [I.getName(n) for n in PT.getNodesFromPredicate1(base, lambda n: I.getName(n) == "ZoneI")] == nodes_from_name1
  # Wildcard is not allowed in getNodesFromName1() from Cassiopee
  assert I.getNodesFromName1(base, "Zone*") == []
  assert [I.getName(n) for n in PT.getNodesFromPredicate1(base, lambda n: fnmatch.fnmatch(I.getName(n), "Zone*"))] == nodes_from_name1
  assert [I.getName(n) for n in PT.getNodesFromName1(base, "Zone*")] == nodes_from_name1
  assert [I.getName(n) for n in PT.getNodesFromName1(base, "Base")] == ["Base"]

  # Test from Type
  nodes_from_type1 = ["Zone_t"]
  assert [I.getType(n) for n in PT.getNodesFromPredicate1(base, lambda n: I.getType(n) == CGL.Zone_t.name)] == nodes_from_type1
  assert [I.getType(n) for n in PT.getNodesFromLabel1(base, CGL.Zone_t.name)] == nodes_from_type1

  # Test from Value
  zone = I.getNodeFromType(tree, 'Zone_t')
  ngon_value = np.array([22,0], dtype=np.int32)
  elements_from_type_value1 = [ngon_value[0]]
  assert [I.getVal(n)[0] for n in PT.getNodesFromPredicate1(zone, lambda n: I.getType(n) == CGL.Elements_t.name and np.array_equal(I.getVal(n), ngon_value))] == elements_from_type_value1
  assert [I.getVal(n)[0] for n in PT.getNodesFromValue1(zone, ngon_value)] == elements_from_type_value1

  zonebcs_from_type_name1 = ['ZBCB']
  assert [I.getName(n) for n in PT.getNodesFromPredicate1(zone, lambda n: I.getType(n) == CGL.ZoneBC_t.name and I.getName(n) != "ZBCA")] == zonebcs_from_type_name1

  # Snake case
  # ----------
  # Test from Name
  base = PT.getNodeFromLabel(tree, 'CGNSBase_t') # get the first base
  nodes_from_name1 = ["ZoneI"]
  assert [I.getName(n) for n in PT.get_nodes_from_predicate1(base, lambda n: I.getName(n) == "ZoneI")] == nodes_from_name1
  assert [I.getName(n) for n in PT.get_nodes_from_predicate1(base, lambda n: fnmatch.fnmatch(I.getName(n), "Zone*"))] == nodes_from_name1
  assert [I.getName(n) for n in PT.get_nodes_from_name1(base, "Zone*")] == nodes_from_name1
  assert [I.getName(n) for n in PT.get_nodes_from_name1(base, "Base")] == ["Base"]

  # Test from Type
  nodes_from_type1 = ["Zone_t"]
  assert [I.getType(n) for n in PT.get_nodes_from_predicate1(base, lambda n: I.getType(n) == CGL.Zone_t.name)] == nodes_from_type1
  assert [I.getType(n) for n in PT.get_nodes_from_label1(base, CGL.Zone_t.name)] == nodes_from_type1

  # Test from Value
  zone = I.getNodeFromType(tree, 'Zone_t')
  ngon_value = np.array([22,0], dtype=np.int32)
  elements_from_type_value1 = [ngon_value[0]]
  assert [I.getVal(n)[0] for n in PT.get_nodes_from_predicate1(zone, lambda n: I.getType(n) == CGL.Elements_t.name and np.array_equal(I.getVal(n), ngon_value))] == elements_from_type_value1
  assert [I.getVal(n)[0] for n in PT.get_nodes_from_value1(zone, ngon_value)] == elements_from_type_value1

  zonebcs_from_type_name1 = ['ZBCB']
  assert [I.getName(n) for n in PT.get_nodes_from_predicate1(zone, lambda n: I.getType(n) == CGL.ZoneBC_t.name and I.getName(n) != "ZBCA")] == zonebcs_from_type_name1


def test_getAllLabel():
  yt = """
Base CGNSBase_t:
  ZoneI Zone_t:
    NgonI Elements_t [22,0]:
    ZBCAI ZoneBC_t:
      bc1I BC_t:
        Index_i IndexArray_t:
        PL1I DataArray_t:
      bc2 BC_t:
        Index_ii IndexArray_t:
        PL2 DataArray_t:
    ZBCBI ZoneBC_t:
      bc3I BC_t:
        Index_iii IndexArray_t:
        PL3I DataArray_t:
      bc4 BC_t:
      bc5 BC_t:
        Index_iv IndexArray_t:
        Index_v IndexArray_t:
        Index_vi IndexArray_t:
        PL4 DataArray_t:
  ZoneJ Zone_t:
    NgonJ Elements_t [22,0]:
    ZBCAJ ZoneBC_t:
      bc1J BC_t:
        Index_j IndexArray_t:
        PL1J DataArray_t:
    ZBCBJ ZoneBC_t:
      bc3J BC_t:
        Index_jjj IndexArray_t:
        PL3J DataArray_t:
"""
  tree = parse_yaml_cgns.to_cgns_tree(yt)
  # Camel case
  # ==========
  assert([I.getName(n) for n in PT.getNodesFromLabelCGNSBase(tree)] == ['Base'])
  assert([I.getName(n) for n in PT.getNodesFromLabelZone(tree)] == ['ZoneI', 'ZoneJ'])
  assert([I.getName(n) for n in PT.getNodesFromLabelElements(tree)] == ['NgonI', 'NgonJ'])
  assert([I.getName(n) for n in PT.getNodesFromLabelZoneBC(tree)] == ['ZBCAI', 'ZBCBI', 'ZBCAJ', 'ZBCBJ'])
  assert([I.getName(n) for n in PT.getNodesFromLabelBC(tree)] == ['bc1I', 'bc2', 'bc3I', 'bc4', 'bc5', 'bc1J', 'bc3J'])

  assert([I.getName(n) for n in PT.getNodesFromLabelCGNSBase(tree, depth=1)] == ['Base'])
  assert([I.getName(n) for n in PT.getNodesFromLabelZone(tree, depth=1)] == [])
  assert([I.getName(n) for n in PT.getNodesFromLabelZone(tree, depth=2)] == ['ZoneI', 'ZoneJ'])
  assert([I.getName(n) for n in PT.getNodesFromLabelElements(tree, depth=1)] == [])
  assert([I.getName(n) for n in PT.getNodesFromLabelElements(tree, depth=2)] == [])
  assert([I.getName(n) for n in PT.getNodesFromLabelElements(tree, depth=3)] == ['NgonI', 'NgonJ'])

  # Snake case
  # ==========
  assert([I.getName(n) for n in PT.get_nodes_from_label_cgns_base(tree)] == ['Base'])
  assert([I.getName(n) for n in PT.get_nodes_from_label_zone(tree)] == ['ZoneI', 'ZoneJ'])
  assert([I.getName(n) for n in PT.get_nodes_from_label_elements(tree)] == ['NgonI', 'NgonJ'])
  assert([I.getName(n) for n in PT.get_nodes_from_label_zone_bc(tree)] == ['ZBCAI', 'ZBCBI', 'ZBCAJ', 'ZBCBJ'])
  assert([I.getName(n) for n in PT.get_nodes_from_label_bc(tree)] == ['bc1I', 'bc2', 'bc3I', 'bc4', 'bc5', 'bc1J', 'bc3J'])


def test_getCGNSName():
  yt = """
Base CGNSBase_t:
  ZoneI Zone_t:
    Coordinates GridCoordinates_t:
      CoordinateX DataArray_t:
      CoordinateY DataArray_t:
      CoordinateZ DataArray_t:
"""
  tree = parse_yaml_cgns.to_cgns_tree(yt)

  # Camel case
  # ==========
  assert(I.getName(PT.getNodesFromNameCoordinateX(tree)[0]) == 'CoordinateX')
  assert(I.getName(PT.getNodesFromNameCoordinateY(tree)[0]) == 'CoordinateY')
  assert(I.getName(PT.getNodesFromNameCoordinateZ(tree)[0]) == 'CoordinateZ')

  grid_coordinates_node = PT.getNodeFromLabel(tree,'GridCoordinates_t')
  assert(I.getName(PT.getNodesFromNameCoordinateX(grid_coordinates_node, depth=1)[0]) == 'CoordinateX')
  assert(I.getName(PT.getNodesFromNameCoordinateY(grid_coordinates_node, depth=1)[0]) == 'CoordinateY')
  assert(I.getName(PT.getNodesFromNameCoordinateZ(grid_coordinates_node, depth=1)[0]) == 'CoordinateZ')

  zone_node = PT.getNodeFromLabel(tree,'Zone_t')
  assert(PT.getNodesFromNameCoordinateX(zone_node, depth=1) == [])
  assert(PT.getNodesFromNameCoordinateY(zone_node, depth=1) == [])
  assert(PT.getNodesFromNameCoordinateZ(zone_node, depth=1) == [])

  # Snake case
  # ==========
  assert(I.getName(PT.get_nodes_from_name_coordinate_x(tree)[0]) == 'CoordinateX')
  assert(I.getName(PT.get_nodes_from_name_coordinate_y(tree)[0]) == 'CoordinateY')
  assert(I.getName(PT.get_nodes_from_name_coordinate_z(tree)[0]) == 'CoordinateZ')

