#include <iostream>
#include <vector>
#include <algorithm>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include "std_e/algorithm/permutation.hpp"

namespace py = pybind11;

template<typename T> constexpr auto
make_raw_view(py::array_t<T, py::array::f_style>& x){
  py::buffer_info buf = x.request();
  return static_cast<T*>(buf.ptr);
}

void
adapt_match_information(py::array_t<int, py::array::f_style>& np_neighbor_idx,
                        py::array_t<int, py::array::f_style>& np_neighbor_desc,
                        py::array_t<int, py::array::f_style>& np_recv_entity_stri,
                        py::array_t<int, py::array::f_style>& np_point_list,
                        py::array_t<int, py::array::f_style>& np_point_list_donor)
{
  int join_size = np_point_list.size();

  auto neighbor_idx     = make_raw_view(np_neighbor_idx);
  auto neighbor_desc    = make_raw_view(np_neighbor_desc);     /* i_proc, i_cloud, i_entity */
  auto entity_stri      = make_raw_view(np_recv_entity_stri);  /* stride of pointlist       */
  auto point_list       = make_raw_view(np_point_list);        /* point_list                */
  auto point_list_donor = make_raw_view(np_point_list_donor);  /* point_list_donor          */

  // Sanity check - For now only faces so 1to1 - En vertex on aura le pb
  for(int i = 0; i < join_size; ++i){
    assert(neighbor_idx[i+1] - neighbor_idx[i] == 1);
    assert(entity_stri[i] == 1);
  }

  /* We first need to sort the neighbor_desc lexicographicly */
  std::vector<int> order(join_size);
  std::iota(begin(order), end(order), 0);
  std::sort(begin(order), end(order), [&](auto& i, auto& j){
    return std::tie(neighbor_desc[3*i], neighbor_desc[3*i+1], neighbor_desc[3*i+2])
         < std::tie(neighbor_desc[3*j], neighbor_desc[3*j+1], neighbor_desc[3*j+2]);
  });

  /* Now we have section with all coherent partition */
  // Count how many new section is here
  std::vector<int> section_idx(join_size, 0);
  int n_entity  = 0;
  int n_section = 1;
  int cur_proc = neighbor_desc[3*order[0]  ];
  int cur_part = neighbor_desc[3*order[0]+1];
  for(int i = 1; i < join_size; ++i){
    int p = order[i];
    int next_proc = neighbor_desc[3*p  ];
    int next_part = neighbor_desc[3*p+1];
    if( next_part != cur_part || next_proc != cur_proc ){
      cur_proc = next_proc;
      cur_part = next_part;
      section_idx[n_section] = n_entity;
      n_section++;
      n_entity = 0;
    } else {
      n_entity++;
    }
  }
  section_idx[n_section] = n_entity;
  printf(" n_section = %i\n", n_section);
  section_idx.resize(n_section+1);
  for (int i = 0; i < n_section; i++){
    section_idx[i+1] += section_idx[i];
    printf("section_idx[%i] = %i \n", i+1, section_idx[i+1]);
  }

  std_e::permute(point_list      , order);
  std_e::permute(point_list_donor, order);

  // Now we order the pointlist
  std::vector<int> point_list_min(join_size);
  std::vector<int> point_list_max(join_size);

  for(int i = 0; i < join_size; ++i){
    point_list_min[i] = std::min(point_list[i], point_list_donor[i]);
    point_list_max[i] = std::max(point_list[i], point_list_donor[i]);
  }

  // Pour chaque raccord il faut trier

  std::vector<int> order_pl(join_size);
  std::iota(begin(order_pl), end(order_pl), 0);

  std::sort(begin(order_pl), end(order_pl), [&](auto& i, auto& j){
    return std::tie(point_list_min[i], point_list_max[i])
         < std::tie(point_list_min[j], point_list_max[j]);
  });


  // Panic verbose
  for(int i = 0; i < join_size; ++i){
    std::cout << "Info :: pl = " << point_list[i] << " | pld = " << point_list_donor[i];
    std::cout << " | order = " << order[i] << " | order_pl = " << order_pl[i];
    std::cout << " | " << neighbor_desc[3*i  ] << "/";
    std::cout <<          neighbor_desc[3*i+1] << "/";
    std::cout <<          neighbor_desc[3*i+2] << std::endl;
  }

}


