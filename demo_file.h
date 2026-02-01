// SPDX-FileCopyrightText: 2024 The OpenSn Authors <https://open-sn.github.io/opensn/>
// SPDX-License-Identifier: MIT

#pragma once

#include <vector>
#include <memory>

namespace opensn
{

class MeshHandler;

class GeometryManager
{
public:
  GeometryManager(size_t dimension, std::shared_ptr<MeshHandler>& mesh);

  size_t GetDimension() const { return dimension_; }
  
  void BuildGeometry();
  
  void UpdateBoundaries(const std::vector<int>& boundary_ids);
  
  bool IsInitialized() const;

private:
  const size_t dimension_;
  std::shared_ptr<MeshHandler> mesh_;
  bool initialized_;
  std::vector<int> boundary_list_;
};

}
