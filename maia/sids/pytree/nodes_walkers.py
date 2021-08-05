from typing import List, Optional, NoReturn, Union, Tuple, Callable, Any
# from functools import partial
import numpy as np
import copy

from ._node_parsers2 import iter_nodes_from_predicates_for_each__, \
                            iter_nodes_from_predicates__, \
                            iter_nodes_from_predicates_with_parents_for_each__, \
                            iter_nodes_from_predicates_with_parents__

# import maia.utils.py_utils as PYU

from .compare import is_valid_node

TreeNode = List[Union[str, Optional[np.ndarray], List["TreeNode"]]]

# --------------------------------------------------------------------------
#
#   NodesWalkers
#
# --------------------------------------------------------------------------
class NodesWalkers:

  def __init__(self, root, predicates, **kwargs):
    self.root       = root
    self.predicates = predicates
    self.kwargs     = kwargs
    self.ancestors  = kwargs.get('ancestors', False)
    if kwargs.get('ancestors'):
      kwargs.pop('ancestors')
    self._cache = []

  @property
  def root(self):
    return self._root

  @root.setter
  def root(self, node: TreeNode):
    if is_valid_node(node):
      self._root = node
      self.clean()

  @property
  def predicates(self):
    return self._predicates

  @predicates.setter
  def predicates(self, value):
    self._predicates = []
    if isinstance(value, str):
      self._predicates = value.split('/')
      self.clean()
    elif isinstance(value, (list, tuple, dict)):
      self._predicates = value
      self.clean()
    else:
      raise TypeError("predicates must be a sequence of predicates or a path of name or label separated by '/'.")

  @property
  def ancestors(self):
    return self._ancestor

  @ancestors.setter
  def ancestors(self, value):
    if isinstance(value, bool):
      self._ancestor = value
      self.clean()
    else:
      raise TypeError("ancestors must be a boolean.")

  @property
  def caching(self):
    return self.kwargs.get("caching", False)

  @caching.setter
  def caching(self, value):
    if isinstance(value, bool):
      self.kwargs['caching'] = value
      self.clean()
    else:
      raise TypeError("caching must be a boolean.")

  @property
  def cache(self):
    return self._cache

  @property
  def parser(self):
    return self._parser

  def _deconv_kwargs(self):
    predicates = []; for_each = []
    for kwargs in self.predicates:
      lkwargs = {}
      for k,v in kwargs.items():
        if k == 'predicate':
          predicates.append(v)
        else:
          lkwargs[k] = v
      for_each.append(lkwargs)
    if len(predicates) != len(self.predicates):
      raise ValueError(f"Missing predicate.")
    return predicates, for_each

  def __call__(self):
    if self.ancestors:
      return self._parse_with_parents()
    else:
      return self._parse()

  def _parse_with_parents(self):
    if any([isinstance(kwargs, dict) for kwargs in self.predicates]):
      predicates, for_each = self._deconv_kwargs()
      for index, kwargs in enumerate(for_each):
        if kwargs.get('caching'):
          print(f"Warning: unable to activate caching for predicate at index {index}.")
          kwargs['caching'] = False
      if self.caching:
        if not bool(self._cache):
          self._cache = list(iter_nodes_from_predicates_with_parents_for_each__(self.root, predicates, for_each))
        return self._cache
      else:
        return iter_nodes_from_predicates_with_parents_for_each__(self.root, predicates, for_each)
    else:
      if self.caching:
        if not bool(self._cache):
          kwargs = copy.deepcopy(self.kwargs)
          kwargs['caching'] = False
          self._cache = list(iter_nodes_from_predicates_with_parents__(self.root, self.predicates, **kwargs))
        return self._cache
      else:
        return iter_nodes_from_predicates_with_parents__(self.root, self.predicates, **self.kwargs)

  def _parse(self):
    if any([isinstance(kwargs, dict) for kwargs in self.predicates]):
      predicates, for_each = self._deconv_kwargs()
      for index, kwargs in enumerate(for_each):
        if kwargs.get('caching'):
          print(f"Warning: unable to activate caching for predicate at index {index}.")
          kwargs['caching'] = False
      if self.caching:
        if not bool(self._cache):
          self._cache = list(iter_nodes_from_predicates_for_each__(self.root, predicates, for_each))
        return self._cache
      else:
        return iter_nodes_from_predicates_for_each__(self.root, predicates, for_each)
    else:
      if self.caching:
        if not bool(self._cache):
          kwargs = copy.deepcopy(self.kwargs)
          kwargs['caching'] = False
          self._cache = list(iter_nodes_from_predicates__(self.root, self.predicates, **kwargs))
        return self._cache
      else:
        return iter_nodes_from_predicates__(self.root, self.predicates, **self.kwargs)

  def apply(self, f, *args, **kwargs):
    for n in self.__call__():
      f(n, *args, **kwargs)

  def clean(self):
    """ Reset the cache """
    self._cache = []

  def __del__(self):
    self.clean()

