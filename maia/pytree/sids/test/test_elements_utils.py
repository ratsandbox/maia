import pytest
import Converter.Internal as I

from maia.pytree.sids import elements_utils as EU

def test_element_name():
  assert EU.element_name(5)  == "TRI_3"
  assert EU.element_name(38) == "HEXA_56"
  with pytest.raises(AssertionError):
    EU.element_name(1000)

def test_element_dim():
  assert EU.element_dim(5)  == 2
  assert EU.element_dim(38) == 3
  with pytest.raises(AssertionError):
    EU.element_dim(1000)

def test_element_number_of_nodes():
  assert EU.element_number_of_nodes(5)  == 3
  assert EU.element_number_of_nodes(38) == 56
  with pytest.raises(AssertionError):
    EU.element_number_of_nodes(1000)
