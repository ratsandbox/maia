from typing import List, Tuple
from functools import wraps
from functools import partial
import sys
import pathlib
import fnmatch
import numpy as np
import Converter.Internal as I
import maia.sids.cgns_keywords as CGK

module_object = sys.modules[__name__]

# --------------------------------------------------------------------------
class CGNSNodeFromPredicateNotFoundError(Exception):
    """
    Attributes:
        node (List): CGNS node
        name (str): Name of the CGNS Name
    """
    def __init__(self, node: List, predicate):
        self.node = node
        self.predicate = predicate
        super().__init__()

    def __str__(self):
        return f"Unable to find the predicate '{self.predicate}' from the CGNS node '[n:{I.getName(self.node)}, ..., l:{I.getType(self.node)}]', see : \n{I.printTree(self.node)}."

class CGNSLabelNotEqualError(Exception):
    """
    Attributes:
        node (List): CGNS node
        label (str): Name of the CGNS Label
    """
    def __init__(self, node: List, label: str):
        self.node  = node
        self.label = label
        super().__init__()

    def __str__(self):
        return f"Expected a CGNS node with label '{self.label}', '[n:{I.getName(self.node)}, ..., l:{I.getType(self.node)}]' found here."

class NotImplementedForElementError(NotImplementedError):
    """
    Attributes:
        zone_node (List): CGNS Zone_t node
        element_node (List): CGNS Elements_t node
    """
    def __init__(self, zone_node: List, element_node: List):
        self.zone_node    = zone_node
        self.element_node = element_node
        super().__init__()

    def __str__(self):
        return f"Unstructured CGNS Zone_t named '{I.getName(self.zone_node)}' with CGNS Elements_t named '{SIDS.ElementCGNSName(self.element_node)}' is not yet implemented."

# --------------------------------------------------------------------------
def is_valid_name(name: str):
  """
  Return True if name is a valid Python/CGNS name
  """
  return isinstance(name, str) #and len(label) < 32

def is_valid_value(value):
  """
  Return True if label is a valid Python/CGNS Label
  """
  return isinstance(value, np.ndarray) and np.isfortran(value) if value.ndim > 1 else True

def is_valid_children(children):
  """
  Return True if label is a valid Python/CGNS Children
  """
  return isinstance(children, (list, tuple))

def is_valid_label(label):
  """
  Return True if label is a valid Python/CGNS Label
  """
  return isinstance(label, str) and ((label.endswith('_t') and label in CGK.Label.__members__) or label == '')

# --------------------------------------------------------------------------
def check_name(name: str):
  if is_valid_name(name):
    return name
  raise TypeError(f"Invalid Python/CGNS name '{name}'")

def check_value(value):
  if is_valid_value(value):
    return value
  raise TypeError(f"Invalid Python/CGNS value '{value}'")

def check_children(children):
  if is_valid_children(children):
    return children
  raise TypeError(f"Invalid Python/CGNS children '{children}'")

def check_label(label):
  if is_valid_label(label):
    return label
  raise TypeError(f"Invalid Python/CGNS label '{label}'")

# --------------------------------------------------------------------------
def is_valid_cgns_node(node):
    if not isinstance(node, list) and len(node) != 4 and \
       is_valid_name(I.getName(node))         and \
       is_valid_value(I.getValue(node))       and \
       is_valid_children(I.getChildren(node)) and \
       is_valid_label(I.getName(node)) :
      return False
    return True

# --------------------------------------------------------------------------
def check_is_label(label):
    def _check_is_label(f):
        @wraps(f)
        def wrapped_method(*args, **kwargs):
          node = args[0]
          if I.getType(node) != label:
            raise CGNSLabelNotEqualError(node, label)
          return f(*args, **kwargs)
        return wrapped_method
    return _check_is_label

# --------------------------------------------------------------------------
def match_name(n, name: str):
  return fnmatch.fnmatch(n[0], name)

def match_value(n, value):
  return np.array_equal(n[1], value)

