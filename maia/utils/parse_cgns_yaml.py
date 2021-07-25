from typing import List
from ruamel.yaml import YAML
from ruamel.yaml import parser
import ast
import numpy as np
import Converter.PyTree as C
import maia.sids.internal as I
import maia.sids.cgns_keywords as CGK
import maia.utils.py_utils as PYU

LINE_MAX = 300

def generate_line(node: I.TreeNode, lines: List, ident: int=0):
  start = True if not bool(lines) else False

  # Print value
  node_value = I.get_value(node)
  value_type = ''
  if isinstance(node_value, str):
    value = f"'{node_value}'"
  elif isinstance(node_value, (int, float, list)):
    value = str(node_value)
  elif isinstance(node_value, (tuple, set)):
    value = str(list(node_value))
  elif isinstance(node_value, np.ndarray):
    if node_value.dtype == CGK.cgns_to_dtype[CGK.C1]: # and node_value.size < 32:
      value = f"'{node_value.tostring()}'"
    elif node_value.dtype in [np.dtype('<U8'), np.dtype('>U8')]:
      value = f"{node_value.tolist()}"
    else:
      value_type = f"{' '*ident}  {CGK.dtype_to_cgns[node_value.dtype]}\n"
      value = f"{node_value.tolist()}"
  else:
    value = ''

  line = f"{' '*ident}{I.get_name(node)} {I.get_label(node)} {value}:"
  if len(line) > LINE_MAX:
    values = [f"{' '*ident}  {value[y-LINE_MAX:y]}" for y in range(LINE_MAX, len(value)+LINE_MAX, LINE_MAX)]
    svalues = "\n".join(values)
    line = """{ident}? >
{ident}  {name}
{ident}  {label}
{value_type}{values}
{ident}  :""".format(ident=' '*ident,
                     name=I.get_name(node),
                     label=I.get_label(node),
                     value_type=value_type,
                     values=svalues)
  lines.append(line)

  children      = I.get_children(node)
  iend_children = len(children)-1
  for i, child in enumerate(children):
    generate_line(child, lines, ident+2)

  if start:
    return lines

def to_yaml(t: I.TreeNode):
  lines = []
  for base in I.get_all_base(t):
    generate_line(base, lines=lines)
  return lines

if __name__ == "__main__":
  from maia.utils import parse_yaml_cgns
  with open("test/cubeU_join_bnd-ref.yaml", "r") as f:
    yt0 = f.read()
  # print(f"yt0 = {yt0}")
  t = parse_yaml_cgns.to_cgns_tree(yt0)
  I.print_tree(t)
  lines = to_yaml(t)
  # for l in lines:
  #   print(f"l: {l}")
  yt1 = '\n'.join(lines)
  assert(yt0 == yt1)

  # t = C.convertFile2PyTree('cubeU_join_bnd-new.hdf')
  # # I.print_tree(t)
  # lines = to_yaml(t)
  # # for l in lines:
  # #   print(f"l: {l}")
  # yt = '\n'.join(lines)
  # with open("toto.yaml", "w") as f:
  #   f.write(yt)
  # from maia.utils import parse_yaml_cgns
  # with open("toto.yaml", "r") as f:
  #   yt = f.read()
  # # print(f"yt = {yt}")
  # yaml = YAML(typ="safe")
  # yaml_dict = yaml.load(yt)
  # # print(f"yaml_dict = {yaml_dict}")
  # t = parse_yaml_cgns.to_cgns_tree(yt)
  # I.print_tree(t)
  # C.convertPyTree2File(t, 'toto.hdf')