auto
compute_face_center_and_characteristic_length(py::array_t<int   , py::array::f_style>& np_point_list,
                                              py::array_t<double, py::array::f_style>& np_cx,
                                              py::array_t<double, py::array::f_style>& np_cy,
                                              py::array_t<double, py::array::f_style>& np_cz,
                                              py::array_t<int   , py::array::f_style>& np_face_vtx,
                                              py::array_t<int   , py::array::f_style>& np_face_vtx_idx)
{
  int bnd_size = np_point_list.size();

  auto point_list   = make_raw_view(np_point_list);
  auto cx           = make_raw_view(np_cx);
  auto cy           = make_raw_view(np_cy);
  auto cz           = make_raw_view(np_cz);
  auto face_vtx     = make_raw_view(np_face_vtx);
  auto face_vtx_idx = make_raw_view(np_face_vtx_idx);

  py::array_t<double, py::array::f_style> np_bnd_coord(3*bnd_size);
  py::array_t<double, py::array::f_style> np_characteristic_lenght(bnd_size);

  auto bnd_coord             = make_raw_view(np_bnd_coord);
  auto characteristic_lenght = make_raw_view(np_characteristic_lenght);

  for(int idx = 0; idx < bnd_size; ++idx) {
    int i_face = point_list[idx]-1;
    bnd_coord[3*idx  ] = 0.;
    bnd_coord[3*idx+1] = 0.;
    bnd_coord[3*idx+2] = 0.;

    characteristic_lenght[idx] = std::numeric_limits<double>::max();

    int beg = face_vtx_idx[i_face];
    int n_vtx_on_face = face_vtx_idx[i_face+1]-beg;

    for(int idx_vtx = beg; idx_vtx < face_vtx_idx[i_face+1]; ++idx_vtx){

      int pos1 =   idx_vtx - beg;
      int pos2 = ( idx_vtx - beg + 1 ) % n_vtx_on_face;

      int ivtx1 = face_vtx[beg+pos1] - 1;
      int ivtx2 = face_vtx[beg+pos2] - 1;

      // std::cout << "pos1 = " << pos1 << " | pos2 = " << pos2 << std::endl;
      // std::cout << "ivtx1 = " << ivtx1 << " | ivtx2 = " << ivtx2 << std::endl;

      bnd_coord[3*idx  ] += cx[ivtx1];
      bnd_coord[3*idx+1] += cy[ivtx1];
      bnd_coord[3*idx+2] += cz[ivtx1];

      double dx = cx[ivtx1] - cx[ivtx2];
      double dy = cy[ivtx1] - cy[ivtx2];
      double dz = cz[ivtx1] - cz[ivtx2];
      double le = std::sqrt(dx*dx + dy*dy + dz*dz);

      characteristic_lenght[idx] = std::min(characteristic_lenght[idx], le);

    }

    // Finish
    double inv = 1./n_vtx_on_face;
    bnd_coord[3*idx  ] = bnd_coord[3*idx  ] * inv;
    bnd_coord[3*idx+1] = bnd_coord[3*idx+1] * inv;
    bnd_coord[3*idx+2] = bnd_coord[3*idx+2] * inv;

  }

  return std::make_tuple(np_bnd_coord, np_characteristic_lenght);
}



PYBIND11_MODULE(geometry, m) {
  m.doc() = "pybind11 utils for geomery plugin"; // optional module docstring

  m.def("compute_face_center_and_characteristic_length", &compute_face_center_and_characteristic_length,
        py::arg("np_point_list").noconvert(),
        py::arg("np_cx").noconvert(),
        py::arg("np_cy").noconvert(),
        py::arg("np_cz").noconvert(),
        py::arg("np_face_vtx").noconvert(),
        py::arg("np_face_vtx_idx").noconvert());

  m.def("adapt_match_information", &adapt_match_information,
        py::arg("np_neighbor_idx"    ).noconvert(),
        py::arg("np_neighbor_desc"   ).noconvert(),
        py::arg("np_recv_entity_stri").noconvert(),
        py::arg("np_point_list"      ).noconvert(),
        py::arg("np_point_list_donor").noconvert());

}