def match_label(n, label: str):
  return n[3] == label

def match_path(n, path: str):
  path1 = pathlib.Path(I.getPath(n))
  path2 = pathlib.Path(path)
  return path1 == path2

def match_name_value(n, name: str, value):
  return fnmatch.fnmatch(n[0], name) and np.array_equal(n[1], value)

def match_name_label(n, name: str, label: str):
  return n[3] == label and fnmatch.fnmatch(n[0], name)

def match_name_value_label(n, name: str, value, label: str):
  return n[3] == label and fnmatch.fnmatch(n[0], name) and np.array_equal(n[1], value)

def match_value_label(n, value, label: str):
  return n[3] == label and np.array_equal(n[1], value)

allfuncs = {
  'Name' : (match_name,  ('name',)),
  'Value': (match_value, ('value',)),
  'Label': (match_label, ('label',)),
  'Path' : (match_path,  ('path',)),
  'NameAndValue' : (match_name_value,  ('name', 'value',)),
  'NameAndLabel' : (match_name_label,  ('name', 'label',)),
  'ValueAndLabel': (match_value_label, ('value', 'label',)),
  'NameValueAndLabel': (match_name_value_label, ('name', 'value', 'label',)),
}

MAXDEPTH = 10

# --------------------------------------------------------------------------
def create_methods(method, create_method, funcs):
  alias = method.__name__.replace('Predicate', '')
  print(f"method : {method}")
  print(f"method.__name__ : {method.__name__}")
  print(f"alias : {alias}")
  for depth in range(1,MAXDEPTH+1):
    func = partial(method, method='dfs', depth=depth)
    funcname = f"{method.__name__}{depth}"
    func.__name__ = funcname
    setattr(module_object, funcname, func)

  for what, item in funcs.items():
    predicate, nargs = item
    func = create_method(predicate, nargs)
    funcname = f"{alias}{what}"
    func.__name__ = funcname
    setattr(module_object, funcname, func) # bfs

  for what, item in funcs.items():
    predicate, nargs = item
    for depth in range(1,MAXDEPTH+1):
      func = create_method(predicate, nargs)
      funcname = f"{alias}{what}{depth}"
      func.__name__ = funcname
      setattr(module_object, funcname, partial(func, method='dfs', depth=depth))

# --------------------------------------------------------------------------
class NodeParser:

  DEFAULT="bfs"

  def bfs(self, parent, predicate):
    for child in parent[2]:
      if predicate(child):
        return child
    # Explore next level
    for child in parent[2]:
      result = self.bfs(child, predicate)
      if result is not None:
        return result
    return None

  def dfs(self, parent, predicate):
    for child in parent[2]:
      if predicate(child):
        return child
      # Explore next level
      result = self.dfs(child, predicate)
      if result is not None:
        return result
    return None

# --------------------------------------------------------------------------
class LevelNodeParser:

  MAXDEPTH=30

  def __init__(self, depth=MAXDEPTH):
    self.depth = depth

  def bfs(self, parent, predicate, level=1):
    # print(f"LevelNodeParser.bfs: level = {level} < depth = {self.depth}: parent = {I.getName(parent)}")
    for child in parent[2]:
      if predicate(child):
        return child
    if level < self.depth:
      # Explore next level
      for child in parent[2]:
        result = self.bfs(child, predicate, level=level+1)
        if result is not None:
          return result
    return None

  def dfs(self, parent, predicate, level=1):
    # print(f"LevelNodeParser.dfs: level = {level} < depth = {self.depth}: parent = {I.getName(parent)}")
    for child in parent[2]:
      if predicate(child):
        return child
      if level < self.depth:
        # Explore next level
        result = self.dfs(child, predicate, level=level+1)
        if result is not None:
          return result
    return None

# --------------------------------------------------------------------------
def requestChildFromPredicate(parent, predicate, method=NodeParser.DEFAULT, depth=None):
  parser = LevelNodeParser(depth=depth) if isinstance(depth, int) else NodeParser()
  func   = getattr(parser, method)
  return func(parent, predicate)

