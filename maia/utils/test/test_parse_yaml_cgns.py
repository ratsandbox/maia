from maia.utils import parse_yaml_cgns
import Converter.Internal as I
import numpy as np

def test_yaml_parse():
  assert 1 == 0
#  yt = """
#Base0 Base_t [3,3]:
#  Zone0 Zone_t [24,6,0]:
#    GridCoordinates GridCoordinates_t:
#      CoordinateX DataArray_t:
#        R8 : [ 0,1,2,3,
#               0,1,2,3,
#               0,1,2,3,
#               0,1,2,3,
#               0,1,2,3,
#               0,1,2,3 ]
#      CoordinateY DataArray_t:
#        R4 : [ 0,0,0,0,
#               1,1,1,1,
#               2,2,2,2,
#               0,0,0,0,
#               1,1,1,1,
#               2,2,2,2 ]
#      CoordinateZ DataArray_t:
#        R4 : [ 0,0,0,0,
#               0,0,0,0,
#               0,0,0,0,
#               1,1,1,1,
#               1,1,1,1,
#               1,1,1,1 ]
#    ZoneBC ZoneBC_t:
#      Inlet BC_t:
#        GridLocation GridLocation_t "FaceCenter":
#        PointList IndexArray_t [1,2]: # 1,2 are the two i-faces at x=0
#    ZoneGridConnectivity ZoneGridConnectivity_t:
#      MixingPlane GridConnectivity "Zone1":
#        GridConnectivityType GridConnectivityType_t "Abutting1to1":
#        GridLocation GridLocation_t "FaceCenter":
#        PointList IndexArray_t [7]: # 7 is the bottom i-face at x=3
#        PointListDonor IndexArray_t [1]: # cf. Zone1
#"""
#
#  t = parse_yaml_cgns.to_pytree(yt)
#  assert False
