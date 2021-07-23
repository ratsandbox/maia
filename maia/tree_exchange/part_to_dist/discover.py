import Converter.Internal as I
import maia.sids.cgns_keywords as CGK
import maia.sids.Internal_ext  as IE


def discover_nodes_from_matching(dist_node, part_nodes, queries, comm,
                                 child_list=[], get_value="ancestors",
                                 merge_rule=lambda path:path):
  """
  Recreate a distributed structure (basically without data) in dist_node merging all the
  path found in (locally known) part_nodes.
  Usefull eg to globally reput on a dist_zone some BC created on specific part_zones.
  Nodes already present in dist_node will not be added.
  dist_node and part_nodes are the starting point of the search to which queries is related
  Additional options:
    child_list is a list of node names or types related to leaf nodes that will be copied into dist_node
    get_value (string) indicates which nodes of the path must repport their value to the dist node
      (none = nothing, all = all nodes of queries, anything else = all but last nodes of queries)
    merge_rule accepts a function whose argument is the leaf node path. This function can map the path to an
      other, eg to merge splitted node related to a same dist node
  Todo : could be optimised using a distributed hash table -> see BM
  """
  collected_part_nodes = dict()
  for part_node in part_nodes:
    for nodes in IE.iterNodesWithParentsByMatching(part_node, queries):
      # Apply merge rule to map splitted nodes (eg jn) to the same dist node
      leaf_path = merge_rule('/'.join([I.getName(node) for node in nodes]))
      # Avoid data duplication to minimize exchange
      if I.getNodeFromPath(dist_node, leaf_path) is None and leaf_path not in collected_part_nodes:
        # Label
        labels = [I.getType(node) for node in nodes]

        # Values
        leaf = nodes[-1]
        if isinstance(get_value, str):
          if get_value == "none":
            get_value = len(nodes)*[False]
          elif get_value == "all":
            get_value = len(nodes)*[True]
          elif get_value == "ancestors":
            get_value = [True]*(len(nodes)-1) + [False]
          elif get_value == "leaf":
            get_value = [False]*(len(nodes)-1) + [True]
          else:
            raise ValueError(f"If get_value argument is a string, it must be in {{'none', 'all', 'ancestors' or 'leaf'}}, '{get_value}' given here.")
        if isinstance(get_value, (tuple, list)):
          values = [I.getValue(node) if value else None for node, value in zip(nodes, get_value)]
        else:
          raise TypeError(f"get_value argument is a list or a string in {{'none', 'all' or 'ancestors'}}, '{get_value}' given here.")

        # Children
        childs = list()
        for query in child_list:
          childs.extend(IE.getNodesDispatch1(leaf, query))
        collected_part_nodes[leaf_path] = (labels, values, childs)

  for rank_node_path in comm.allgather(collected_part_nodes):
    for node_path, (labels, values, childs) in rank_node_path.items():
      if I.getNodeFromPath(dist_node, node_path) is None:
        nodes_name = node_path.split('/')
        ancestor = dist_node
        for name, label, value in zip(nodes_name, labels, values):
          ancestor = I.createUniqueChild(ancestor, name, label, value)
        # At the end of this loop, ancestor is in fact the leaf node
        for child in childs:
          I._addChild(ancestor, child)