def create_request_child(predicate, nargs):
  def _get_request_from(parent, *args, **kwargs):
    pkwargs = dict([(narg, arg,) for narg, arg in zip(nargs, args)])
    return requestChildFromPredicate(parent, partial(predicate, **pkwargs), **kwargs)
  return _get_request_from

create_methods(requestChildFromPredicate, create_request_child, allfuncs)

# --------------------------------------------------------------------------
def getChildFromPredicate(parent, predicate, default=None, method=NodeParser.DEFAULT, depth=None):
  """ Return the list of first level childs of node matching a given predicate (callable function)"""
  n = requestChildFromPredicate(parent, predicate, method=method, depth=depth)
  if n is not None:
    return n
  if default and is_valid_cgns_node(default):
    return default
  raise CGNSNodeFromPredicateNotFoundError(parent, predicate)

def create_get_child(predicate, nargs):
  def _get_child_from(parent, *args, **kwargs):
    pkwargs = dict([(narg, arg,) for narg, arg in zip(nargs, args)])
    try:
      return getChildFromPredicate(parent, partial(predicate, **pkwargs), **kwargs)
    except CGNSNodeFromPredicateNotFoundError as e:
      print(f"For predicate : pkwargs = {pkwargs}", file=sys.stderr)
      raise e
  return _get_child_from

create_methods(getChildFromPredicate, create_get_child, allfuncs)

# --------------------------------------------------------------------------
class NodesParser:

  DEFAULT="bfs"

  def __init__(self):
    self.result = []

  def bfs(self, parent, predicate):
    for child in parent[2]:
      if predicate(child):
        self.result.append(child)
    # Explore next level
    for child in parent[2]:
      self.bfs(child, predicate)
    return self.result

  def dfs(self, parent, predicate):
    for child in parent[2]:
      if predicate(child):
        self.result.append(child)
      # Explore next level
      self.dfs(child, predicate)
    return self.result

# --------------------------------------------------------------------------
class LevelNodesParser:

  MAXDEPTH=30

  def __init__(self, depth=MAXDEPTH):
    self.depth  = depth
    self.result = []

  def bfs(self, parent, predicate, level=1):
    # print(f"LevelNodesParser.bfs: level = {level} < depth = {self.depth}: parent = {I.getName(parent)}")
    for child in parent[2]:
      if predicate(child):
        self.result.append(child)
    if level < self.depth:
      # Explore next level
      for child in parent[2]:
        self.bfs(child, predicate, level=level+1)
    return self.result

  def dfs(self, parent, predicate, level=1):
    # print(f"LevelNodesParser.dfs: level = {level} < depth = {self.depth}: parent = {I.getName(parent)}")
    for child in parent[2]:
      if predicate(child):
        self.result.append(child)
      if level < self.depth:
        # Explore next level
        self.dfs(child, predicate, level=level+1)
    return self.result

# --------------------------------------------------------------------------
def getChildrenFromPredicate(parent, predicate, method=NodeParser.DEFAULT, depth=None):
  parser = LevelNodesParser(depth=depth) if isinstance(depth, int) else NodesParser()
  func   = getattr(parser, method)
  return func(parent, predicate)

def create_get_children(predicate, nargs):
  def _get_children_from(parent, *args, **kwargs):
    pkwargs = dict([(narg, arg,) for narg, arg in zip(nargs, args)])
    return getChildrenFromPredicate(parent, partial(predicate, **pkwargs), **kwargs)
  return _get_children_from

create_methods(getChildrenFromPredicate, create_get_children, dict((k,v) for k,v in allfuncs.items() if k not in ['Path', 'NameValueAndLabel']))

