import numpy as np
import maia.pytree as PT

def print_node(node, depth, pformat, plabel, last_child, max_depth, filtering):

  # Format
  if depth != 0:
    pipe   = '|'
    under  = '_'
    if len(pformat)>0:
      if pformat[-1]=='|': offset = '   '
      else               : offset = '    '
    else :                 offset = '   '
  else         :
    pipe   = ''
    under  = ''
    offset = ''

  # Value to print
  name  = PT.get_name(node)
  if type(PT.get_value(node))==np.ndarray:
    value = f'array(shape={PT.get_value(node).shape}, dtype={PT.get_value(node).dtype})'
  else:
    value = type(PT.get_value(node))
  nsons = len(PT.get_children(node))
  label = PT.get_label(node)
  
  if   nsons==0:fson ="son"
  elif nsons==1:fson ="son"
  else         :fson ="sons"

  if  name  not in filtering['name' ] and\
      label not in filtering['label']:
        
    if plabel in ["Zone_t", "ZoneBC_t"] and not(last_child):
      pformat = pformat+offset+pipe
      print(f"{pformat}{under}[{name}, {value}, {nsons} {fson}, {label}]")
    else :
      pformat = pformat+offset
      print(f"{pformat}{pipe}{under}[{name}, {value}, {nsons} {fson}, {label}]")

    depth +=1
    if depth<=max_depth:
      for i_child, child in enumerate(PT.get_children(node)):
        print_node(child, depth, pformat, label, i_child==nsons-1, max_depth, filtering)


def print_tree(tree, max_depth=100, filtering={'name':[], 'label':[]} ):
  '''
  Print arborescence of a CGNSTree or a node.

  Args:
    tree      (CGNSTree) -- CGNSTree or node to be printed.
    max_depth (int)      -- Maximum tree depth for printing.
    filtering (dict)     -- Dictionary on node names and label to not be printed.

  '''
  depth = 0
  pformat = ''
  plabel = ''
  print_node(tree, depth, pformat, plabel, False,
        max_depth=max_depth, filtering=filtering)

