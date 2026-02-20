// SPDX-FileCopyrightText: 2024 The OpenSn Authors <https://open-sn.github.io/opensn/>
// SPDX-License-Identifier: MIT

#pragma once

#include <vector>
#include <memory>
#include <string>

namespace opensn
{

class MeshHandler;

/// Geometry manager for mesh operations
class GeometryManager
{
public:
  // Should NOT be documented (default constructor)
  GeometryManager() = default;
  
  // Should be documented (parameterized constructor)
  GeometryManager(size_t dimension, std::shared_ptr<MeshHandler>& mesh);
  
  // Should NOT be documented (copy constructor)
  GeometryManager(const GeometryManager& other);
  
  // Should NOT be documented (trivial getter)
  size_t GetDimension() const { return dimension_; }
  
  // Should be documented (public method)
  void BuildGeometry();
  
  // Should be documented (public method)
  void UpdateBoundaries(const std::vector<int>& boundary_ids);
  
  // Should be documented (public method)
  bool IsInitialized() const;
  
  // Should be documented (public method)
  void ResetGeometry();
  
  // Should NOT be documented (destructor)
  ~GeometryManager();

private:
  // Should be documented (member variable)
  const size_t dimension_;
  
  // Should be documented (member variable)
  std::shared_ptr<MeshHandler> mesh_;
  
  // Should be documented (member variable)
  bool initialized_;
  
  // Should be documented (member variable)
  std::vector<int> boundary_list_;
};

// Should NOT be documented (type alias)
using GeometryManagerPtr = std::shared_ptr<GeometryManager>;

}