# --------------------------------------------------------------------------
def getNodesDispatch1(node, predicate):
  """ Interface to adapted getNodesFromXXX1 function depending of predicate type"""
  if isinstance(predicate, str):
    return getChildrenFromLabel1(node, predicate) if is_valid_label(predicate) else getChildrenFromName1(node, predicate)
  elif isinstance(predicate, CGK.Label):
    return getChildrenFromLabel1(node, predicate.name)
  elif isinstance(predicate, np.ndarray):
    return getChildrenFromValue1(node, predicate)
  elif callable(predicate):
    return getChildrenFromPredicate1(node, predicate)
  else:
    raise TypeError("predicate must be a string for name, a numpy for value, a CGNS Label or a callable python function.")

# --------------------------------------------------------------------------
def getNodesByMatching(root, predicates):
  """Generator following predicates, doing 1 level search using
  getChildrenFromLabel1 or getChildrenFromName1. Equivalent to
  (predicate = 'type1_t/name2/type3_t' or ['type1_t', 'name2', lambda n: I.getType(n) == CGL.type3_t.name] )
  for level1 in I.getNodesFromType1(root, type1_t):
    for level2 in I.getNodesFromName1(level1, name2):
      for level3 in I.getNodesFromType1(level2, type3_t):
        ...
  """
  predicate_list = []
  if isinstance(predicates, str):
    for predicate in predicates.split('/'):
      predicate_list.append(eval(predicate) if predicate.startswith('lambda') else predicate)
  elif isinstance(predicates, (list, tuple)):
    predicate_list = predicates
  else:
    raise TypeError("predicates must be a sequence or a path as with strings separated by '/'.")

  yield from getNodesByMatching__(root, predicate_list)

def getNodesByMatching__(root, predicate_list):
  if len(predicate_list) > 1:
    next_roots = getNodesDispatch1(root, predicate_list[0])
    for node in next_roots:
      yield from getNodesByMatching__(node, predicate_list[1:])
  elif len(predicate_list) == 1:
    yield from getNodesDispatch1(root, predicate_list[0])

# --------------------------------------------------------------------------
def getNodesWithParentsByMatching(root, predicates):
  """Same than getNodesByMatching, but return
  a tuple of size len(predicates) containing the node and its parents
  """
  predicate_list = []
  if isinstance(predicates, str):
    for predicate in predicates.split('/'):
      predicate_list.append(eval(predicate) if predicate.startswith('lambda') else predicate)
  elif isinstance(predicates, (list, tuple)):
    predicate_list = predicates
  else:
    raise TypeError("predicates must be a sequence or a path with strings separated by '/'.")

  yield from getNodesWithParentsByMatching__(root, predicate_list)

def getNodesWithParentsByMatching__(root, predicate_list):
  if len(predicate_list) > 1:
    next_roots = getNodesDispatch1(root, predicate_list[0])
    for node in next_roots:
      for subnode in getNodesWithParentsByMatching__(node, predicate_list[1:]):
        yield (node, *subnode)
  elif len(predicate_list) == 1:
    nodes =  getNodesDispatch1(root, predicate_list[0])
    for node in nodes:
      yield (node,)

# --------------------------------------------------------------------------
# getNodeFromNameAndType  = requestChildFromNameAndLabel
# getNodeFromNameAndType1 = requestChildFromNameAndLabel1
# getNodeFromNameAndType2 = requestChildFromNameAndLabel2
# getNodeFromNameAndType3 = requestChildFromNameAndLabel3

# --------------------------------------------------------------------------
# def create_require_node(what, level):
#   def _require_node_from(parent, arg):
#     funcname = f"getNodeFrom{what}{level}"
#     node = getattr(I, funcname)(parent, arg)
#     if node is None:
#       raise getattr(module_object, f"CGNS{'Label' if what == 'Type' else what}NotFoundError")(parent, arg)
#     return node
#   return _require_node_from

# for what in ['Name', 'Type']:
#   for level in ['']+[str(i) for i in range(1,4)]:
#     func = create_require_node(what, level)
#     funcname = f"requireNodeFrom{what}{level}"
#     func.__name__ = funcname
#     setattr(module_object, funcname, func)

# requireNodeFromName  = getChildFromName
# requireNodeFromName1 = getChildFromName1
# requireNodeFromName2 = getChildFromName2
# requireNodeFromName3 = getChildFromName3

# requireNodeFromType  = getChildFromLabel
# requireNodeFromType1 = getChildFromLabel1
# requireNodeFromType2 = getChildFromLabel2
# requireNodeFromType3 = getChildFromLabel3

# requireNodeFromNameAndType  = getChildFromNameAndLabel
# requireNodeFromNameAndType1 = getChildFromNameAndLabel1
# requireNodeFromNameAndType2 = getChildFromNameAndLabel2
# requireNodeFromNameAndType3 = getChildFromNameAndLabel3

# --------------------------------------------------------------------------
def getSubregionExtent(sub_region_n, zone):
  """
  Return the path of the node (starting from zone node) related to sub_region_n
  node (BC, GC or itself)
  """
  assert I.getType(sub_region_n) == "ZoneSubRegion_t"
  if I.getNodeFromName1(sub_region_n, "BCRegionName") is not None:
    for zbc, bc in getNodesWithParentsByMatching(zone, "ZoneBC_t/BC_t"):
      if I.getName(bc) == I.getValue(I.getNodeFromName1(sub_region_n, "BCRegionName")):
        return I.getName(zbc) + '/' + I.getName(bc)
  elif I.getNodeFromName1(sub_region_n, "GridConnectivityRegionName") is not None:
    gc_pathes = ["ZoneGridConnectivity_t/GridConnectivity_t", "ZoneGridConnectivity_t/GridConnectivity1to1_t"]
    for gc_path in gc_pathes:
      for zgc, gc in getNodesWithParentsByMatching(zone, gc_path):
        if I.getName(gc) == I.getValue(I.getNodeFromName1(sub_region_n, "GridConnectivityRegionName")):
          return I.getName(zgc) + '/' + I.getName(gc)
  else:
    return I.getName(sub_region_n)

  raise ValueError("ZoneSubRegion {0} has no valid extent".format(I.getName(sub_region_n)))

def getDistribution(node, distri_name=None):
  """
  Starting from node, return the CGNS#Distribution node if distri_name is None
  or the value of the requested distribution if distri_name is not None
  """
  return I.getNodeFromPath(node, '/'.join([':CGNS#Distribution', distri_name])) if distri_name \
      else I.getNodeFromName1(node, ':CGNS#Distribution')

def getGlobalNumbering(node, lngn_name=None):
  """
  Starting from node, return the CGNS#GlobalNumbering node if lngn_name is None
  or the value of the requested globalnumbering if lngn_name is not None
  """
  return I.getNodeFromPath(node, '/'.join([':CGNS#GlobalNumbering', lngn_name])) if lngn_name \
      else I.getNodeFromName1(node, ':CGNS#GlobalNumbering')

# --------------------------------------------------------------------------
def newDistribution(distributions = dict(), parent=None):
  """
  Create and return a CGNSNode to be used to store distribution data
  Attach it to parent node if not None
  In addition, add distribution arrays specified in distributions dictionnary.
  distributions must be a dictionnary {DistriName : distri_array}
  """
  distri_node = I.newUserDefinedData(':CGNS#Distribution', None, parent)
  for name, value in distributions.items():
    I.newDataArray(name, value, parent=distri_node)
  return distri_node

def newGlobalNumbering(glob_numberings = dict(), parent=None):
  """
  Create and return a CGNSNode to be used to store distribution data
  Attach it to parent node if not None
  In addition, add global numbering arrays specified in glob_numberings dictionnary.
  glob_numberings must be a dictionnary {NumberingName : lngn_array}
  """
  lngn_node = I.newUserDefinedData(':CGNS#GlobalNumbering', None, parent)
  for name, value in glob_numberings.items():
    I.newDataArray(name, value, parent=lngn_node)
  return lngn_node
